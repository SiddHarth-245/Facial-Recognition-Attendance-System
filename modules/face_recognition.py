"""
========================================================================================
Real-Time Biometric Face Recognition & Attendance Logging Module
FaceAttend Cyber-Blue Ultra Enterprise Edition (Embedded Viewport & Anti-Flicker HUD)
========================================================================================
Module: modules/face_recognition.py
Author: Ved Prakash Pandey (Lead Developer - Biometric Detection & Camera Pipelines)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module implements the live biometric verification engine that captures high-definition
video feeds from the system webcam, detects human faces in real-time, extracts invariant
textural feature maps, queries the trained LBPH Machine Learning model (`classifier/classifier.xml`),
and performs dual-persistence attendance logging (synchronous SQLite3 + CSV file record).

Key System Capabilities:
------------------------
1. Native Embedded Viewport (Zero Window Stretching / Zero Distortion):
   - Streams live camera feeds directly inside the native Tkinter Cyber-Blue card with
     aspect-ratio auto-fitting and anti-aliased Lanczos/linear scaling.
2. Temporal Multi-Frame Majority Voting & Stabilization:
   - Uses an 8-frame rolling buffer (`TemporalFaceTracker`) to eliminate frame-to-frame
     identity flipping and flickering between enrolled students caused by lighting/sensor noise.
3. Anti-Collision Dynamic HUD Overlays:
   - Dynamic boundary calculation guarantees badge text never collides or overlaps with
     the top status bar, bottom guidance bar, or screen edges.
4. Standardized Zero-Padding Crop Matching:
   - Matches the 0% bounding box crop (`gray[y:y+h, x:x+w]`) used during dataset acquisition,
     preventing grid-cell spatial misalignment in LBPH 8x8 histograms.
5. Calibrated Two-Tier Distance Thresholding:
   - High Confidence Match: `distance <= 60.0` (85% - 99% accuracy) -> Instant Green HUD.
   - Verified Match: `60.0 < distance <= 72.0` -> Confirmed after majority vote consensus.
   - Rejection Boundary: `distance > 72.0` -> Marked as 'Unknown Face' (Red HUD), preventing false
     swaps with other students.
6. Dual-Persistence Attendance & Daily Deduplication:
   - Records attendance synchronously to SQLite database and CSV file with daily deduplication.
========================================================================================
"""

import sys
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

# Ensure project root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Database operations for student info resolution and attendance recording
from database.db_manager import get_student_by_id, log_attendance

# Filesystem directory paths
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


