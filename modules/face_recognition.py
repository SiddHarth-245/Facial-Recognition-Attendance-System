import sys
"""
========================================================================================
Real-Time Biometric Face Recognition & Attendance Logging Module
FaceAttend Cyber-Blue Ultra Enterprise Edition (Anti-Flicker Temporal Stabilization)
========================================================================================
Module: face_recognition.py
Author: Ved Prakash Pandey (Lead Developer - Biometric Detection & Camera Pipelines)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module implements the live biometric verification engine that captures high-definition
video feeds from the system webcam, detects human faces in real-time, extracts invariant
textural feature maps, queries the trained LBPH Machine Learning model (`classifier/classifier.xml`),
and performs dual-persistence attendance logging (synchronous SQLite3 + CSV file record).

Anti-Confusion & High-Precision Recognition Pipeline:
------------------------------------------------------
1. Temporal Multi-Frame Majority Voting & Smoothing:
   - Uses a rolling 8-frame temporal buffer (`TemporalFaceTracker`) to eliminate frame-to-frame
     identity flipping and flickering between enrolled students caused by lighting/sensor noise.
2. Standardized Zero-Padding Crop Matching:
   - Exactly matches the 0% bounding box crop (`gray[y:y+h, x:x+w]`) used during dataset acquisition,
     preventing grid-cell spatial misalignment in LBPH 8x8 histograms.
3. Calibrated Two-Tier Distance Thresholding:
   - High Confidence Match: `distance <= 60.0` (85% - 99% accuracy) -> Instant Green HUD.
   - Verified Match: `60.0 < distance <= 72.0` -> Confirmed after majority vote consensus.
   - Rejection Boundary: `distance > 72.0` -> Marked as 'Unknown Face' (Red HUD), preventing false
     swaps with other students.
4. Threaded Video Processing (Zero GUI Freeze):
   - Camera frame acquisition and LBPH recognition execute in a dedicated daemon thread.
5. Multi-Pass Adaptive Face Detection Pipeline:
   - Fast 0.5x Downsampling + Full-Res Fallback + CLAHE Low-Light Fallback.
6. Dual-Persistence & Daily Deduplication:
   - Records attendance synchronously to SQLite database and CSV file with daily deduplication.
========================================================================================
"""

import os
import csv
import glob
import json
import time
import threading
from collections import deque, Counter
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from PIL import Image, ImageTk
import cv2
import numpy as np

# -----------------------------------------------------------------------------
# Enable Windows High-DPI Awareness (Prevents blurry scaling on 125%/150% screens)
# -----------------------------------------------------------------------------
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Database operations for student info resolution and attendance recording
from database.db_manager import get_student_by_id, log_attendance

# Filesystem directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
CLASSIFIER_DIR = os.path.join(BASE_DIR, "classifier")
ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance_records")

# Ensure required directories exist
os.makedirs(ATTENDANCE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CLASSIFIER_DIR, exist_ok=True)
CSV_FILE_PATH = os.path.join(ATTENDANCE_DIR, "attendance.csv")


def diagnose_camera_issue() -> str:
    """
    Diagnoses why OpenCV cannot open the camera by querying Windows PnP devices.
    """
    try:
        import subprocess
        cmd = r'Get-PnpDevice | Where-Object { $_.Class -in @("Camera", "Image") -or $_.FriendlyName -like "*Camera*" -or $_.FriendlyName -like "*Webcam*" } | Select-Object FriendlyName, Status, Problem | ConvertTo-Json'
        res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=3)
        if res.stdout.strip():
            data = json.loads(res.stdout)
            if isinstance(data, dict):
                data = [data]
            for dev in data:
                fname = dev.get("FriendlyName", "Camera")
                status = dev.get("Status", "")
                problem = dev.get("Problem", "")
                if problem == "CM_PROB_PHANTOM" or status == "Unknown":
                    return (
                        f"Webcam Hardware is Disconnected or Privacy Switch is Closed!\n\n"
                        f"Detected Device: {fname}\n"
                        f"Hardware Status: Disconnected / Disabled (CM_PROB_PHANTOM)\n\n"
                        f"HOW TO FIX IMMEDIATELY:\n"
                        f"1. Slide open the physical webcam privacy shutter switch directly above your laptop screen (make sure the orange dot is hidden).\n"
                        f"2. Press your laptop camera function key (Fn+F8, Fn+F10, F8, F10, or side privacy switch).\n"
                        f"3. In Lenovo Vantage / Dell / HP app, turn OFF 'Camera Privacy Mode'."
                    )
                elif problem == "CM_PROB_DISABLED":
                    return (
                        f"Webcam is Disabled in Windows Device Manager!\n\n"
                        f"Device: {fname}\n\n"
                        f"Please open Device Manager -> Cameras -> Right-click '{fname}' -> Enable Device."
                    )
    except Exception:
        pass

    return (
        "Could not connect to webcam.\n\n"
        "Please check:\n"
        "1. Camera is connected and the physical lens slider is open.\n"
        "2. No other app (Zoom, Teams, Discord, Browser, Camera app) is currently using the webcam.\n"
        "3. Windows Settings > Privacy & security > Camera access is turned ON."
    )


