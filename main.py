import os
import cv2
import requests
from pyzbar.pyzbar import decode
import tkinter as tk
from tkinter import messagebox
import re

# Snipe-IT API configuration
API_URL = 'https://129.21.94.190/api/v1/'
API_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIzIiwianRpIjoiYWMxZDhjOWI1MzA4NWJlMjkyMDg4ZDAwYWYzNDMwMWM0NTU2N2JiNmYxMGQ2YzQ3YjVhMDIwNzVmZGU3NDMzODUwMTQxODQzYzFiMDZkM2IiLCJpYXQiOjE3MjQ4NjQ4NTMuNDY2NzA0LCJuYmYiOjE3MjQ4NjQ4NTMuNDY2NzIyLCJleHAiOjIxOTgxNjQwNTMuNDUyNTk4LCJzdWIiOiIxIiwic2NvcGVzIjpbXX0.WBnunRdiV2d6armj1T87YMeW3xXIEBmiAAm2pRD73MIkwl-ja_AdSyjEzTC0FsENDOe9Zhhaqyva9wmjdcwW5lk8n__RiemYNRXilHBRblgXPg8waIV4kp5AafbUwSKBibWRdOomCdyBFleBR7CiuSx1tSXsmALInd2jEUIiJ8gStlmznrAWqwkOe5YmBXujSh5tkkKifx0uA_9n3Z2pMQ1tGcAGjB3t2AA61CqcQ1rbrAdZz5EthMcTAQgoDNqNoD5BJR1keKC_Bjt15fcj_eNX7pLPqL2Ix_3EENe-xDqMSKKCvMMXTm7PtO4tt2jhNLmgi2iwZE24TDdZDDgPx4z65KIiBakQ9syoECNLoKI1OUV0_7WVv002SH6eMsl1pIxkPIZZYZIx0YRpxPtRbA5f9xNp89DDGcLSaGQV3XG-bqqYBYg8A9QX3SaoXbWIFPS6HfKFRbBl2edc-sAYy8rtn8G8gzl9G1WWzxCkhSk7P746ghYKif-VP922kWQQZs5RgY25Qzj6iq7zRNG7zpCZmonb3D_fQmaj4D4smSW6w-NU08M-cDutJ9jDmzwio02UK02ZTvDMFqyLaB6trMlM8TThg1H6DlQXQjE79BPGcg3SQzLYG9RD4DP_LIuIOdMSUbWaWhRgQ1xzngaqpDVI-cndkWs2vLaTrYiT9KA'
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
            print("No user data found")
            return None
    except (requests.RequestException, KeyError, IndexError) as e:
        print(f"Failed to fetch user info: {e}")
        return None

