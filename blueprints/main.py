# blueprints/main.py

from flask import Blueprint, render_template, jsonify, request, current_app
import logging
import base64
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from utils.snipe_it_api import (
    handle_user_signin,
    checkout_asset,
    checkin_asset
)

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# Global variables to store current user state
current_user = {
    'id': None,
    'name': None,
    'action': None  # 'checkin' or 'checkout'
}

@main_bp.route('/')
def home():
    logger.debug('Home page accessed.')
    return render_template('index.html')

@main_bp.route('/sign-in')
def sign_in():
    try:
        return render_template('sign-in.html')
    except Exception as e:
        print(f"Error rendering template: {e}")
        return "An error occurred", 500

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
        
        # Determine the action based on current state
        if current_user['id'] is None:
            # Handle user sign-in
            result = handle_user_signin(barcode_data)
            if 'error' in result:
                logger.error(result['error'])
                return jsonify({'success': False, 'error': result['error']})
            else:
                # Update current user state
                current_user['id'] = result['id']
                current_user['name'] = result['name']
                logger.info(f"User signed in: {current_user['name']}")
                return jsonify({'success': True, 'message': f"Welcome, {current_user['name']}!"})
        else:
            # Handle asset check-in or check-out
            if current_user['action'] == 'checkout':
                result = checkout_asset(barcode_data, current_user['id'])
            elif current_user['action'] == 'checkin':
                result = checkin_asset(barcode_data, current_user['id'])
            else:
                logger.error('No action specified for asset processing.')
                return jsonify({'success': False, 'error': 'No action specified.'})

            if 'error' in result:
                logger.error(result['error'])
                return jsonify({'success': False, 'error': result['error']})
            else:
                logger.info(result['message'])
                return jsonify({'success': True, 'message': result['message']})
    else:
        logger.warning('No barcode found in the image.')
        return jsonify({'success': False, 'error': 'No barcode found.'})

@main_bp.route('/set-action', methods=['POST'])
def set_action():
    data = request.get_json()
    action = data.get('action')
    if action in ['checkin', 'checkout']:
        current_user['action'] = action
        logger.debug(f"Action set to {action}.")
        return jsonify({'success': True})
    else:
        logger.error('Invalid action specified.')
        return jsonify({'success': False, 'error': 'Invalid action.'})

@main_bp.route('/sign-out', methods=['POST'])
def sign_out():
    logger.info(f"User signed out: {current_user['name']}")
    current_user['id'] = None
    current_user['name'] = None
    current_user['action'] = None
    return jsonify({'success': True, 'message': 'Signed out successfully.'})
