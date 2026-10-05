"""
=============================================================================================================
FACIAL RECOGNITION ATTENDANCE MANAGEMENT SYSTEM
Main Application Entry Point (main.py)
=============================================================================================================
Description:
    This script serves as the master bootstrap entrypoint for the entire desktop application.
    It verifies system requirements, initializes the SQLite database schema with Write-Ahead
    Logging (WAL), creates necessary runtime directories (data/, classifier/, attendance_records/),
    ensures OpenCV's frontal face Haar cascade model is present, and launches the Tkinter Login GUI.

Authors / Development Team (KIIT University):
    1. VED PRAKASH PANDEY (23053645) - Face Detection Module
    2. SIDDHARTH SINGH (23053720)    - Student Management
    3. DEEPAK SAH (23053920)        - System Testing
    4. SANTOSH SAH (23053926)       - Attendance System
    5. ANSHUDEEP SHAH (23053930)    - Login & Security
    6. RISAN SHRESTHA (23053941)    - UI & Dashboard
Supervisor: Mr. Rakesh Kumar Rai
=============================================================================================================
"""

import os
import sys
import tkinter as tk

# -----------------------------------------------------------------------------
# Enable Windows High-DPI Awareness (Prevents blurry scaling on 125%/150% screens)
# -----------------------------------------------------------------------------
try:
    import ctypes
    # Per-monitor DPI aware (Windows 10 / 11)
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        # System DPI aware (Windows 8 / 8.1)
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# -----------------------------------------------------------------------------------------------------------
# Path Configuration: Ensure project root directory is the first entry in Python's module search path (sys.path)
# This prevents ModuleNotFoundError when executing the script from outside its parent folder.
# -----------------------------------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import internal modules
from database.db_manager import initialize_database
from modules.login import LoginWindow

def main():
    """
    Master Application Bootstrap Function.
    
    Execution Workflow:
        1. Database Initialization: Creates 'users', 'students', and 'attendance' tables in SQLite with WAL mode.
        2. Directory Provisioning: Ensures 'data/', 'classifier/', 'attendance_records/', and 'assets/' exist.
        3. Cascade Verification: Validates presence and integrity of 'haarcascade_frontalface_default.xml'.
        4. Asset Readiness Check: Ensures visual assets (headers, icons, avatars) are available.
        5. GUI Launch: Instantiates the single Tkinter master root window and renders the LoginWindow portal.
    """
    # Step 1: Initialize Database Schema (Tables: users, students, attendance)
    # Uses Write-Ahead Logging (WAL) and 60s busy timeout for concurrent read/write safety.
    initialize_database()

    # Step 2: Ensure required runtime folders exist on the local file system
    # 'data/'               -> Stores 100 facial sample crops per registered student (user.<id>.<count>.jpg)
    # 'classifier/'         -> Stores serialized trained LBPH machine learning model (classifier.xml)
    # 'attendance_records/' -> Stores daily timestamped CSV spreadsheets (attendance_DD-MM-YYYY.csv)
    # 'assets/'             -> Stores UI icons, montage banners, wallpapers, and developer portraits
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "classifier"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "attendance_records"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "assets"), exist_ok=True)

    # Step 3: Ensure OpenCV Haar Feature-based Frontal Face Cascade Classifier is present
    # Size check (> 10000 bytes) ensures the XML file is not corrupted or truncated.
    cascade_dest = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
    if not os.path.exists(cascade_dest) or os.path.getsize(cascade_dest) < 10000:
        try:
            import urllib.request, ssl
            # Official OpenCV GitHub repository upstream mirror
            url = 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml'
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx) as response:
                content = response.read()
            with open(cascade_dest, 'wb') as f:
                f.write(content)
        except Exception as e:
            print(f"Haarcascade notice: {e}")

    # Step 4: Fallback asset generation if background or tile graphics are missing
    bg_asset = os.path.join(BASE_DIR, "assets", "bg_login.png")
    if not os.path.exists(bg_asset):
        try:
            from utils.generate_cyber_2k_assets import generate_all_2k_cyber_assets
            from utils.generate_icons import generate_all_icons
            generate_all_2k_cyber_assets()
            generate_all_icons()
        except Exception as e:
            print(f"Asset generation notice: {e}")

    # Step 5: Instantiate Tkinter Master Root Window & Start Event Loop
    # We maintain a SINGLE root window instance to adhere to Python 3.14 thread-safety standards.
    root = tk.Tk()
    app = LoginWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