def get_asset_id(barcode_data):
    """Fetches the asset information from Snipe-IT using the asset's barcode data."""
    params = {'asset_tag': barcode_data}  # Assuming the barcode contains the asset_tag
    try:
        response = requests.get(f"{API_URL}/hardware/{barcode_data}", headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        return data['id'] if 'id' in data else None
    except requests.RequestException as e:
        print(f"Failed to fetch asset info: {e}")
        return None
    
def extract_asset_id_from_link(link):
    """Extracts the asset ID from the link using a regular expression."""
    match = re.search(r'/(\d+)$', link)
    if match:
        return match.group(1)
    return None

def checkout_asset(barcode_data):
    """Handles asset checkout, ensuring it's not already checked out and the user has permission."""
    
    if current_user_id is None:
        messagebox.showerror("Error", "No user signed in.")
        return
    
    asset_id = extract_asset_id_from_link(barcode_data)

    if asset_id is None:
        messagebox.showerror("Error", "Asset not found.")
        return
    
    if is_asset_checked_out(asset_id):
        messagebox.showerror("Error", "Asset is already checked out or not available for checkout.")
        return

    payload = {
        "checkout_to_type": "user",
        "status_id": 2,  # Use the correct status ID for your system
        "assigned_user": current_user_id  
    }

    checkout_url = f"{API_URL}/hardware/{asset_id}/checkout"

    try:
        response = requests.post(checkout_url, json=payload, headers=HEADERS)
        response.raise_for_status()
        messagebox.showinfo("Success", "Asset checked out successfully.")
    except requests.RequestException as e:
        print(f"Failed to check out asset: {e}")
        messagebox.showerror("Error", f"Failed to check out asset: {e}")

        
def is_asset_checked_out(asset_id):
    """Checks if the asset is currently checked out or cannot be checked out by the user."""
    try:
        response = requests.get(f"{API_URL}/hardware/{asset_id}", headers=HEADERS)
        response.raise_for_status()
        asset_data = response.json()

        # Check if the asset is already checked out or cannot be checked out
        if asset_data['status_label']['status_meta'] == 'deployed' or not asset_data.get('user_can_checkout', False):
            return True
        return False
    except requests.RequestException as e:
        print(f"Failed to check asset status: {e}")
        return None
    
def is_asset_assigned_to_user(asset_id, user_id):
    """Checks if the asset is currently assigned to the given user."""
    try:
        response = requests.get(f"{API_URL}/hardware/{asset_id}", headers=HEADERS)
        response.raise_for_status()
        asset_data = response.json()

        # Assuming 'assigned_to' contains the user information the asset is assigned to
        if asset_data.get('assigned_to', {}).get('id') == user_id:
            return True
        return False
    except requests.RequestException as e:
        print(f"Failed to check asset assignment: {e}")
        return None


def checkin_asset(barcode_data):
    """Handles asset check-in, ensuring it's assigned to the current user."""
    
    asset_id = extract_asset_id_from_link(barcode_data)

    if asset_id is None:
        messagebox.showerror("Error", "Asset not found.")
        return
    
    if not is_asset_assigned_to_user(asset_id, current_user_id):
        messagebox.showerror("Error", "You cannot check in an asset that is not assigned to you.")
        return

    payload = {
        "checkout_id": None,  # This should be the ID of the current checkout, or None if handling automatically
        "note": "Checked in via kiosk"
    }

    checkin_url = f"{API_URL}/hardware/{asset_id}/checkin"

    try:
        response = requests.post(checkin_url, json=payload, headers=HEADERS)
        response.raise_for_status()
        messagebox.showinfo("Success", "Asset checked in successfully.")
    except requests.RequestException as e:
        print(f"Failed to check in asset: {e}")
        messagebox.showerror("Error", f"Failed to check in asset: {e}")


def start_camera(barcode_type='user'):
    """Starts the camera and continuously scans for barcodes."""
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # Adjust index based on your camera
    if not cap.isOpened():
        messagebox.showerror("Error", "Could not open the camera")
        return

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
                handle_user_signin(barcode_data)
            elif barcode_type == 'asset':
                if current_action == 'checkout':
                    checkout_asset(barcode_data)
                elif current_action == 'checkin':
                    checkin_asset(barcode_data)
            return

        cv2.imshow('Scan QR Code or Barcode', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
            break

    cap.release()
    cv2.destroyAllWindows()


def handle_user_signin(barcode_data):
    """Handles user sign-in by scanning a barcode."""
    global current_user_id, current_user_name
    user_info = get_user_info(employee_num=barcode_data)
    if user_info:
        current_user_id = user_info['id']
        current_user_name = user_info['name']
        show_main_menu()
    else:
        messagebox.showerror("Error", "Failed to sign in. User not found.")

def show_main_menu():
    """Shows the main menu after the user has signed in."""
    global current_action
    for widget in root.winfo_children():
        widget.destroy()

    welcome_label = tk.Label(root, text=f"Welcome, {current_user_name}!", font=("Helvetica", 16))
    welcome_label.pack(pady=20)

    checkin_button = tk.Button(root, text="Check In", command=lambda: set_action_and_start_camera('checkin'))
    checkin_button.pack(pady=10)

    checkout_button = tk.Button(root, text="Check Out", command=lambda: set_action_and_start_camera('checkout'))
    checkout_button.pack(pady=10)

def set_action_and_start_camera(action):
    global current_action
    current_action = action
    start_camera('asset')


def show_signin_page():
    """Displays the sign-in page."""
    for widget in root.winfo_children():
        widget.destroy()

    signin_label = tk.Label(root, text="Sign In", font=("Helvetica", 16))
    signin_label.pack(pady=20)

    signin_button = tk.Button(root, text="Start Sign In", command=lambda: start_camera('user'))
    signin_button.pack(pady=20)

# Initialize the main application window
root = tk.Tk()
root.title("Snipe-IT Asset Manager")

# Show the sign-in page on startup
show_signin_page()

root.mainloop()