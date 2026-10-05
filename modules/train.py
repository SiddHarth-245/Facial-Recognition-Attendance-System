import sys
"""
========================================================================================
Dataset Training & Classifier Model Compilation Module
========================================================================================
Module: train.py
Author: Siddharth Singh & Ved Prakash Pandey (Model Architecture & Machine Learning)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module implements the automated Biometric Machine Learning training pipeline for the
Facial Recognition Attendance Management System. It reads grayscale facial image tensors
from the `data/` directory, compiles unique integer-to-string identity mappings, extracts
Local Binary Patterns Histograms (LBPH) using multi-scale radial neighborhood operators,
and serializes the trained model into `classifier/classifier.xml` and `classifier/id_map.json`.

Machine Learning Architecture & Algorithm Details:
--------------------------------------------------
1. LBPH Algorithm (`cv2.face.LBPHFaceRecognizer_create`):
   - `radius = 2`: Circular neighborhood distance in pixels around the center pixel.
   - `neighbors = 8`: Number of sample points taken along the circular circumference.
   - `grid_x = 8`, `grid_y = 8`: Spatial division of the face ROI into an 8x8 spatial grid (64 cells).
2. Lighting Invariance & Spatial Preprocessing:
   - Every input sample is loaded in 8-bit grayscale (`cv2.IMREAD_GRAYSCALE`).
   - Resized to standard `200x200` resolution.
   - Processed via Histogram Equalization (`cv2.equalizeHist`).
3. Interactive Visual HUD Training Preview:
   - During training, a background thread renders an OpenCV visual feedback window ("Training").
========================================================================================
"""

import os
import glob
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np

# Enable Windows Per-Monitor High-DPI Awareness
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Database helper functions for mapping Student IDs to readable names
from database.db_manager import get_student_by_id, fetch_all_students

# Filesystem paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
CLASSIFIER_DIR = os.path.join(BASE_DIR, "classifier")

