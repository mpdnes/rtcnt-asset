from flask import Blueprint, render_template, jsonify, request, current_app, session, redirect, url_for
import logging
import base64
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from utils.snipe_it_api import (
    handle_user_signin,
    checkout_asset,
    checkin_asset,
    get_asset_info,
    is_asset_assigned_to_user
)

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

main_bp = Blueprint('main_bp', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def home():
    logger.debug('Home page accessed.')
    return redirect(url_for('main_bp.sign_in'))

@main_bp.route('/sign-in')
def sign_in():
    if 'user_id' in session:
        return redirect(url_for('main_bp.dashboard'))
    return render_template('sign_in.html')

@main_bp.route('/process_image', methods=['POST'])
def process_image():
    logger.debug('Processing image from client.')
    data = request.get_json()
    image_data = data['image']

    # Remove the data URL prefix
    header, encoded = image_data.split(',', 1)
    image_bytes = base64.b64decode(encoded)

    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    # Decode image
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Process the image to detect barcodes
    barcodes = decode(img)
    if barcodes:
        barcode_data = barcodes[0].data.decode('utf-8')
        logger.debug(f'Barcode data detected: {barcode_data}')
        
        # Handle user sign-in
        result = handle_user_signin(barcode_data)
        logger.debug(f"User Sign-In Result: {result}")  # Log the result to inspect its structure
        print(f"User Sign-In Result: {result}")  # Use print to ensure visibility

        if 'error' in result:
            logger.error(result['error'])
            return jsonify({'success': False, 'error': result['error']})
        else:
            # Safely access session variables using .get()
            session['user_name'] = result.get('name', 'Unknown')
            session['employee_num'] = result.get('employee_num', 'Not Available')

            logger.info(f"Session Data - user_name: {session['user_name']}, employee_num: {session['employee_num']}")
            logger.info(f"User signed in: {session['user_name']}")
            # Include a redirect URL in the response
            return jsonify({'success': True, 'message': f"Welcome, {session['user_name']}!", 'redirect': url_for('main_bp.dashboard')})
    else:
        logger.warning('No barcode found in the image.')
        return jsonify({'success': False, 'error': 'No barcode found in the image.'})


@main_bp.route('/dashboard')
def dashboard():
    logger.debug(f"Session Data at Dashboard: {dict(session)}")  # Log the entire session
    if 'user_name' not in session:
        return redirect(url_for('main_bp.sign_in'))
    return render_template('dashboard.html', user_name=session.get('user_name', 'Unknown'))

@main_bp.route('/logout')
def logout():
    logger.info(f"User logged out: {session.get('user_name')}")
    session.clear()
    return redirect(url_for('main_bp.sign_in'))
