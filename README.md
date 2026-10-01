# 🌟 Facial Recognition Attendance Management System (FaceAttend Ultra)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-brightgreen.svg)](https://opencv.org/)
[![Tkinter](https://img.shields.io/badge/GUI-Tkinter%20%2F%20TTK-darkblue.svg)](https://docs.python.org/3/library/tkinter.html)
[![Database](https://img.shields.io/badge/Database-SQLite3%20%2F%20WAL-orange.svg)](https://www.sqlite.org/)
[![Test Suite](https://img.shields.io/badge/Tests-6%2F6%20Passed-success.svg)](file:///d:/Facial%20Recognition%20Attendance%20Management%20System/test_system.py)

A modern, biometric desktop attendance management application built with **Python**, **OpenCV (Haar Cascade & LBPH Face Recognizer)**, **Tkinter & TTK**, and **SQLite3 / MySQL**. Designed with an enterprise **Cyber-Blue Ultra Design System**, anti-flicker temporal tracking, zero-watermark 2K code-generated assets, and strict registered-users-only access control.

---

## ⚡ Key Highlights & Recent Innovations

### 1. 🎯 Anti-Flicker Temporal Face Tracking (`TemporalFaceTracker`)
- **Multi-Frame Consensus**: Implements a **7-frame rolling majority voting buffer** to eliminate single-frame sensor noise, camera jitter, and instantaneous identity flipping.
- **Confirmation Hold Window**: Employs a **0.8s lock-in period** to keep recognized student metadata smooth and stable on screen.
- **Zero-Padding Synchronization**: Exact mathematical crop alignment ($0\%$ boundary padding, normalized $200 \times 200$ grayscale with histogram equalization) perfectly matching training sample geometry with LBPH $8 \times 8$ grid sub-regions.
- **Strict Distance Thresholds**: Calibrated distance threshold ($\le 72.0$) with dynamic match confidence percentage ($0\text{--}100\%$) and unknown face rejection.

### 2. 🔐 Registered Users Only Authentication
- **Strict Role-Based Access**: Verifies account existence in SQLite/MySQL before authenticating credentials; unregistered users receive an interactive prompt to create an account.
- **Security Features**: Interactive Show/Hide Password eye toggle, security question self-recovery, and session management.

### 3. 🎨 FaceAttend Cyber-Blue Ultra UI System
- **100% Zero-Watermark 2K Graphics**: Clean, high-DPI procedural backgrounds and banners (`#030b18` deep cyber background, `#071a35` glassmorphic cards, `#38bdf8` cyan accents, `#0084ff` primary buttons).
- **Anti-Aliased Vector Tiles**: 8 ultra-high-definition ($256 \times 256$) biometric module icons with smooth hover states.
- **Real-Time Biometric HUD**: Live camera viewport overlay paired with a dynamic telemetry side card displaying Roll No, Name, Department, Match %, and auto-attendance timestamps.

### 4. 🗄️ Resilient Dual-Persistence Data Layer
- **SQLite WAL Mode**: Write-Ahead Logging for high concurrency, zero locks, and corruption prevention.
- **Dual-Persistence Attendance**: Real-time logging to both transactional relational databases and exportable CSV spreadsheets (`attendance_records/`).
- **Hardware Agnostic Camera Fallback**: Multi-backend camera loader supporting `CAP_DSHOW` and `CAP_MSMF` across camera indices ($0, 1, 2$) with interactive error diagnostic dialogs.

---

## 📊 Core Modules Overview

```
                                  ┌───────────────────────────────┐
                                  │      main.py (Launcher)       │
                                  └──────────────┬────────────────┘
                                                 │
                                                 ▼
                                  ┌───────────────────────────────┐
                                  │    login.py (Auth Gateway)    │
                                  └──────────────┬────────────────┘
                                                 │
                                                 ▼
                ┌──────────────────────────────────────────────────────────────────┐
                │                    dashboard.py (Central Hub)                    │
                └──────┬──────────┬──────────┬──────────┬──────────┬─────────┬─────┘
                       │          │          │          │          │         │
                       ▼          ▼          ▼          ▼          ▼         ▼
                 [ Student ]  [ FaceRec ]  [ Attend ]  [ Train ]  [ Dev ]  [ Help ]
```

1. **Student Management (`student.py`)**: Full student CRUD interface with automated 100-sample high-speed facial dataset capture.
2. **Face Recognition Studio (`face_recognition.py`)**: Real-time multi-threaded video stream with live face detection, HUD bounding boxes, and instant attendance logging.
3. **Attendance Records (`attendance.py`)**: Interactive table viewer, date/student filters, manual status overrides, and instant CSV Import/Export.
4. **Model Training (`train.py`)**: Multi-threaded dataset scanner and LBPH Face Recognizer model compiler (`classifier/classifier.xml`).
5. **Photo Sample Explorer**: One-click direct explorer access to captured biometric samples in `data/`.
6. **Developer Profile (`developer.py`)**: Architecture overview, technology stack, and engineering team credits.
7. **Help Desk (`help_desk.py`)**: Interactive troubleshooting guide, lighting/camera calibration tips, and system documentation.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core Application Runtime |
| **Computer Vision** | OpenCV (`opencv-contrib-python`) | Haar Cascade Face Detection & LBPH Classification |
| **GUI Framework** | Tkinter & TTK | Native, High-Performance Desktop Interface |
| **Graphics & Imaging**| Pillow (`PIL`), NumPy | Asset Generation, Color Normalization, Array Slicing |
| **Database** | SQLite3 (WAL Mode) & MySQL | Relational User & Student Records Storage |
| **Data Analytics** | Pandas | CSV Attendance Export, Reporting, & Import Engine |
| **Testing** | `unittest` | Automated 6-Suite Regression Test Pipeline |

---

## 🚀 Installation & Setup Guide

### 1. Prerequisites
- Python 3.10 or higher installed.
- Integrated or USB Webcam.

### 2. Clone & Setup Virtual Environment
```powershell
# Navigate to the project root
cd "d:\Facial Recognition Attendance Management System"

# Create virtual environment
python -m venv .venv

# Activate virtual environment (PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate virtual environment (CMD)
.\.venv\Scripts\activate.bat
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Generate HD UI Assets (Optional / Automatic)
```powershell
python generate_cyber_2k_assets.py
python generate_icons.py
```

### 5. Launch the Application
```powershell
python main.py
# Or directly to login:
python login.py
```

---

## 🔑 Default Administrator Credentials

| Field | Default Value |
| :--- | :--- |
| **Email / Username** | `pandeyvedprakash499@gmail.com` (or `Vedprakash`) |
| **Password** | `admin123` |
| **Security Question** | `Your Birth Place` |
| **Security Answer** | `City` |

*(You can also click **New User Register** on the login screen to register your own credentials)*

---

## 📋 Step-by-Step User Workflow

### Step 1: Student Enrollment & Photo Capture
1. Log in and click **Student Details**.
2. Fill in the student information (*Student ID, Name, Roll No, Department, Course, Year, Semester, Gender, Contact, Email*).
3. Click **Save** to persist the record to the database.
4. Click **📷 Take Photo Sample**. The camera will automatically capture 100 face crops into `data/user.<student_id>.<sample_index>.jpg`.

### Step 2: Train Classifier Model
1. Return to the dashboard and open **Train Data**.
2. Click **🚀 Train Data**.
3. The LBPH machine learning model will parse all images in `data/` and compile `classifier/classifier.xml` and `classifier/id_map.json`.

### Step 3: Run Live Face Recognition Attendance
1. Click **Face Recognition** on the dashboard.
2. Click **📷 Open Face Detector**.
3. Look into the camera. The **Temporal Face Tracker** will verify identity across frames, display your profile on the HUD card, and record your attendance automatically.
4. Press **`q`** or **`ESC`** (or close the window) to stop the camera.

### Step 4: Manage & Export Attendance
1. Click **Attendance** on the dashboard.
2. View real-time logs, filter by student or date, or modify attendance status.
3. Click **📥 Export CSV** to export an Excel-ready attendance report.

---

## 📁 Directory Structure

```
d:/Facial Recognition Attendance Management System/
│
├── main.py                             # Master Application Entry Point
├── login.py                            # Registered-Users-Only Auth Portal
├── register.py                         # User Account Registration Window
├── forget_password.py                  # Self-Service Credential Recovery
├── dashboard.py                        # Central Hub with 8 Biometric Modules
├── student.py                          # Student Details Management & Dataset Capture
├── train.py                            # LBPH Face Classifier Training Pipeline
├── face_recognition.py                 # Live Face Recognition & Temporal HUD
├── attendance.py                       # Interactive Attendance Log & CSV Manager
├── developer.py                        # System Specs & Developer Info
├── help_desk.py                        # Help Desk, Calibration & FAQ Guide
├── test_system.py                      # Automated 6-Suite Regression Test Runner
├── generate_cyber_2k_assets.py         # 2K UI Wallpaper & Banner Generator
├── generate_icons.py                   # 256x256 Anti-Aliased Vector Icon Generator
├── haarcascade_frontalface_default.xml # OpenCV Frontal Face Detection Model
├── requirements.txt                    # Project Dependencies
├── README.md                           # Documentation & Architecture Guide
│
├── database/                           # Relational Database Storage Layer
│   ├── __init__.py
│   ├── db_manager.py                   # Dual SQLite/MySQL Storage Manager
│   └── attendance_system.db            # SQLite Database File (WAL Mode)
│
├── assets/                             # Procedurally Generated UI Graphics
│   ├── bg_login.png
│   ├── login_bg_cyber.png
│   ├── dashboard_bg_cyber.png
│   ├── face_recog_bg_cyber.png
│   ├── student_header.png
│   ├── attendance_header.png
│   ├── train_top_banner.png
│   ├── register_banner.png
│   └── icons/                          # 8 HD Tile Icons (256x256)
│       ├── tile_student.png
│       ├── tile_face.png
│       ├── tile_attendance.png
│       ├── tile_train.png
│       ├── tile_photos.png
│       ├── tile_developer.png
│       ├── tile_help.png
│       └── tile_exit.png
│
├── data/                               # Captured Face Samples (user.<id>.<count>.jpg)
├── classifier/                         # Compiled LBPH Classifier & ID Mapping
│   ├── classifier.xml
│   └── id_map.json
└── attendance_records/                 # CSV Attendance Records & Exported Reports
```

---

## 🧪 Testing & Verification

The project includes an automated regression test suite testing all subsystems:

```powershell
python test_system.py
```

### Test Coverage:
1. `test_01_user_auth_and_recovery`: Validates registration, registered-users-only enforcement, correct password authentication, and security question recovery.
2. `test_02_student_crud`: Validates Create, Read, Update, Delete operations in the database.
3. `test_03_training_and_lbph_classifier`: Validates sample scanning, NumPy serialization, and `classifier.xml` generation.
4. `test_04_attendance_logging`: Validates atomic attendance recording, deduplication on same-day mark, and CSV export integrity.
5. `test_05_gui_module_imports`: Validates clean importability of all 10 GUI modules without circular dependency issues.
6. `test_06_face_recognition_pipeline`: Validates face crop equalization, `TemporalFaceTracker` multi-frame voting consensus, and confidence metrics.

---

## 📜 License & Acknowledgements

Developed for academic and enterprise attendance automation. Built with standard open-source Python computer vision libraries.
