import os
import cv2
import requests
from pyzbar.pyzbar import decode
from flask import Flask, render_template, jsonify, request
import re

# Snipe-IT API configuration
API_URL = 'https://129.21.94.190/api/v1/'
API_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIzIiwianRpIjoiYWMxZDhjOWI1MzA4NWJlMjkyMDg4ZDAwYWYzNDMwMWM0NTU2N2JiNmYxMGQ2YzQ3YjVhMDIwNzVmZGU3NDMzODUwMTQxODQzYzFiMDZkM2IiLCJpYXQiOjE3MjQ4NjQ4NTMuNDY2NzA0LCJuYmYiOjE3MjQ4NjQ4NTMuNDY2NzIyLCJleHAiOjIxOTgxNjQwNTMuNDUyNTk4LCJzdWIiOiIxIiwic2NvcGVzIjpbXX0.WBnunRdiV2d6armj1T87YMeW3xXIEBmiAAm2pRD73MIkwl-ja_AdSyjEzTC0FsENDOe9Zhhaqyva9wmjdcwW5lk8n__RiemYNRXilHBRblgXPg8waIV4kp5AafbUwSKBibWRdOomCdyBFleBR7CiuSx1tSXsmALInd2jEUIiJ8gStlmznrAWqwkOe5YmBXujSh5tkkKifx0uA_9n3Z2pMQ1tGcAGjB3t2AA61CqcQ1rbrAdZz5EthMcTAQgoDNqNoD5BJR1keKC_Bjt15fcj_eNX7pLPqL2Ix_3EENe-xDqMSKKCvMMXTm7PtO4tt2jhNLmgi2iwZE24TDdZDDgPx4z65KIiBakQ9syoECNLoKI1OUV0_7WVv002SH6eMsl1pIxkPIZZYZIx0YRpxPtRbA5f9xNp89DDGcLSaGQV3XG-bqqYBYg8A9QX3SaoXbWIFPS6HfKFRbBl2edc-sAYy8rtn8G8gzl9G1WWzxCkhSk7P746ghYKif-VP922kWQQZs5RgY25Qzj6iq7zRNG7zpCZmonb3D_fQmaj4D4smSW6w-NU08M-cDutJ9jDmzwio02UK02ZTvDMFqyLaB6trMlM8TThg1H6DlQXQjE79BPGcg3SQzLYG9RD4DP_LIuIOdMSUbWaWhRgQ1xzngaqpDVI-cndkWs2vLaTrYiT9KA'
# Initialize Flask app
app = Flask(__name__)

# Global variables
current_user_id = None
current_user_name = None
current_action = None

HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

def get_user_info(employee_num):
    """Fetches the user information from Snipe-IT using the employee number."""
    params = {'employee_num': employee_num}
    
    try:
        response = requests.get(f"{API_URL}/users", headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        if 'rows' in data and len(data['rows']) > 0:
            return data['rows'][0]  # Assuming you want the first matching user
        else:
            return None
    except (requests.RequestException, KeyError, IndexError):
        return None

def get_asset_id(barcode_data):
    """Fetches the asset information from Snipe-IT using the asset's barcode data."""
    try:
        response = requests.get(f"{API_URL}/hardware/{barcode_data}", headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        return data['id'] if 'id' in data else None
    except requests.RequestException:
        return None
    
def extract_asset_id_from_link(link):
    """Extracts the asset ID from the link using a regular expression."""
    match = re.search(r'/(\d+)$', link)
    if match:
        return match.group(1)
    return None

def checkout_asset(barcode_data):
    """Handles asset checkout, ensuring it's not already checked out and the user has permission."""
    global current_user_id

    if current_user_id is None:
        return {'error': "No user signed in."}
    
    asset_id = extract_asset_id_from_link(barcode_data)
    if asset_id is None:
        return {'error': "Asset not found."}
    
    if is_asset_checked_out(asset_id):
        return {'error': "Asset is already checked out or not available for checkout."}

    payload = {
        "checkout_to_type": "user",
        "status_id": 2,  # Use the correct status ID for your system
        "assigned_user": current_user_id  
    }

    checkout_url = f"{API_URL}/hardware/{asset_id}/checkout"

    try:
        response = requests.post(checkout_url, json=payload, headers=HEADERS)
        response.raise_for_status()
        return {'message': "Asset checked out successfully."}
    except requests.RequestException as e:
        return {'error': f"Failed to check out asset: {e}"}

def is_asset_checked_out(asset_id):
    """Checks if the asset is currently checked out or cannot be checked out by the user."""
    try:
        response = requests.get(f"{API_URL}/hardware/{asset_id}", headers=HEADERS)
        response.raise_for_status()
        asset_data = response.json()
        return asset_data['status_label']['status_meta'] == 'deployed' or not asset_data.get('user_can_checkout', False)
    except requests.RequestException:
        return None
    
def is_asset_assigned_to_user(asset_id, user_id):
    """Checks if the asset is currently assigned to the given user."""
    try:
        response = requests.get(f"{API_URL}/hardware/{asset_id}", headers=HEADERS)
        response.raise_for_status()
        asset_data = response.json()
        return asset_data.get('assigned_to', {}).get('id') == user_id
    except requests.RequestException:
        return None

def checkin_asset(barcode_data):
    """Handles asset check-in, ensuring it's assigned to the current user."""
    global current_user_id

    asset_id = extract_asset_id_from_link(barcode_data)
    if asset_id is None:
        return {'error': "Asset not found."}
    
    if not is_asset_assigned_to_user(asset_id, current_user_id):
        return {'error': "You cannot check in an asset that is not assigned to you."}

    payload = {
        "checkout_id": None,  # This should be the ID of the current checkout, or None if handling automatically
        "note": "Checked in via kiosk"
    }

    checkin_url = f"{API_URL}/hardware/{asset_id}/checkin"

    try:
        response = requests.post(checkin_url, json=payload, headers=HEADERS)
        response.raise_for_status()
        return {'message': "Asset checked in successfully."}
    except requests.RequestException as e:
        return {'error': f"Failed to check in asset: {e}"}

def start_camera(barcode_type='user'):
    """Starts the camera and continuously scans for barcodes."""
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # Adjust index based on your camera
    if not cap.isOpened():
        return {'error': "Could not open the camera"}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (640, 480))
        barcodes = decode(frame)
        for barcode in barcodes:
            barcode_data = barcode.data.decode('utf-8')
            cap.release()
            cv2.destroyAllWindows()
            if barcode_type == 'user':
                return handle_user_signin(barcode_data)
            elif barcode_type == 'asset':
                if current_action == 'checkout':
                    return checkout_asset(barcode_data)
                elif current_action == 'checkin':
                    return checkin_asset(barcode_data)

        cv2.imshow('Scan QR Code or Barcode', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
            break

    cap.release()
    cv2.destroyAllWindows()
    return {'error': "No barcode found."}

def handle_user_signin(barcode_data):
    """Handles user sign-in by scanning a barcode."""
    global current_user_id, current_user_name
    user_info = get_user_info(employee_num=barcode_data)
    if user_info:
        current_user_id = user_info['id']
        current_user_name = user_info['name']
        return {'name': current_user_name}
    else:
        return {'error': "Failed to sign in. User not found."}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start-camera', methods=['POST'])
def camera_action():
    barcode_type = request.args.get('type')  # Get the type (user, checkin, checkout)
    result = start_camera(barcode_type)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)