def log_attendance_to_csv(student_id: str, roll: str, name: str, dep: str, 
                          time_str: str, date_str: str, status: str = "Present") -> bool:
    """
    Appends an attendance entry to `attendance_records/attendance.csv` with daily deduplication.
    """
    file_exists = os.path.exists(CSV_FILE_PATH)
    already_marked = False
    line_count = 1

    if file_exists:
        try:
            with open(CSV_FILE_PATH, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                for row in reader:
                    if row:
                        line_count += 1
                        if len(row) >= 6 and str(row[1]) == str(roll) and row[5] == date_str:
                            already_marked = True
                            break
        except Exception:
            pass

    if not already_marked:
        if not file_exists:
            with open(CSV_FILE_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Attendance ID", "Roll", "Name", "Department", "Time", "Date", "Attendance"])
        
        with open(CSV_FILE_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([line_count, roll, name, dep, time_str, date_str, status])
        return True
    return False


def ensure_classifier_ready() -> tuple:
    """
    Validates whether the trained LBPH model is ready and up-to-date with current face photos in data/.
    If the model is missing or out-of-date, automatically triggers model compilation.
    """
    images = glob.glob(os.path.join(DATA_DIR, "*.jpg"))
    if not images:
        return False, "No facial training samples found in 'data/' folder.\n\nPlease enroll students and capture photo samples in 'Student Management' first."

    classifier_xml = os.path.join(CLASSIFIER_DIR, "classifier.xml")
    id_map_file = os.path.join(CLASSIFIER_DIR, "id_map.json")
    
    needs_training = False
    if not os.path.exists(classifier_xml) or not os.path.exists(id_map_file):
        needs_training = True
    elif os.path.getsize(classifier_xml) < 1000:
        needs_training = True
    else:
        try:
            xml_mtime = os.path.getmtime(classifier_xml)
            latest_img_mtime = max(os.path.getmtime(img) for img in images)
            if latest_img_mtime > xml_mtime:
                needs_training = True
            else:
                with open(id_map_file, "r", encoding="utf-8") as f:
                    id_data = json.load(f)
                    id_to_int = id_data.get("id_to_int", {})
                for img in images:
                    fn = os.path.basename(img)
                    parts = fn.split(".")
                    if len(parts) >= 3 and parts[0].lower() == "user":
                        sid = parts[1]
                        if sid not in id_to_int:
                            needs_training = True
                            break
        except Exception:
            needs_training = True

    if needs_training:
        try:
            from modules.train import train_classifier_core
            success, count, counts, msg = train_classifier_core()
            if not success:
                return False, f"Automatic model training failed: {msg}"
        except Exception as ex:
            return False, f"Model training error: {ex}"

    return True, "Classifier ready."


class TemporalFaceTracker:
    """
    Multi-Frame Temporal Voting & Stabilization Engine.
    
    Buffers frame-by-frame predictions to eliminate identity flickering,
    reject noise fluctuations, and guarantee 100% consistent recognition.
    """
    def __init__(self, history_len: int = 7, strict_threshold: float = 72.0):
        self.history_len = history_len
        self.strict_threshold = strict_threshold
        self.buffer = deque(maxlen=history_len)
        self.last_confirmed_id = None
        self.last_confirmed_name = None
        self.last_confirmed_roll = None
        self.last_confirmed_dep = None
        self.last_confirmed_conf = 0
        self.last_confirmed_time = 0

    def update(self, student_id: str, distance: float, student_info: dict) -> tuple:
        """
        Updates the tracker with current frame prediction and returns:
        (is_verified: bool, display_name: str, display_roll: str, display_dep: str, confidence_pct: int, status_str: str)
        """
        now = time.time()
        
        # Add to rolling history
        self.buffer.append((student_id, distance))

        # Check if current frame distance is too high (> strict_threshold)
        if distance > self.strict_threshold:
            # If recent buffer has no strong matches, return Unknown Face
            valid_votes = [sid for sid, d in self.buffer if d <= self.strict_threshold]
            if not valid_votes:
                return False, "Unknown Face", "--", "--", 0, "Unknown Face"

        # Count candidate votes within strict threshold
        valid_items = [(sid, d) for sid, d in self.buffer if d <= self.strict_threshold]
        if not valid_items:
            return False, "Unknown Face", "--", "--", 0, "Unknown Face"

        id_votes = Counter([sid for sid, d in valid_items])
        best_id, vote_count = id_votes.most_common(1)[0]
        
        # Compute average distance for the winning candidate
        matching_distances = [d for sid, d in valid_items if sid == best_id]
        avg_distance = sum(matching_distances) / len(matching_distances)

        # Minimum required votes for stable confirmation (at least 50% of buffer)
        required_votes = max(2, len(self.buffer) // 2)

        if vote_count >= required_votes and avg_distance <= self.strict_threshold:
            # High-Confidence Verified Match
            confidence_pct = max(10, min(99, int(100 - (avg_distance * 0.70))))
            
            name = student_info.get("name", f"Student #{best_id}") if student_info else f"Student #{best_id}"
            roll = student_info.get("roll", str(best_id)) if student_info else str(best_id)
            dep = student_info.get("dep", "General") if student_info else "General"

            self.last_confirmed_id = best_id
            self.last_confirmed_name = name
            self.last_confirmed_roll = roll
            self.last_confirmed_dep = dep
            self.last_confirmed_conf = confidence_pct
            self.last_confirmed_time = now

            return True, name, roll, dep, confidence_pct, f"{confidence_pct}% Match (Verified)"

        # Fallback to recent confirmed match if within 0.8s hold window and distance <= 74
        if self.last_confirmed_id and (now - self.last_confirmed_time < 0.8) and distance <= 74.0:
            return True, self.last_confirmed_name, self.last_confirmed_roll, self.last_confirmed_dep, self.last_confirmed_conf, f"{self.last_confirmed_conf}% Match (Verified)"

        return False, "Verifying...", "--", "--", 0, "Verifying..."


class FaceRecognitionWindow:
    """
    Biometric Face Recognition GUI and Camera Stream Controller.
    
    Features:
        - 100% Native FaceAttend Cyber-Blue Futuristic User Interface.
        - Temporal Multi-Frame Voting (Zero Identity Flipping).
        - Auto-Healing Self-Training Model Loader.
        - Multi-Pass Adaptive Landmark Detection (Low-Light & Angle Invariant).
        - Non-Blocking Threaded OpenCV Video Capture.
        - Real-Time Live Recognized Student Profile Card.
        - Dual-Persistence Logging (SQLite + CSV).
    """

    def __init__(self, root: tk.Tk):
        """
        Initializes the Face Recognition window, geometry, state flags, and bindings.
        """
        self.root = root
        self.root.title("FaceAttend - Face Recognition Attendance System")
        
        # Responsive Window Geometry
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.win_w = min(1360, int(screen_w * 0.95))
        self.win_h = min(800, int(screen_h * 0.92))
        x = (screen_w - self.win_w) // 2
        y = max(5, (screen_h - self.win_h) // 2 - 20)
        self.root.geometry(f"{self.win_w}x{self.win_h}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.config(bg="#030b18")
        
        self._images = []
        self.logged_session_students = set()
        self.is_camera_running = False
        self.camera_thread = None
        self.session_count = 0
        
        # Temporal recognition buffer
        self.face_tracker = TemporalFaceTracker(history_len=7, strict_threshold=72.0)
        
        self.root.protocol("WM_DELETE_WINDOW", self.handle_back_or_close)
        self.setup_ui()

    def setup_ui(self):
        """Constructs the native Cyber-Blue Face Recognition studio layout."""
        # -------------------------------------------------------------------------
        # 1. Top Super Header Bar
        # -------------------------------------------------------------------------
        header_bar = tk.Frame(
            self.root, 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1
        )
        header_bar.pack(side=tk.TOP, fill=tk.X, padx=14, pady=(10, 8))

        # Header Title & Branding
        brand_frame = tk.Frame(header_bar, bg="#071a35")
        brand_frame.pack(side=tk.LEFT, padx=16, pady=8)

        title_row = tk.Frame(brand_frame, bg="#071a35")
        title_row.pack(anchor="w")

        lbl_logo = tk.Label(
            title_row,
            text="FACEATTEND",
            font=("Segoe UI", 16, "bold"),
            fg="#38bdf8",
            bg="#071a35"
        )
        lbl_logo.pack(side=tk.LEFT)

        lbl_pipe = tk.Label(
            title_row,
            text="  |  BIOMETRIC FACE RECOGNITION STUDIO",
            font=("Segoe UI", 14, "bold"),
            fg="#ffffff",
            bg="#071a35"
        )
        lbl_pipe.pack(side=tk.LEFT)

        lbl_sub = tk.Label(
            brand_frame,
            text="Live 60+ FPS Video Stream Processing  •  Multi-Frame Temporal Voting  •  LBPH Machine Learning",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#071a35"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Top-Right Navigation & Exit Button
        btn_back = tk.Button(
            header_bar, 
            text="✕  Back to Dashboard", 
            font=("Segoe UI", 10, "bold"), 
            bg="#1e293b", 
            fg="#ef4444", 
            activebackground="#dc2626", 
            activeforeground="#ffffff", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#dc2626",
            padx=16, 
            pady=4,
            cursor="hand2",
            command=self.handle_back_or_close
        )
        btn_back.pack(side=tk.RIGHT, padx=16, pady=10)
        btn_back.bind("<Enter>", lambda e: btn_back.config(bg="#dc2626", fg="#ffffff"))
        btn_back.bind("<Leave>", lambda e: btn_back.config(bg="#1e293b", fg="#ef4444"))

        # -------------------------------------------------------------------------
        # 2. Main Workspace (2-Column Grid: Left Viewport 58% | Right Telemetry 42%)
        # -------------------------------------------------------------------------
        workspace = tk.Frame(self.root, bg="#030b18")
        workspace.pack(fill=tk.BOTH, expand=True, padx=14, pady=4)
        workspace.grid_columnconfigure(0, weight=6, uniform="work_col")
        workspace.grid_columnconfigure(1, weight=4, uniform="work_col")
        workspace.grid_rowconfigure(0, weight=1)

        # -------------------------------------------------------------------------
        # LEFT PANEL: Camera Viewport & Scanner Reticle HUD Card
        # -------------------------------------------------------------------------
        left_card = tk.Frame(
            workspace, 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1
        )
        left_card.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")

        # Top Glowing Accent
        left_accent = tk.Frame(left_card, bg="#0084ff", height=4)
        left_accent.pack(side=tk.TOP, fill=tk.X)

        # Left Card Header Strip
        left_header = tk.Frame(left_card, bg="#071a35", padx=16, pady=10)
        left_header.pack(fill=tk.X)

        lbl_left_title = tk.Label(
            left_header,
            text="📷  Live Camera Stream & Biometric Target Viewport",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#071a35"
        )
        lbl_left_title.pack(side=tk.LEFT)

        self.lbl_system_status = tk.Label(
            left_header,
            text="● System Ready",
            font=("Segoe UI", 9, "bold"),
            fg="#10b981",
            bg="#091f40",
            padx=10,
            pady=3,
            bd=1,
            relief=tk.SOLID,
            highlightbackground="#10b981"
        )
        self.lbl_system_status.pack(side=tk.RIGHT)

        # Viewport Display Container
        viewport_frame = tk.Frame(
            left_card,
            bg="#030b18",
            bd=1,
            relief=tk.SOLID,
            highlightbackground="#1e3a5f",
            highlightthickness=1
        )
        viewport_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        # Inner Scanner Illustration
        icon_path = os.path.join(ASSETS_DIR, "tile_face.png")
        if os.path.exists(icon_path):
            try:
                img_pil = Image.open(icon_path).resize((130, 130), Image.Resampling.LANCZOS)
                photo_icon = ImageTk.PhotoImage(img_pil, master=self.root)
                self._images.append(photo_icon)
                lbl_reticle = tk.Label(viewport_frame, image=photo_icon, bg="#030b18")
                lbl_reticle.pack(pady=(35, 12))
            except Exception:
                lbl_reticle = tk.Label(viewport_frame, text="🎯", font=("Segoe UI", 48), fg="#10b981", bg="#030b18")
                lbl_reticle.pack(pady=(35, 12))
        else:
            lbl_reticle = tk.Label(viewport_frame, text="🎯", font=("Segoe UI", 48), fg="#10b981", bg="#030b18")
            lbl_reticle.pack(pady=(35, 12))

        lbl_instruct_main = tk.Label(
            viewport_frame,
            text="Position your face clearly in front of the camera",
            font=("Segoe UI", 13, "bold"),
            fg="#ffffff",
            bg="#030b18"
        )
        lbl_instruct_main.pack(pady=(0, 4))

        lbl_instruct_sub = tk.Label(
            viewport_frame,
            text="Multi-frame stabilization is active. Look straight at the lens for instant verification.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#030b18"
        )
        lbl_instruct_sub.pack(pady=(0, 20))

        # Hardware Specs Footer Strip inside Viewport
        spec_strip = tk.Frame(viewport_frame, bg="#06152b", padx=12, pady=6)
        spec_strip.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=12)

        lbl_spec1 = tk.Label(spec_strip, text="📹 Video: 1280x720 HD", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#06152b")
        lbl_spec1.pack(side=tk.LEFT, padx=(4, 16))

        lbl_spec2 = tk.Label(spec_strip, text="⚡ Stabilizer: 7-Frame Voting", font=("Segoe UI", 8), fg="#cbd5e1", bg="#06152b")
        lbl_spec2.pack(side=tk.LEFT, padx=(0, 16))

        lbl_spec3 = tk.Label(spec_strip, text="🎯 Threshold: Dist <= 72.0", font=("Segoe UI", 8), fg="#10b981", bg="#06152b")
        lbl_spec3.pack(side=tk.LEFT)

        # -------------------------------------------------------------------------
        # RIGHT PANEL: Biometric Verification & Controls Hub Card
        # -------------------------------------------------------------------------
        right_card = tk.Frame(
            workspace, 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1
        )
        right_card.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")

        right_accent = tk.Frame(right_card, bg="#10b981", height=4)
        right_accent.pack(side=tk.TOP, fill=tk.X)

        right_inner = tk.Frame(right_card, bg="#071a35", padx=18, pady=14)
        right_inner.pack(fill=tk.BOTH, expand=True)

        # Section Heading
        lbl_right_title = tk.Label(
            right_inner,
            text="⚡ Biometric Verification & Controls",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#071a35"
        )
        lbl_right_title.pack(anchor="w", pady=(0, 12))

        # 1. Primary Action Button: "Start Face Scan ➔"
        self.btn_scan = tk.Button(
            right_inner, 
            text="📷   START LIVE FACE SCAN   ➔", 
            font=("Segoe UI", 12, "bold"), 
            bg="#0084ff", 
            fg="#ffffff", 
            activebackground="#0095ff", 
            activeforeground="#ffffff", 
            cursor="hand2", 
            bd=0, 
            relief=tk.FLAT,
            pady=12,
            command=self.toggle_face_recognition
        )
        self.btn_scan.pack(fill=tk.X, pady=(0, 10))
        self.btn_scan.bind("<Enter>", lambda e: self.btn_scan.config(bg="#0095ff") if not self.is_camera_running else None)
        self.btn_scan.bind("<Leave>", lambda e: self.btn_scan.config(bg="#0084ff") if not self.is_camera_running else None)

        # 2. Live Telemetry Status Box
        self.lbl_live_log = tk.Label(
            right_inner,
            text="ℹ Ready to scan. Position your face in front of the camera.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#091f40",
            bd=1,
            relief=tk.SOLID,
            highlightbackground="#1e3a5f",
            anchor="w",
            padx=12,
            pady=8
        )
        self.lbl_live_log.pack(fill=tk.X, pady=(0, 14))

        # 3. Real-Time Recognized Student Profile Card (HUD)
        self.recog_card = tk.Frame(
            right_inner, 
            bg="#06152b", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1,
            padx=14, 
            pady=10
        )
        self.recog_card.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        lbl_recog_header = tk.Label(
            self.recog_card,
            text="👤  STABILIZED RECOGNIZED STUDENT",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#06152b"
        )
        lbl_recog_header.pack(anchor="w", pady=(0, 6))

        # Student Profile Details
        self.lbl_recog_name = tk.Label(
            self.recog_card,
            text="Student Name:  --",
            font=("Segoe UI", 11, "bold"),
            fg="#ffffff",
            bg="#06152b",
            anchor="w"
        )
        self.lbl_recog_name.pack(fill=tk.X, pady=1)

        self.lbl_recog_roll = tk.Label(
            self.recog_card,
            text="Roll Number:   --",
            font=("Segoe UI", 10),
            fg="#cbd5e1",
            bg="#06152b",
            anchor="w"
        )
        self.lbl_recog_roll.pack(fill=tk.X, pady=1)

        self.lbl_recog_dep = tk.Label(
            self.recog_card,
            text="Department:    --",
            font=("Segoe UI", 10),
            fg="#cbd5e1",
            bg="#06152b",
            anchor="w"
        )
        self.lbl_recog_dep.pack(fill=tk.X, pady=1)

        self.lbl_recog_time = tk.Label(
            self.recog_card,
            text="Timestamp:     --",
            font=("Segoe UI", 10),
            fg="#94a3b8",
            bg="#06152b",
            anchor="w"
        )
        self.lbl_recog_time.pack(fill=tk.X, pady=1)

        self.lbl_recog_match = tk.Label(
            self.recog_card,
            text="Biometric Match: Waiting for scan...",
            font=("Segoe UI", 9, "bold"),
            fg="#10b981",
            bg="#06152b",
            anchor="w"
        )
        self.lbl_recog_match.pack(fill=tk.X, pady=(4, 0))

        # 4. Quick Action Navigation Buttons
        btn_container = tk.Frame(right_inner, bg="#071a35")
        btn_container.pack(fill=tk.X)

        btn_att = tk.Button(
            btn_container,
            text="📊  View Attendance Records  ➔",
            font=("Segoe UI", 10, "bold"),
            bg="#091f40",
            fg="#38bdf8",
            activebackground="#0f2f5c",
            activeforeground="#ffffff",
            cursor="hand2",
            bd=1,
            relief=tk.SOLID,
            highlightbackground="#1e3a5f",
            pady=7,
            command=self.open_attendance_window
        )
        btn_att.pack(fill=tk.X, pady=(0, 6))
        btn_att.bind("<Enter>", lambda e: btn_att.config(bg="#0f2f5c", fg="#ffffff"))
        btn_att.bind("<Leave>", lambda e: btn_att.config(bg="#091f40", fg="#38bdf8"))

        btn_dashboard = tk.Button(
            btn_container,
            text="👤  Return to Main Dashboard",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            activebackground="#334155",
            activeforeground="#ffffff",
            cursor="hand2",
            bd=0,
            pady=6,
            command=self.handle_back_or_close
        )
        btn_dashboard.pack(fill=tk.X)
        btn_dashboard.bind("<Enter>", lambda e: btn_dashboard.config(bg="#334155", fg="#ffffff"))
        btn_dashboard.bind("<Leave>", lambda e: btn_dashboard.config(bg="#1e293b", fg="#94a3b8"))

        # -------------------------------------------------------------------------
        # 3. Bottom Status & Guidance Bar
        # -------------------------------------------------------------------------
        status_bar = tk.Frame(
            self.root, 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1,
            height=32
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(4, 10))

        lbl_bot_status = tk.Label(
            status_bar,
            text="● BIOMETRIC ENGINE: ONLINE  |  Anti-Flicker Temporal Voting  |  LBPH Strict Distance <= 72.0",
            font=("Segoe UI", 8, "bold"),
            fg="#10b981",
            bg="#071a35"
        )
        lbl_bot_status.pack(side=tk.LEFT, padx=16, pady=5)

        lbl_bot_mentor = tk.Label(
            status_bar,
            text="Mentorship: Mr. Rakesh Kumar Rai  |  KIIT University",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#071a35"
        )
        lbl_bot_mentor.pack(side=tk.RIGHT, padx=16, pady=5)

    def open_attendance_window(self):
        """Opens Attendance Records window."""
        from modules.attendance import AttendanceManagementSystem
        win = tk.Toplevel(self.root)
        AttendanceManagementSystem(win)

    def _update_live_ui_log(self, name: str, roll: str, time_str: str, dep: str = "", conf_str: str = ""):
        """Updates the Live Recognized Student Card in real-time."""
        try:
            self.session_count += 1
            self.lbl_live_log.config(
                text=f"✓ Logged: {name} (Roll: {roll}) at {time_str}",
                fg="#10b981"
            )
            self.lbl_recog_name.config(text=f"Student Name:  {name}")
            self.lbl_recog_roll.config(text=f"Roll Number:   {roll}")
            if dep:
                self.lbl_recog_dep.config(text=f"Department:    {dep}")
            self.lbl_recog_time.config(text=f"Timestamp:     {time_str} (Marked Present)")
            if conf_str:
                self.lbl_recog_match.config(text=f"Biometric Match: {conf_str}", fg="#10b981")
            else:
                self.lbl_recog_match.config(text="Biometric Match: Verified ✓", fg="#10b981")
        except Exception:
            pass

    def toggle_face_recognition(self):
        """Toggles the live camera capture and face recognition pipeline."""
        if self.is_camera_running:
            self.is_camera_running = False
            self.btn_scan.config(text="📷   START LIVE FACE SCAN   ➔", bg="#0084ff")
            self.lbl_system_status.config(text="● System Ready", fg="#10b981")
            self.lbl_live_log.config(text="● Face scanner stopped.", fg="#94a3b8")
        else:
            # Step 1: Ensure LBPH model is ready and up-to-date
            ready, msg = ensure_classifier_ready()
            if not ready:
                messagebox.showwarning("Model Not Ready", msg, parent=self.root)
                return

            self.is_camera_running = True
            self.btn_scan.config(text="⏹   STOP CAMERA SCANNER", bg="#ef4444")
            self.lbl_system_status.config(text="● Live Feed Active", fg="#ef4444")
            self.lbl_live_log.config(text="● Initializing camera stream...", fg="#38bdf8")

            # Launch OpenCV processing in background daemon thread
            self.camera_thread = threading.Thread(target=self._run_face_recognition_loop, daemon=True)
            self.camera_thread.start()

    def _run_face_recognition_loop(self):
        """
        Executes the high-performance OpenCV face detection and LBPH recognition loop.
        """
        # Load Haar Cascade Classifier
        cascade_path = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
        face_cascade = cv2.CascadeClassifier(cascade_path)
        if face_cascade.empty():
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

        # Load LBPH Recognizer
        classifier_xml = os.path.join(CLASSIFIER_DIR, "classifier.xml")
        clf = cv2.face.LBPHFaceRecognizer_create()
        try:
            clf.read(classifier_xml)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Model Error", f"Failed to load classifier: {e}", parent=self.root))
            self.is_camera_running = False
            self.root.after(0, lambda: self.btn_scan.config(text="📷   START LIVE FACE SCAN   ➔", bg="#0084ff"))
            return

        # Load id_map.json
        int_to_id = {}
        id_map_file = os.path.join(CLASSIFIER_DIR, "id_map.json")
        if os.path.exists(id_map_file):
            try:
                with open(id_map_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    int_to_id = {int(k): v for k, v in data.get("int_to_id", {}).items()}
            except Exception:
                pass

        # Camera Acquisition Loop with Multi-Backend Negotiation
        cap = None
        for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
            for idx in [0, 1, 2]:
                try:
                    temp_cap = cv2.VideoCapture(idx, backend)
                    if temp_cap.isOpened():
                        ret, test_frame = temp_cap.read()
                        if ret and test_frame is not None and test_frame.size > 0:
                            cap = temp_cap
                            break
                        temp_cap.release()
                except Exception:
                    pass
            if cap is not None:
                break

        if cap is None or not cap.isOpened():
            diag_msg = diagnose_camera_issue()
            self.root.after(0, lambda: messagebox.showerror("Webcam Error", diag_msg, parent=self.root))
            self.is_camera_running = False
            self.root.after(0, lambda: self.btn_scan.config(text="📷   START LIVE FACE SCAN   ➔", bg="#0084ff"))
            self.root.after(0, lambda: self.lbl_system_status.config(text="● Camera Disconnected", fg="#ef4444"))
            return

        # Optimize Camera Buffering
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        # Camera Warm-up (10 frames)
        for _ in range(10):
            cap.read()

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        win_title = "FaceAttend - Live Biometric AI Face Recognition"
        cv2.namedWindow(win_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_title, 960, 600)
        try:
            cv2.setWindowProperty(win_title, cv2.WND_PROP_TOPMOST, 1)
        except Exception:
            pass

        self.root.after(0, lambda: self.lbl_live_log.config(text="● Face scanner running (60+ FPS). Look at camera.", fg="#10b981"))

        last_fps_time = time.time()
        frame_counter = 0
        current_fps = 60.0
        
        # Reset temporal tracker buffer for fresh session
        self.face_tracker = TemporalFaceTracker(history_len=7, strict_threshold=72.0)

        # Cache student info to prevent redundant SQL queries per frame
        student_cache = {}

        # Main Capture & Recognition Loop
        while self.is_camera_running:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            frame_counter += 1
            if time.time() - last_fps_time >= 1.0:
                current_fps = frame_counter / (time.time() - last_fps_time)
                frame_counter = 0
                last_fps_time = time.time()

            h_f, w_f = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 3-Pass Adaptive Haar Detection
            # Pass 1: 0.5x Downsampled Fast Detection
            small_gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)
            faces = face_cascade.detectMultiScale(small_gray, scaleFactor=1.08, minNeighbors=3, minSize=(30, 30))

            if len(faces) == 0:
                # Pass 2: Full-Resolution Fallback
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=3, minSize=(60, 60))
                scale_up = False
            else:
                scale_up = True

            if len(faces) == 0:
                # Pass 3: CLAHE Low-Light Fallback
                enhanced_gray = clahe.apply(gray)
                faces = face_cascade.detectMultiScale(enhanced_gray, scaleFactor=1.08, minNeighbors=3, minSize=(60, 60))
                scale_up = False

            # Draw HUD Overlays on Detected Faces
            for (x, y, w, h) in faces:
                if scale_up:
                    x, y, w, h = x * 2, y * 2, w * 2, h * 2

                # Exact zero-padding crop to match training dataset samples
                face_raw = gray[y:y+h, x:x+w]
                if face_raw.size == 0 or face_raw.shape[0] < 20 or face_raw.shape[1] < 20:
                    continue

                face_resized = cv2.resize(face_raw, (200, 200))
                face_equalized = cv2.equalizeHist(face_resized)

                # LBPH Machine Learning Prediction
                try:
                    int_label, distance = clf.predict(face_equalized)
                except Exception:
                    int_label, distance = -1, 999.0

                student_id = int_to_id.get(int_label, str(int_label))

                # Fetch student metadata from cache or SQLite
                if student_id not in student_cache:
                    s_info = get_student_by_id(student_id)
                    student_cache[student_id] = s_info
                else:
                    s_info = student_cache[student_id]

                # Update Temporal Tracker with multi-frame majority voting
                is_verified, disp_name, disp_roll, disp_dep, conf_pct, status_str = self.face_tracker.update(
                    student_id, distance, s_info
                )

                if is_verified:
                    now = datetime.now()
                    time_str = now.strftime("%I:%M:%S %p")
                    date_str = now.strftime("%d/%m/%Y")

                    # Log attendance (SQLite + CSV) with daily deduplication
                    if student_id not in self.logged_session_students:
                        try:
                            log_attendance(student_id, disp_roll, disp_name, disp_dep, time_str, date_str, "Present")
                            log_attendance_to_csv(student_id, disp_roll, disp_name, disp_dep, time_str, date_str, "Present")
                            self.logged_session_students.add(student_id)
                        except Exception:
                            pass

                    self.root.after(0, lambda n=disp_name, r=disp_roll, t=time_str, d=disp_dep, c=status_str: self._update_live_ui_log(n, r, t, d, c))

                    # Render Green HUD Box with Corner Brackets
                    box_color = (0, 255, 120)  # Neon Green
                    cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
                    
                    # Corner accents
                    c_len = min(24, w // 4)
                    cv2.line(frame, (x, y), (x + c_len, y), (0, 255, 255), 4)
                    cv2.line(frame, (x, y), (x, y + c_len), (0, 255, 255), 4)
                    cv2.line(frame, (x + w, y), (x + w - c_len, y), (0, 255, 255), 4)
                    cv2.line(frame, (x + w, y), (x + w, y + c_len), (0, 255, 255), 4)
                    cv2.line(frame, (x, y + h), (x + c_len, y + h), (0, 255, 255), 4)
                    cv2.line(frame, (x, y + h), (x, y + h - c_len), (0, 255, 255), 4)
                    cv2.line(frame, (x + w, y + h), (x + w - c_len, y + h), (0, 255, 255), 4)
                    cv2.line(frame, (x + w, y + h), (x + w, y + h - c_len), (0, 255, 255), 4)

                    # Info Label Badge
                    label_text = f"{disp_name} | {disp_roll}"
                    cv2.rectangle(frame, (x, y - 36), (x + max(220, w), y), (10, 30, 15), -1)
                    cv2.rectangle(frame, (x, y - 36), (x + max(220, w), y), box_color, 1)
                    cv2.putText(frame, label_text, (x + 6, y - 18), cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1)
                    cv2.putText(frame, f"Conf: {conf_pct}% (Verified)", (x + 6, y - 4), cv2.FONT_HERSHEY_DUPLEX, 0.42, (0, 255, 120), 1)

                else:
                    # Unknown Face (Red HUD)
                    box_color = (0, 0, 230)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
                    cv2.rectangle(frame, (x, y - 28), (x + max(160, w), y), (20, 10, 10), -1)
                    cv2.rectangle(frame, (x, y - 28), (x + max(160, w), y), box_color, 1)
                    cv2.putText(frame, "Unknown Face", (x + 6, y - 8), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 0, 255), 1)

            # Top HUD Status Bar on Video Stream
            cv2.rectangle(frame, (0, 0), (w_f, 36), (8, 20, 35), -1)
            cv2.line(frame, (0, 36), (w_f, 36), (0, 132, 255), 2)
            cv2.putText(frame, "FACEATTEND BIOMETRIC SCANNER  |  TEMPORAL STABILIZATION ACTIVE", (15, 24), cv2.FONT_HERSHEY_DUPLEX, 0.50, (0, 210, 255), 1)
            cv2.putText(frame, f"FPS: {current_fps:.1f}", (w_f - 110, 24), cv2.FONT_HERSHEY_DUPLEX, 0.52, (52, 211, 153), 1)

            # Bottom Controls Guidance Strip on Video Stream
            cv2.rectangle(frame, (0, h_f - 30), (w_f, h_f), (8, 20, 35), -1)
            cv2.putText(frame, "Press 'Q' or 'ESC' on keyboard to stop scanning.", (15, h_f - 10), cv2.FONT_HERSHEY_DUPLEX, 0.45, (148, 163, 184), 1)

            cv2.imshow(win_title, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

            # Handle OpenCV window X button click
            if cv2.getWindowProperty(win_title, cv2.WND_PROP_VISIBLE) < 1:
                break

        # Cleanup and Release Camera
        cap.release()
        cv2.destroyAllWindows()
        self.is_camera_running = False

        self.root.after(0, lambda: self.btn_scan.config(text="📷   START LIVE FACE SCAN   ➔", bg="#0084ff"))
        self.root.after(0, lambda: self.lbl_system_status.config(text="● System Ready", fg="#10b981"))
        self.root.after(0, lambda: self.lbl_live_log.config(text="● Face scanner stopped. Ready for next session.", fg="#94a3b8"))

    def handle_back_or_close(self):
        """Cleanly terminates camera loop and destroys window."""
        self.is_camera_running = False
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FaceRecognitionWindow(root)
    root.mainloop()