# Ensure target directories exist on the filesystem
os.makedirs(CLASSIFIER_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def train_classifier_core() -> tuple:
    """
    Core headless Machine Learning training routine.
    
    Reads all `user.<StudentID>.<SampleNum>.jpg` image files from `data/`,
    builds integer-to-string identity maps, trains an 8x8 cell LBPH recognizer,
    and writes `classifier.xml` and `id_map.json` to the `classifier/` directory.

    Returns:
    --------
    tuple: (success: bool, total_faces: int, student_counts: dict, message: str)
    """
    image_paths = glob.glob(os.path.join(DATA_DIR, "*.jpg"))
    if not image_paths:
        return False, 0, {}, "No face samples found in 'data/' directory."

    faces = []          # List of 200x200 equalized grayscale numpy image matrices
    ids = []            # List of corresponding integer labels for LBPH training
    id_to_int = {}      # String Student ID -> Sequential Integer Label (e.g. "23053645" -> 1)
    int_to_id = {}      # Sequential Integer Label -> String Student ID (e.g. "1" -> "23053645")
    student_counts = {} # Student ID -> Count of valid samples parsed
    next_int_id = 1

    # Group and sort image files by student ID for deterministic label indexing
    student_to_files = {}
    for img_path in sorted(image_paths):
        img_file = os.path.split(img_path)[1]
        parts = img_file.split(".")
        if len(parts) >= 3 and parts[0].lower() == "user":
            raw_id = parts[1]
            if raw_id not in student_to_files:
                student_to_files[raw_id] = []
            student_to_files[raw_id].append(img_path)

    if not student_to_files:
        return False, 0, {}, "No valid 'user.<student_id>.<num>.jpg' samples found."

    # Sort student IDs deterministically (numerical if digits, else string)
    sorted_ids = sorted(student_to_files.keys(), key=lambda s: (int(s) if s.isdigit() else float('inf'), s))
    for sid in sorted_ids:
        id_to_int[sid] = next_int_id
        int_to_id[str(next_int_id)] = sid
        next_int_id += 1

    # Load and process image samples
    for sid in sorted_ids:
        for img_path in student_to_files[sid]:
            try:
                img_gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                if img_gray is None:
                    continue
                img_eq = cv2.equalizeHist(cv2.resize(img_gray, (200, 200)))
                faces.append(img_eq)
                ids.append(id_to_int[sid])
                student_counts[sid] = student_counts.get(sid, 0) + 1
            except Exception as e:
                print(f"Error processing image {img_path}: {e}")
                continue

    if not faces or not ids:
        return False, 0, {}, "No valid face samples could be parsed."

    # Initialize and Train Local Binary Patterns Histograms (LBPH) Recognizer
    clf = cv2.face.LBPHFaceRecognizer_create(radius=2, neighbors=8, grid_x=8, grid_y=8)
    clf.train(faces, np.array(ids))

    # File serialization paths
    classifier_xml = os.path.join(CLASSIFIER_DIR, "classifier.xml")
    id_map_file = os.path.join(CLASSIFIER_DIR, "id_map.json")

    # Serialize trained model weights and ID lookup dictionaries
    clf.write(classifier_xml)
    with open(id_map_file, "w", encoding="utf-8") as f:
        json.dump({"id_to_int": id_to_int, "int_to_id": int_to_id}, f, indent=2)

    return True, len(faces), student_counts, f"Successfully trained on {len(faces)} face samples for {len(id_to_int)} student(s)."


class TrainDataWindow:
    """
    Graphical User Interface for interactive Model Training.
    
    Provides a visual dashboard with photographic banners, a one-click 'TRAIN DATA'
    action button, threaded asynchronous background training, and real-time visual HUD
    feedback window showcasing every student's dataset samples.
    """

    def __init__(self, root: tk.Tk):
        """
        Initializes the Train Data window, responsive geometry, and UI widgets.

        Parameters:
        -----------
        root : tk.Tk or tk.Toplevel
            Parent Tkinter root window hosting this interface.
        """
        self.root = root
        self.root.title("FaceAttend - LBPH Classifier Model Training")
        
        # Calculate dynamic responsive screen geometry
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1280, int(screen_w * 0.90))
        win_h = min(740, int(screen_h * 0.88))
        x = (screen_w - win_w) // 2
        y = max(10, (screen_h - win_h) // 2 - 20)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.config(bg="#030b18")
        
        # Image reference cache to prevent garbage collection
        self._images = []
        self.setup_ui()

    def setup_ui(self):
        """Constructs the visual components of the training window."""
        # -------------------------------------------------------------------------
        # 1. Top Header Bar
        # -------------------------------------------------------------------------
        top_bar = tk.Frame(self.root, bg="#071933", height=46)
        top_bar.pack(side=tk.TOP, fill=tk.X)

        lbl_title = tk.Label(
            top_bar, 
            text="⚡  NEURAL CLASSIFIER MODEL COMPILATION", 
            font=("Segoe UI", 12, "bold"), 
            fg="#ffffff", 
            bg="#071933"
        )
        lbl_title.pack(side=tk.LEFT, padx=18, pady=10)

        # Back Navigation Button (Top-Right)
        btn_back = tk.Button(
            top_bar, 
            text="✕  Back", 
            font=("Segoe UI", 9, "bold"), 
            bg="#0f213d", 
            fg="#ef4444", 
            activebackground="#1e3a5f", 
            activeforeground="#f87171", 
            bd=1, 
            relief=tk.SOLID, 
            padx=16, 
            pady=1,
            cursor="hand2",
            command=self.root.destroy
        )
        btn_back.pack(side=tk.RIGHT, padx=16, pady=8)

        # -------------------------------------------------------------------------
        # 2. Top Photographic Banner
        # -------------------------------------------------------------------------
        top_banner_path = os.path.join(ASSETS_DIR, "train_top_banner.png")
        if os.path.exists(top_banner_path):
            img_tb = Image.open(top_banner_path).resize((1366, 180), Image.Resampling.LANCZOS)
            photo_tb = ImageTk.PhotoImage(img_tb)
            self._images.append(photo_tb)
            lbl_top = tk.Label(self.root, image=photo_tb, bg="#030b18")
            lbl_top.pack(side=tk.TOP, fill=tk.X)

        # -------------------------------------------------------------------------
        # 3. Central Interactive Training Action Card
        # -------------------------------------------------------------------------
        action_card = tk.Frame(self.root, bg="#071a35", bd=1, relief=tk.SOLID)
        action_card.pack(fill=tk.X, padx=20, pady=(12, 10))

        self.btn_train = tk.Button(
            action_card, 
            text="⚡  START LBPH MODEL TRAINING  ➔", 
            font=("Segoe UI", 13, "bold"), 
            bg="#8b5cf6", 
            fg="#ffffff", 
            activebackground="#7c3aed", 
            activeforeground="#ffffff", 
            bd=0, 
            relief=tk.FLAT, 
            cursor="hand2", 
            command=self.handle_train_data
        )
        self.btn_train.pack(fill=tk.X, padx=16, pady=(14, 8), ipady=8)

        # Dynamic Hover Colors
        self.btn_train.bind("<Enter>", lambda e: self.btn_train.config(bg="#9333ea") if self.btn_train["state"] == tk.NORMAL else None)
        self.btn_train.bind("<Leave>", lambda e: self.btn_train.config(bg="#8b5cf6") if self.btn_train["state"] == tk.NORMAL else None)

        # Status & Progress strip under TRAIN DATA button
        self.lbl_status = tk.Label(
            action_card, 
            text="● Ready to compile facial datasets. Click 'START LBPH MODEL TRAINING' to begin.", 
            font=("Segoe UI", 9, "bold"), 
            bg="#071a35", 
            fg="#38bdf8",
            pady=6
        )
        self.lbl_status.pack(side=tk.TOP, fill=tk.X, padx=16, pady=(0, 10))

        # -------------------------------------------------------------------------
        # 4. Bottom Mosaic Photographic Wallpaper
        # -------------------------------------------------------------------------
        bottom_mosaic_path = os.path.join(ASSETS_DIR, "train_bottom_mosaic.jpg")
        if os.path.exists(bottom_mosaic_path):
            img_bm = Image.open(bottom_mosaic_path).resize((1366, 320), Image.Resampling.LANCZOS)
            photo_bm = ImageTk.PhotoImage(img_bm)
            self._images.append(photo_bm)
            lbl_bottom = tk.Label(self.root, image=photo_bm, bg="#030b18")
            lbl_bottom.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))

    def handle_train_data(self):
        """Disables UI button to prevent duplicates and spawns daemon training thread."""
        self.btn_train.config(state=tk.DISABLED, text="⏳ TRAINING IN PROGRESS...", bg="#475569")
        self.lbl_status.config(text="● Processing and training face datasets for all students...", fg="#f59e0b")
        threading.Thread(target=self._train_worker, daemon=True).start()

    def _train_worker(self):
        """Asynchronous background worker executing image scanning and model training."""
        all_files = glob.glob(os.path.join(DATA_DIR, "*.jpg"))
        if not all_files:
            self.root.after(0, lambda: messagebox.showerror(
                "Error", 
                "No photo samples found in 'data/' folder.\nPlease capture photos in Student Details first!",
                parent=self.root
            ))
            self.root.after(0, lambda: self.btn_train.config(state=tk.NORMAL, text="⚡ START LBPH MODEL TRAINING ➔", bg="#8b5cf6"))
            self.root.after(0, lambda: self.lbl_status.config(text="● Ready to train face datasets.", fg="#38bdf8"))
            return

        student_files = {}
        for f in all_files:
            fname = os.path.basename(f)
            parts = fname.split(".")
            if len(parts) >= 3 and parts[0].lower() == "user":
                sid = parts[1]
                if sid not in student_files:
                    student_files[sid] = []
                student_files[sid].append(f)

        total_students = len(student_files)
        win_title = "Training"
        cv2.namedWindow(win_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win_title, 480, 480)
        try:
            cv2.setWindowProperty(win_title, cv2.WND_PROP_TOPMOST, 1)
        except Exception:
            pass

        for s_idx, (sid, flist) in enumerate(student_files.items(), start=1):
            stu = get_student_by_id(sid)
            sname = stu["name"] if stu else f"Student {sid}"
            
            self.root.after(0, lambda s=sname, i=s_idx, tot=total_students: self.lbl_status.config(
                text=f"● Training Student {i}/{tot}: {s}...", fg="#38bdf8"
            ))

            preview_count = min(12, len(flist))
            step = max(1, len(flist) // preview_count)
            sample_subset = flist[::step][:preview_count]

            for img_path in sample_subset:
                try:
                    img_gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if img_gray is not None:
                        display_frame = cv2.cvtColor(cv2.resize(img_gray, (480, 480)), cv2.COLOR_GRAY2BGR)
                        
                        cv2.rectangle(display_frame, (0, 0), (480, 75), (20, 20, 30), -1)
                        cv2.putText(display_frame, "TRAINING DATASET - LBPH MODEL", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        cv2.putText(display_frame, f"Student: {sname} (ID: {sid})", (15, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
                        cv2.putText(display_frame, f"Student {s_idx}/{total_students} | {len(flist)} Samples", (15, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        
                        cv2.rectangle(display_frame, (0, 465), (480, 480), (30, 30, 30), -1)
                        prog_w = int(480 * (s_idx / total_students))
                        cv2.rectangle(display_frame, (0, 465), (prog_w, 480), (0, 200, 0), -1)

                        cv2.imshow(win_title, display_frame)
                        cv2.waitKey(20)
                except Exception:
                    pass

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        # Execute core model training and serialization
        success, total_count, counts, msg = train_classifier_core()

        if success:
            summary_lines = [
                "Training datasets completed successfully!\n",
                f"Total Face Samples Trained: {total_count}",
                f"Total Students Registered: {len(counts)}\n",
                "Trained Students Breakdown:"
            ]
            for sid, count in counts.items():
                stu = get_student_by_id(sid)
                sname = stu["name"] if stu else f"Student {sid}"
                sroll = f" (Roll: {stu['roll']})" if stu and stu.get("roll") else ""
                summary_lines.append(f"  • ID {sid}: {sname}{sroll} — {count} samples")

            summary_lines.append("\nAll students are now ready for Face Recognition!")
            final_msg = "\n".join(summary_lines)

            self.root.after(0, lambda: self.lbl_status.config(
                text=f"✓ Training Complete! Trained {total_count} samples for {len(counts)} student(s).", fg="#10b981"
            ))
            self.root.after(0, lambda: messagebox.showinfo("Result", final_msg, parent=self.root))
        else:
            self.root.after(0, lambda: self.lbl_status.config(text="● Training Failed.", fg="#ef4444"))
            self.root.after(0, lambda: messagebox.showerror("Error", msg, parent=self.root))

        self.root.after(0, lambda: self.btn_train.config(state=tk.NORMAL, text="⚡ START LBPH MODEL TRAINING ➔", bg="#8b5cf6"))


if __name__ == "__main__":
    root = tk.Tk()
    app = TrainDataWindow(root)
    root.mainloop()