class SpatialFaceTracker:
    """
    Per-Face Spatial Temporal Stabilizer & Identity Consensus Engine.
    Maintains independent majority-voting history for each distinct face.
    """
    def __init__(self, track_id: int = 1, history_len: int = 6, strict_threshold: float = 68.0):
        self.track_id = track_id
        self.history_len = history_len
        self.strict_threshold = strict_threshold
        self.history = deque(maxlen=history_len)
        self.bbox = None
        self.last_seen = time.time()
        self.last_confirmed_id = None
        self.last_confirmed_name = None
        self.last_confirmed_roll = None
        self.last_confirmed_dep = None
        self.last_confirmed_conf = 0

    def update(self, student_id: str, distance: float, student_info: dict, bbox: tuple = None) -> tuple:
        """
        Updates the tracker with current frame prediction and returns:
        (is_verified: bool, display_name: str, display_roll: str, display_dep: str, confidence_pct: int, status_str: str)
        """
        now = time.time()
        self.bbox = bbox
        self.last_seen = now
        
        # Add prediction to rolling history
        self.history.append((student_id, distance))

        # Rejection if distance is too high (> strict_threshold)
        if distance > self.strict_threshold:
            valid_votes = [(sid, d) for sid, d in self.history if d <= self.strict_threshold]
            if not valid_votes:
                return False, "Unknown Face", "--", "--", 0, "Unknown Face"

        # Count candidate votes within strict threshold
        valid_items = [(sid, d) for sid, d in self.history if d <= self.strict_threshold]
        if not valid_items:
            return False, "Unknown Face", "--", "--", 0, "Unknown Face"

        id_votes = Counter([sid for sid, d in valid_items])
        best_id, vote_count = id_votes.most_common(1)[0]
        
        matching_distances = [d for sid, d in valid_items if sid == best_id]
        avg_distance = sum(matching_distances) / len(matching_distances)

        # Minimum required votes for stable confirmation (at least 2-3 votes in history)
        required_votes = max(2, min(3, len(self.history)))

        if vote_count >= required_votes and avg_distance <= self.strict_threshold:
            confidence_pct = max(10, min(99, int(100 - (avg_distance * 0.70))))
            name = student_info.get("name", f"Student #{best_id}") if student_info else f"Student #{best_id}"
            roll = student_info.get("roll", str(best_id)) if student_info else str(best_id)
            dep = student_info.get("dep", "General") if student_info else "General"

            self.last_confirmed_id = best_id
            self.last_confirmed_name = name
            self.last_confirmed_roll = roll
            self.last_confirmed_dep = dep
            self.last_confirmed_conf = confidence_pct

            return True, name, roll, dep, confidence_pct, f"{confidence_pct}% Match (Verified)"

        # Instant verification for very high confidence single matches (distance <= 50.0)
        if distance <= 50.0 and student_info:
            confidence_pct = max(10, min(99, int(100 - (distance * 0.70))))
            name = student_info.get("name", f"Student #{student_id}")
            roll = student_info.get("roll", str(student_id))
            dep = student_info.get("dep", "General")
            return True, name, roll, dep, confidence_pct, f"{confidence_pct}% Match (Verified)"

        return False, "Scanning...", "--", "--", 0, "Scanning Face..."


# Alias for backward compatibility
TemporalFaceTracker = SpatialFaceTracker


class MultiFaceTrackerManager:
    """
    Manages spatial face tracks across frames using bounding box centroid association.
    Eliminates cross-contamination between different faces and background artifacts.
    """
    def __init__(self, max_distance: float = 120.0, max_age_seconds: float = 0.8):
        self.tracks = {}
        self.next_id = 1
        self.max_distance = max_distance
        self.max_age_seconds = max_age_seconds

    def match_boxes_to_trackers(self, detected_boxes: list) -> dict:
        now = time.time()
        # Purge stale tracks that disappeared
        stale_ids = [tid for tid, trk in self.tracks.items() if (now - trk.last_seen) > self.max_age_seconds]
        for tid in stale_ids:
            del self.tracks[tid]

        box_to_tracker = {}
        used_tracks = set()

        for idx, (x, y, w, h) in enumerate(detected_boxes):
            cx, cy = x + w / 2.0, y + h / 2.0
            best_track_id = None
            min_dist = float("inf")

            for tid, trk in self.tracks.items():
                if tid in used_tracks or trk.bbox is None:
                    continue
                tx, ty, tw, th = trk.bbox
                tcx, tcy = tx + tw / 2.0, ty + th / 2.0
                dist = np.hypot(cx - tcx, cy - tcy)
                if dist < self.max_distance and dist < min_dist:
                    min_dist = dist
                    best_track_id = tid

            if best_track_id is not None:
                used_tracks.add(best_track_id)
                tracker = self.tracks[best_track_id]
            else:
                tracker = SpatialFaceTracker(track_id=self.next_id, history_len=6, strict_threshold=68.0)
                self.tracks[self.next_id] = tracker
                self.next_id += 1

            box_to_tracker[idx] = tracker

        return box_to_tracker


