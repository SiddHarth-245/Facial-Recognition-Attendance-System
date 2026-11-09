# ðŸŒŸ Facial Recognition Attendance Management System (FaceAttend Ultra)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.x-brightgreen.svg)](https://opencv.org/)
[![GUI](https://img.shields.io/badge/GUI-Tkinter%20%2F%20TTK-darkblue.svg)](https://docs.python.org/3/library/tkinter.html)
[![Database](https://img.shields.io/badge/Database-SQLite3%20%2F%20WAL-orange.svg)](https://www.sqlite.org/)
[![Security](https://img.shields.io/badge/Security-PBKDF2--HMAC--SHA256-brightgreen.svg)](utils/security.py)
[![Test Suite](https://img.shields.io/badge/Tests-38%2F38%20Passed-success.svg)](utils/)

A modern, enterprise-grade desktop biometric attendance management system built with **Python**, **OpenCV (Haar Cascade & LBPH Face Recognizer)**, **Tkinter / TTK**, and **SQLite3 (WAL Mode)**. Designed with a high-contrast **FaceAttend Cyber-Blue Ultra Design System**, anti-flicker temporal face tracking, interactive randomized liveness verification, cryptographic authentication defense, transactional data integrity, and automated parent email alerts via the official Brevo REST API.

---

## âš¡ Key Highlights & Security Architecture

### 1. ðŸ” Cryptographic Authentication & Account Setup
- **PBKDF2-HMAC-SHA256 Hashing**: Passwords and security challenge answers are salted with 16 bytes of cryptographically secure random entropy (`secrets.token_bytes`) and hashed with **200,000 iterations** (`hashlib.pbkdf2_hmac`).
- **Constant-Time Verification**: Verification uses `secrets.compare_digest` to eliminate side-channel timing analysis attacks.
- **Safe First-Run Administrator Onboarding**: Hardcoded default administrator credentials have been completely removed. Upon initial setup on an empty database, FaceAttend automatically detects the first-run state and launches the Administrator Setup wizard.
- **Zero-Lockout Legacy Migration**: Existing accounts are upgraded in-place to PBKDF2 hashes upon initial database connection and authentication without requiring user intervention or causing account lockouts.
- **Session Privacy**: The "Remember Me" credential caching stores only the username identifier in `database/.user_session.json`â€”passwords are never saved in plaintext on the filesystem.

### 2. ðŸ‘ï¸ Interactive Anti-Spoofing & Liveness Challenge Engine
- **Randomized Multi-Action Challenge**: When a face is initially detected and recognized by LBPH, the system initiates a fresh, randomized sequence of distinct behavioral actions (e.g., *turn left, then blink*; *blink, then turn right*; *look up, then return to center*). A static photo or simple prerecorded replay clip is rejected because it cannot dynamically respond to randomized prompts.
- **Face Tracker Continuity**: Challenges are strictly bound to the spatial tracker ID (`SpatialFaceTracker`). If the face leaves the viewport, is occluded, or swaps identity during the challenge, the session immediately aborts.
- **Strict Fail-Closed Enforcement**: Attendance is recorded **only** after both the interactive liveness challenge and the LBPH identity match pass. If the challenge fails, times out, or detection becomes uncertain, attendance is **never** logged to SQLite or CSV.
- **Clear Diagnostic Feedback & Fallback**: Real-time HUD guidance displays interactive prompts, directional indicators, and countdown timers. If a challenge fails, a clear message is displayed, allowing an immediate retry or manual instructor review via the Attendance Records interface.
- **2D Sensor Limitations & Disclaimer**: While active challenges significantly reduce proxy attendance from photographs and basic video replays, standard 2D webcams lack physiological depth and infrared emissivity sensing. Software-only 2D checks may remain vulnerable to high-end video screen injection or real-time deepfake synthesis. Dedicated 3D depth/infrared hardware or instructor supervision is recommended for high-assurance security perimeters.

### 3. ðŸ›¡ï¸ Transactional Attendance & Notification Integrity
- **Single Source of Truth**: Relational SQLite (`database/attendance_system.db`) serves as the authoritative persistence engine across all sessions. Flat-file CSVs (`attendance_records/attendance.csv`) are synchronized as mirrors.
- **Strict Unique Constraints**: Enforces at most **one attendance record per student per date** via database unique index `idx_attendance_student_date`.
- **Atomic UPSERT Notification Tracking**: Enforces at most **one notification record per student, date, and status** via unique index `idx_email_notif_student_date_status_unique` using conflict-safe `ON CONFLICT` writes to preserve `ACCEPTED` delivery proofs.
- **Zero CSV Discrepancy**: CSV mirror rows are appended **only** after the SQLite database insert transaction succeeds. If the database rejects an insert (e.g., duplicate record or integrity violation), no CSV row is written.
- **Automated Safe Deduplication**: Redundant legacy duplicate records are safely cleaned during database initialization, preserving the latest confirmed records.

### 4. ðŸŽ¯ Recognition Safeguards & Multi-Pose Biometric Training
- **3-Phase Guided Multi-Pose Acquisition**: During student photo registration (`modules/student.py`), the system captures a balanced 100-sample multi-angle dataset across 3 guided phases:
  - **Phase 1 (Samples 1â€“35)**: Frontal / Center Pose (direct neutral perspective).
  - **Phase 2 (Samples 36â€“68)**: Left Profile Pose (guided head turn to the left).
  - **Phase 3 (Samples 69â€“100)**: Right Profile Pose (guided head turn to the right).
  This multi-pose dataset ensures the LBPH recognizer learns rich spatial texture representations across varying yaw angles, allowing fast and accurate identification even while the student executes left/right head movements during liveness checks.
- **Fast, Natural Liveness Challenge Calibration**: Action detection thresholds (`yaw_delta > 0.016`, natural blink dip `< 0.80`) are tuned for natural, ergonomic micro-movements, completing challenges in ~1.5â€“2.5s without requiring exaggerated neck rotation that could cause face loss.
- **Tolerant Spatial Tracking Continuity**: A multi-frame grace buffer (18 frames / ~0.6â€“0.8s) prevents transient motion blur or rapid pose changes from immediately dropping the session, eliminating frustrating repeated retry loops.
- **Enrolled-Student Training Safeguards**: The machine learning compilation pipeline (`modules/train.py`) cross-references the active database and **strictly trains only on face samples belonging to currently enrolled students**. Orphaned or deleted student images are excluded from models.
- **Biometric Sample Deletion Cascade**: Deleting a student profile immediately purges all associated photographic face crops (`data/user.<student_id>.*.jpg`) from disk and rebuilds the recognizer model.
- **Metric Accuracy**: Local Binary Patterns Histograms (LBPH) generate an uncalibrated chi-square distance between spatial texture histograms (lower = closer match). Displayed Match Scores (0â€“100) are relative proximity metrics and are explicitly documented as **non-calibrated probabilities**.
- **Manual Attendance Overrides**: Conservative distance thresholding rejects uncertain matches, and administrators retain complete manual attendance marking and status editing via the Attendance Records interface.

### 5. ðŸ“§ Automated Parent Notifications (Brevo REST API v3)
- **Direct HTTPS API**: Eliminates SMTP, Google 2-Step Verification, and Gmail App Password dependencies.
- **Asynchronous Live Dispatch**: Non-blocking worker threads prevent camera stuttering or dropped frames during biometric recognition.
- **Comprehensive Audit Log**: Every dispatch attempt is logged with sanitized timestamps and provider message IDs in `attendance_records/email_notifications.log`.

---

## ðŸ“Š System Architecture & Liveness Verification Flow

```
                                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                                  â”‚      main.py (Bootstrap)      â”‚
                                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                                 â”‚
                                                 â–¼
                                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                                  â”‚    login.py (Auth Gateway)    â”‚
                                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                                 â”‚
                                                 â–¼
                 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                 â”‚                    dashboard.py (Central Hub)                    â”‚
                 â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”˜
                        â”‚          â”‚          â”‚          â”‚          â”‚         â”‚
                        â–¼          â–¼          â–¼          â–¼          â–¼         â–¼
                  [ Student ]  [ FaceRec ]  [ Attend ]  [ Train ]  [ Dev ]  [ Help ]
```

### Biometric & Liveness Verification Pipeline:
```
  [ Live Webcam Frame ]
           â”‚
           â–¼
  [ Haar Cascade Detection ] â”€â”€(No Face)â”€â”€> [ Standby / Continue Stream ]
           â”‚
           â–¼
  [ Multi-Face Spatial Tracker ] â”€â”€(Face Swapped)â”€â”€> [ ABORT: Tracker Changed ]
           â”‚
           â–¼
  [ LBPH Feature Extraction ] â”€â”€(Distance > 78.0)â”€â”€> [ Unknown Face HUD (Red) ]
           â”‚
           â–¼ (Identity Verified)
  [ Check Daily Attendance ] â”€â”€(Already Marked)â”€â”€> [ HUD: "Already Marked Today" ]
           â”‚ (Unmarked)
           â–¼
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚         Interactive Randomized Liveness Challenge           â”‚
  â”‚   - Calibrate Baseline Face Position & Eye Openness         â”‚
  â”‚   - Present Step 1 (e.g. "Turn Head Left") [Timeout: 5.5s]  â”‚
  â”‚   - Present Step 2 (e.g. "Blink Both Eyes") [Timeout: 5.5s] â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                 â”‚
                 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                 â–¼                               â–¼
         [ Challenge Passed ]            [ Failed / Expired ]
                 â”‚                               â”‚
                 â–¼                               â–¼
       [ Atomic SQLite Insert ]          [ FAIL CLOSED ]
                 â”‚                    - No SQLite Record Written
                 â–¼                    - No CSV Row Appended
       [ Append CSV Mirror ]          - No Parent Email Dispatched
                 â”‚                    - Show Diagnostic Feedback
                 â–¼                    - Allow Retry / Manual Review
     [ Async Brevo Parent Email ]
```

---

## ðŸ› ï¸ Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core application runtime |
| **Cryptography** | PBKDF2-HMAC-SHA256 (`hashlib`, `secrets`) | NIST SP 800-132 password and recovery hashing |
| **Computer Vision** | OpenCV (`opencv-contrib-python`) | Haar Cascade face detection & LBPH recognition |
| **Liveness Engine** | Python / NumPy / OpenCV (`utils/liveness_detector.py`) | Spatial head-pose and eye-blink state machine |
| **GUI Framework** | Tkinter & TTK | Hardware-accelerated Cyber-Blue desktop interface |
| **Database** | SQLite3 (WAL Mode, 60s timeout) | ACID transactional relational storage (`attendance_system.db`) |
| **Transactional Email** | Brevo REST API v3 (`requests`) | Automated parent attendance notifications |
| **Testing** | Python `unittest` | Comprehensive 38-test verification harness |

---

## ðŸš€ Installation & First-Run Setup

### 1. Prerequisites
- Python 3.10 or higher installed.
- Integrated or external USB Webcam.

### 2. Setup Virtual Environment
```powershell
# Navigate to project directory
cd "d:\Facial Recognition Attendance Management System"

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

### 3. Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Parent Email Notifications (Optional)
Copy `.env.example` to `.env` and configure your verified Brevo credentials:
```ini
BREVO_API_KEY=your_brevo_v3_api_key_here
BREVO_SENDER_EMAIL=your_verified_sender@institution.edu
BREVO_SENDER_NAME=FaceAttend Biometrics
```

### 5. Launch Application & First-Run Administrator Setup
```powershell
python main.py
```
*On first launch with an uninitialized database, FaceAttend displays a First-Run setup notification and prompts you to register the primary administrator credentials. No hardcoded credentials exist.*

---

## ðŸ—„ï¸ Database & Artifact Management

- **Primary Database**: `database/attendance_system.db` (Concurrency-tuned Write-Ahead Logging mode).
- **Audit Logs**: `attendance_records/email_notifications.log`
- **CSV Mirror**: `attendance_records/attendance.csv`
- **Biometric Face Samples**: `data/user.<student_id>.<sample_index>.jpg`
- **Trained Model**: `classifier/classifier.xml` and `classifier/id_map.json`
- **Legacy Inactive Artifact**: `attendance.db` (0-byte file located at root) is an unused legacy placeholder. The active database is `database/attendance_system.db`. Root `attendance.db` is retained and not deleted without explicit administrator approval.

---

## ðŸ§ª Automated Testing & Verification Suite

The repository includes a comprehensive 38-test automated test harness covering liveness verification, authentication security, database constraints, email automation, and core computer vision pipelines:

```powershell
# 1. Interactive Liveness & Anti-Spoofing Verification (9 tests)
.\.venv\Scripts\python.exe utils/test_liveness_detection.py

# 2. Security, PBKDF2 hashing, and integrity safeguards (8 tests)
.\.venv\Scripts\python.exe utils/test_security_and_integrity.py

# 3. Core system CRUD, authentication, and classifier tests (6 tests)
.\.venv\Scripts\python.exe utils/test_system.py

# 4. Brevo REST API transactional email & duplicate prevention (11 tests)
.\.venv\Scripts\python.exe utils/test_brevo_notifications.py

# 5. Parent email automation & GUI hooks (4 tests)
.\.venv\Scripts\python.exe utils/test_parent_email_automation.py
```

### Summary of Verified Coverage:
- âœ… **Randomized Liveness Challenges**: Generates diverse multi-action challenges rejecting static photo presentations.
- âœ… **Face Tracker Continuity**: Detects tracker ID shifts and aborts challenge sessions immediately.
- âœ… **Strict Fail-Closed Enforcement**: Ensures failed, expired, or aborted challenges never write to SQLite or CSV.
- âœ… **Zero CSV Discrepancy**: Validates that CSV rows are only appended when SQLite transactions succeed.
- âœ… **PBKDF2 Hashing**: 200,000 rounds, unique random salt generation, constant-time validation.
- âœ… **Zero-Lockout Upgrade**: In-place transparent migration from legacy plaintext to PBKDF2 salted hashes.
- âœ… **Single Attendance per Date**: `idx_attendance_student_date` constraint enforcement.
- âœ… **Single Notification per Date/Status**: `idx_email_notif_student_date_status_unique` UPSERT enforcement.
- âœ… **Enrolled-Student Safeguard**: Ignores orphaned face samples during model training.
- âœ… **Biometric Cascade Deletion**: Purges facial samples from disk upon student profile removal.

---

## ðŸ“œ Academic Mentorship & Authors

Developed at the **School of Computer Engineering, KIIT Deemed to be University**, under the mentorship of **Project Mentor**.