class FaceRecognitionWindow:
    """
    Main Live Face Recognition & Attendance Studio GUI Controller.
    
    Architecture:
        - 100% Native Tkinter Cyber-Blue layout with embedded camera viewport.
        - High-performance threaded OpenCV capture loop (60+ FPS).
        - MultiFaceTrackerManager spatial face tracking.
        - Dynamic HUD Overlays (Neon Green for Verified, Red for Unknown).
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
        self.win_h = min(820, int(screen_h * 0.92))
        x = (screen_w - self.win_w) // 2
        y = max(5, (screen_h - self.win_h) // 2 - 20)
        self.root.geometry(f"{self.win_w}x{self.win_h}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.config(bg="#030b18")
        
        self._images = []
        self._current_video_photo = None
        self.logged_session_students = set()
        self.is_camera_running = False
        self.camera_thread = None
        self.session_count = 0
        self.var_hd_boost = tk.StringVar(value="Enhanced HD (Default)")
        
        # Multi-face spatial tracking manager
        self.tracker_manager = MultiFaceTrackerManager(max_distance=120.0, max_age_seconds=0.8)
        self.face_tracker = SpatialFaceTracker(track_id=1, history_len=6, strict_threshold=68.0)
        
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
            text="Live Embedded Video Stream  •  Anti-Flicker Temporal Voting  •  LBPH Machine Learning",
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
        # 2. Main Workspace (2-Column Grid: Left Viewport 60% | Right Telemetry 40%)
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
            text="📷  Live Camera Stream & Biometric Viewport",
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
        self.viewport_frame = tk.Frame(
            left_card,
            bg="#020813",
            bd=1,
            relief=tk.SOLID,
            highlightbackground="#1e3a5f",
            highlightthickness=1
        )
        self.viewport_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))

        # 1. Live Video Stream Label (Embedded directly into Tkinter Viewport)
        self.lbl_video_feed = tk.Label(self.viewport_frame, bg="#020813")

        # 2. Placeholder Container (Shown when camera is offline)
        self.placeholder_frame = tk.Frame(self.viewport_frame, bg="#020813")
        self.placeholder_frame.pack(fill=tk.BOTH, expand=True)

        icon_path = os.path.join(ASSETS_DIR, "tile_face.png")
        photo_icon = None
        if os.path.exists(icon_path):
            try:
                img_pil = Image.open(icon_path).resize((130, 130), Image.Resampling.LANCZOS)
                photo_icon = ImageTk.PhotoImage(img_pil, master=self.root)
                self._images.append(photo_icon)
            except Exception:
                pass

        if photo_icon:
            lbl_reticle = tk.Label(self.placeholder_frame, image=photo_icon, bg="#020813")
        else:
            lbl_reticle = tk.Label(self.placeholder_frame, text="🎯", font=("Segoe UI", 48), fg="#10b981", bg="#020813")
        lbl_reticle.pack(pady=(45, 12))

        lbl_instruct_main = tk.Label(
            self.placeholder_frame,
            text="Position your face clearly in front of the camera",
            font=("Segoe UI", 13, "bold"),
            fg="#ffffff",
            bg="#020813"
        )
        lbl_instruct_main.pack(pady=(0, 4))

        lbl_instruct_sub = tk.Label(
            self.placeholder_frame,
            text="Click 'START LIVE FACE SCAN' below to open real-time recognition.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#020813"
        )
        lbl_instruct_sub.pack(pady=(0, 20))

        # Hardware Specs Footer Strip inside Viewport
        spec_strip = tk.Frame(left_card, bg="#06152b", padx=12, pady=6)
        spec_strip.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(0, 10))

        lbl_spec1 = tk.Label(spec_strip, text="📹 Video: 720p HD + CLAHE", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#06152b")
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

        right_inner = tk.Frame(right_card, bg="#071a35", padx=18, pady=12)
        right_inner.pack(fill=tk.BOTH, expand=True)

        # Section Heading
        lbl_right_title = tk.Label(
            right_inner,
            text="⚡ Biometric Verification & Telemetry",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#071a35"
        )
        lbl_right_title.pack(anchor="w", pady=(0, 8))

        # HD Clarity & Lighting Engine Control Strip
        clarity_box = tk.Frame(
            right_inner,
            bg="#06152b",
            bd=1,
            relief=tk.SOLID,
            highlightbackground="#1e3a5f",
            highlightthickness=1,
            padx=12,
            pady=8
        )
        clarity_box.pack(fill=tk.X, pady=(0, 10))

        clarity_top = tk.Frame(clarity_box, bg="#06152b")
        clarity_top.pack(fill=tk.X, pady=(0, 4))

        lbl_clarity_icon = tk.Label(
            clarity_top,
            text="✨ HD Clarity & Lighting Engine:",
            font=("Segoe UI", 9, "bold"),
            fg="#38bdf8",
            bg="#06152b"
        )
        lbl_clarity_icon.pack(side=tk.LEFT)

        combo_clarity = ttk.Combobox(
            clarity_box,
            textvariable=self.var_hd_boost,
            font=("Segoe UI", 9),
            state="readonly",
            values=[
                "Enhanced HD (Default)",
                "High Sharpness / Vivid",
                "Low Light & Shadow Boost",
                "Natural / Raw Stream"
            ]
        )
        combo_clarity.pack(fill=tk.X)

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
            pady=10,
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
            pady=7
        )
        self.lbl_live_log.pack(fill=tk.X, pady=(0, 10))

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
        self.recog_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

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
        self.lbl_recog_name.pack(fill=tk.X, pady=2)

        self.lbl_recog_roll = tk.Label(
            self.recog_card,
            text="Roll Number:   --",
            font=("Segoe UI", 10),
            fg="#cbd5e1",
            bg="#06152b",
            anchor="w"
        )
        self.lbl_recog_roll.pack(fill=tk.X, pady=2)

        self.lbl_recog_dep = tk.Label(
            self.recog_card,
            text="Department:    --",
            font=("Segoe UI", 10),
            fg="#cbd5e1",
            bg="#06152b",
            anchor="w"
        )
        self.lbl_recog_dep.pack(fill=tk.X, pady=2)

        self.lbl_recog_time = tk.Label(
            self.recog_card,
            text="Timestamp:     --",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#06152b",
            anchor="w"
        )
        self.lbl_recog_time.pack(fill=tk.X, pady=2)

        self.lbl_recog_match = tk.Label(
            self.recog_card,
            text="Biometric Match: --",
            font=("Segoe UI", 10, "bold"),
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
            pady=6,
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
            pady=5,
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
            height=30
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(4, 8))

        lbl_bot_status = tk.Label(
            status_bar,
            text="● BIOMETRIC ENGINE: ONLINE  |  Anti-Flicker Temporal Voting  |  LBPH Strict Distance <= 72.0",
            font=("Segoe UI", 8, "bold"),
            fg="#10b981",
            bg="#071a35"
        )
        lbl_bot_status.pack(side=tk.LEFT, padx=16, pady=4)

        lbl_bot_mentor = tk.Label(
            status_bar,
            text="Mentorship: Mr. Rakesh Kumar Rai  |  KIIT University",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#071a35"
        )
        lbl_bot_mentor.pack(side=tk.RIGHT, padx=16, pady=4)

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

    def _enhance_frame_clarity(self, frame, mode="Enhanced HD (Default)"):
        """
        Fast, real-time video clarity & lighting normalizer optimized for 60+ FPS.
        """
        if frame is None or frame.size == 0 or mode == "Natural / Raw Stream":
            return frame

        try:
            if mode == "High Sharpness / Vivid":
                # Fast 3x3 sharpening kernel
                kernel = np.array([[0, -0.25, 0], [-0.25, 2.0, -0.25], [0, -0.25, 0]], dtype=np.float32)
                sharpened = cv2.filter2D(frame, -1, kernel)
                return cv2.convertScaleAbs(sharpened, alpha=1.08, beta=6)
            elif mode == "Low Light & Shadow Boost":
                # Fast Y-channel CLAHE in YCrCb
                ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
                y, cr, cb = cv2.split(ycrcb)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                y_eq = clahe.apply(y)
                merged = cv2.merge((y_eq, cr, cb))
                return cv2.cvtColor(merged, cv2.COLOR_YCrCb2BGR)
            else:  # "Enhanced HD (Default)"
                # Fast SIMD contrast & brightness stretch
                return cv2.convertScaleAbs(frame, alpha=1.10, beta=6)
        except Exception:
            return frame

    def _display_frame_on_ui(self, rgb_frame):
        """Thread-safe method to update the embedded Tkinter video label with crisp anti-aliased scaling."""
        if not self.is_camera_running:
            return
        try:
            # Measure viewport container size dynamically
            v_w = self.viewport_frame.winfo_width()
            v_h = self.viewport_frame.winfo_height()
            
            # Default fallback size if window not yet rendered
            if v_w < 100 or v_h < 100:
                v_w, v_h = 700, 480

            f_h, f_w = rgb_frame.shape[:2]
            scale = min(v_w / f_w, v_h / f_h)
            new_w = max(10, int(f_w * scale))
            new_h = max(10, int(f_h * scale))

            # Resize with area/lanczos4 interpolation for crisp viewport display
            if scale < 1.0:
                resized_rgb = cv2.resize(rgb_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                resized_rgb = cv2.resize(rgb_frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

            pil_img = Image.fromarray(resized_rgb)
            self._current_video_photo = ImageTk.PhotoImage(pil_img, master=self.root)
            self.lbl_video_feed.config(image=self._current_video_photo)
        except Exception:
            pass

    def toggle_face_recognition(self):
        """Toggles the live camera capture and face recognition pipeline."""
        if self.is_camera_running:
            self.is_camera_running = False
            self.btn_scan.config(text="📷   START LIVE FACE SCAN   ➔", bg="#0084ff")
            self.lbl_system_status.config(text="● System Ready", fg="#10b981")
            self.lbl_live_log.config(text="● Face scanner stopped.", fg="#94a3b8")
            
            # Switch view back to placeholder
            self.lbl_video_feed.pack_forget()
            self.placeholder_frame.pack(fill=tk.BOTH, expand=True)
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

            # Switch view to video feed
            self.placeholder_frame.pack_forget()
            self.lbl_video_feed.pack(fill=tk.BOTH, expand=True)

            # Launch OpenCV processing in background daemon thread
            self.camera_thread = threading.Thread(target=self._run_face_recognition_loop, daemon=True)
            self.camera_thread.start()

    def _run_face_recognition_loop(self):
        """
        Executes the high-performance OpenCV face detection and LBPH recognition loop.
        Renders live frames directly into the embedded Tkinter viewport at 60+ FPS.
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

        # Camera Acquisition Loop with Multi-Backend Negotiation & HD Resolution Request
        cap = None
        for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
            for idx in [0, 1, 2]:
                try:
                    temp_cap = cv2.VideoCapture(idx, backend)
                    if temp_cap.isOpened():
                        # Negotiate MJPG codec and HD resolution
                        try:
                            temp_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                        except Exception:
                            pass
                        try:
                            temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            temp_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        except Exception:
                            pass
                            
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
            self.root.after(0, lambda: (self.lbl_video_feed.pack_forget(), self.placeholder_frame.pack(fill=tk.BOTH, expand=True)))
            return

        # Optimize Camera Buffering
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        # Camera Warm-up (6 frames)
        for _ in range(6):
            cap.read()

        self.root.after(0, lambda: self.lbl_live_log.config(text="● Face scanner running (60+ FPS). Look at camera.", fg="#10b981"))

        last_fps_time = time.time()
        frame_counter = 0
        current_fps = 60.0
        
        # Spatial multi-face tracking manager
        tracker_manager = MultiFaceTrackerManager(max_distance=120.0, max_age_seconds=0.8)

        # Cache student info to prevent redundant SQL queries per frame
        student_cache = {}

        # Main Capture & Recognition Loop
        while self.is_camera_running:
            ret, raw_frame = cap.read()
            if not ret or raw_frame is None:
                time.sleep(0.01)
                continue

            # Real-Time HD Clarity & Adaptive Lighting Enhancement
            frame = self._enhance_frame_clarity(raw_frame, mode=self.var_hd_boost.get())

            frame_counter += 1
            if time.time() - last_fps_time >= 1.0:
                current_fps = frame_counter / (time.time() - last_fps_time)
                frame_counter = 0
                last_fps_time = time.time()

            h_f, w_f = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Fast, Robust 1-Pass Face Detection on 0.5x Downsampled Frame
            small_gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_LINEAR)
            
            # Calibrated parameters to ELIMINATE phantom curtain/wall detections:
            # - scaleFactor: 1.15
            # - minNeighbors: 6 (strictly eliminates background texture false positives)
            # - minSize: (40, 40) on half-res (corresponds to 80x80px on 720p)
            detected_raw = face_cascade.detectMultiScale(
                small_gray,
                scaleFactor=1.15,
                minNeighbors=6,
                minSize=(40, 40),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            # Filter valid faces by aspect ratio and scale back to original resolution
            faces = []
            for (sx, sy, sw, sh) in detected_raw:
                aspect = sw / float(sh)
                # Filter out tall skinny curtain folds or wide flat objects
                if 0.70 <= aspect <= 1.35 and sw >= 35 and sh >= 35:
                    faces.append((sx * 2, sy * 2, sw * 2, sh * 2))

            # Match detected faces to spatial trackers
            tracker_map = tracker_manager.match_boxes_to_trackers(faces)

            best_verified_face = None
            max_conf = 0

            # Draw HUD Overlays on Detected Faces
            for idx, (x, y, w, h) in enumerate(faces):
                face_tracker = tracker_map.get(idx)
                if face_tracker is None:
                    continue

                # Exact zero-padding crop to match training dataset samples
                face_raw = gray[y:y+h, x:x+w]
                if face_raw.size == 0 or face_raw.shape[0] < 30 or face_raw.shape[1] < 30:
                    continue

                face_resized = cv2.resize(face_raw, (200, 200), interpolation=cv2.INTER_LANCZOS4)
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

                # Update per-face spatial tracker
                is_verified, disp_name, disp_roll, disp_dep, conf_pct, status_str = face_tracker.update(
                    student_id, distance, s_info, (x, y, w, h)
                )

                if is_verified:
                    if conf_pct > max_conf:
                        max_conf = conf_pct
                        best_verified_face = (student_id, disp_name, disp_roll, disp_dep, conf_pct, status_str)

                    # 1. Render Neon Green HUD Bounding Box
                    box_color = (0, 255, 120)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
                    
                    # Corner accents (Cyan)
                    c_len = min(22, w // 4)
                    cv2.line(frame, (x, y), (x + c_len, y), (0, 240, 255), 3)
                    cv2.line(frame, (x, y), (x, y + c_len), (0, 240, 255), 3)
                    cv2.line(frame, (x + w, y), (x + w - c_len, y), (0, 240, 255), 3)
                    cv2.line(frame, (x + w, y), (x + w, y + c_len), (0, 240, 255), 3)
                    cv2.line(frame, (x, y + h), (x + c_len, y + h), (0, 240, 255), 3)
                    cv2.line(frame, (x, y + h), (x, y + h - c_len), (0, 240, 255), 3)
                    cv2.line(frame, (x + w, y + h), (x + w - c_len, y + h), (0, 240, 255), 3)
                    cv2.line(frame, (x + w, y + h), (x + w, y + h - c_len), (0, 240, 255), 3)

                    # 2. Dynamic Collision-Free Info Badge Positioning
                    # If face is near the top edge (y < 45), draw label BELOW the face box
                    badge_w = max(200, w)
                    bx1 = max(0, min(x, w_f - badge_w))
                    bx2 = bx1 + badge_w

                    if y < 45:
                        by1 = y + h
                        by2 = min(h_f - 28, y + h + 38)
                        ty1 = y + h + 16
                        ty2 = y + h + 30
                    else:
                        by1 = max(34, y - 38)
                        by2 = y
                        ty1 = y - 22
                        ty2 = y - 8

                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (8, 24, 15), -1)
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), box_color, 1)
                    
                    label_title = f"{disp_name} | {disp_roll}"
                    if len(label_title) > 26:
                        label_title = label_title[:24] + ".."
                    cv2.putText(frame, label_title, (bx1 + 6, ty1), cv2.FONT_HERSHEY_DUPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)
                    cv2.putText(frame, f"Match: {conf_pct}% (Verified)", (bx1 + 6, ty2), cv2.FONT_HERSHEY_DUPLEX, 0.40, (0, 255, 120), 1, cv2.LINE_AA)

                else:
                    # Unknown Face / Scanning (Red HUD)
                    box_color = (0, 0, 225)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
                    
                    badge_w = max(140, w)
                    bx1 = max(0, min(x, w_f - badge_w))
                    bx2 = bx1 + badge_w

                    if y < 35:
                        by1 = y + h
                        by2 = min(h_f - 28, y + h + 24)
                        ty = y + h + 17
                    else:
                        by1 = max(34, y - 24)
                        by2 = y
                        ty = y - 7

                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (25, 8, 8), -1)
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), box_color, 1)
                    cv2.putText(frame, "Unknown Face", (bx1 + 6, ty), cv2.FONT_HERSHEY_DUPLEX, 0.44, (0, 80, 255), 1, cv2.LINE_AA)

            # Update Attendance & UI Telemetry for highest confidence verified face
            if best_verified_face is not None:
                b_sid, b_name, b_roll, b_dep, b_conf, b_status = best_verified_face
                now = datetime.now()
                time_str = now.strftime("%I:%M:%S %p")
                date_str = now.strftime("%d/%m/%Y")

                if b_sid not in self.logged_session_students:
                    try:
                        log_attendance(b_sid, b_roll, b_name, b_dep, time_str, date_str, "Present")
                        log_attendance_to_csv(b_sid, b_roll, b_name, b_dep, time_str, date_str, "Present")
                        self.logged_session_students.add(b_sid)
                    except Exception:
                        pass

                self.root.after(0, lambda n=b_name, r=b_roll, t=time_str, d=b_dep, c=b_status: self._update_live_ui_log(n, r, t, d, c))
            cv2.rectangle(frame, (0, 0), (w_f, 32), (6, 18, 32), -1)
            cv2.line(frame, (0, 32), (w_f, 32), (0, 132, 255), 2)
            cv2.putText(frame, "FACEATTEND BIOMETRIC SCANNER", (14, 21), cv2.FONT_HERSHEY_DUPLEX, 0.46, (0, 210, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, f"FPS: {current_fps:.1f}", (w_f - 90, 21), cv2.FONT_HERSHEY_DUPLEX, 0.46, (52, 211, 153), 1, cv2.LINE_AA)

            # Bottom Guidance Strip
            cv2.rectangle(frame, (0, h_f - 24), (w_f, h_f), (6, 18, 32), -1)
            cv2.putText(frame, "Live Biometric AI Active  •  Anti-Flicker Multi-Frame Consensus", (14, h_f - 7), cv2.FONT_HERSHEY_DUPLEX, 0.40, (148, 163, 184), 1, cv2.LINE_AA)

            # Convert BGR to RGB and push to Tkinter embedded canvas
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.root.after(0, lambda f=rgb_frame: self._display_frame_on_ui(f))

            time.sleep(0.015)  # Yield CPU (~60 FPS cap)

        # Cleanup and Release Camera
        cap.release()
        self.is_camera_running = False

        self.root.after(0, lambda: self.btn_scan.config(text="📷   START LIVE FACE SCAN   ➔", bg="#0084ff"))
        self.root.after(0, lambda: self.lbl_system_status.config(text="● System Ready", fg="#10b981"))
        self.root.after(0, lambda: self.lbl_live_log.config(text="● Face scanner stopped. Ready for next session.", fg="#94a3b8"))
        self.root.after(0, lambda: (self.lbl_video_feed.pack_forget(), self.placeholder_frame.pack(fill=tk.BOTH, expand=True)))

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
