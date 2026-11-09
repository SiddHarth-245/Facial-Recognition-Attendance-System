"""
========================================================================================
FaceAttend Automated Parent Email Notification Engine (Brevo Transactional API)
========================================================================================
Module: utils/email_notifier.py
Role:
    Handles automated, transactional email notifications sent to parents when a
    student's attendance is recorded or updated (marked Present or Absent) via live
    facial recognition or manual administrative action.

Backend Provider:
    Official Brevo (formerly Sendinblue) Transactional Email REST API v3:
    Endpoint: https://api.brevo.com/v3/smtp/email

Security & Reliability Standards:
    1. Zero SMTP / Zero Passwords:
       Uses HTTPS REST calls via Python 'requests' library. No smtplib, no Gmail App
       Passwords, no Google 2-Step Verification, and no browser popup windows.
    2. Secure Credential Management:
       Reads API keys from environment variables (BREVO_API_KEY, BREVO_SENDER_EMAIL,
       BREVO_SENDER_NAME) or local '.env' file. Never hardcodes or logs secrets.
    3. Persistent Duplicate Prevention:
       Integrates with SQLite 'email_notifications' table to enforce at most one
       PRESENT and one ABSENT notification per student per attendance date/session.
       Preserves full immutable audit trail upon status corrections.
    4. Non-Blocking Asynchronous Queue:
       All network transmissions run in background daemon threads so live camera feeds
       (60+ FPS) and Tkinter GUI event loops never freeze or stutter.
========================================================================================
"""

import os
import re
import json
import logging
import threading
import webbrowser
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "email_config.json")
ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance_records")
LOG_FILE = os.path.join(ATTENDANCE_DIR, "email_notifications.log")
PREVIEW_FILE = os.path.join(ATTENDANCE_DIR, "email_preview.html")

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(ATTENDANCE_DIR, exist_ok=True)

# Brevo v3 Transactional Email REST Endpoint
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

# Email format validation regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


# ========================================================================================
# 1. Environment & Configuration Loader
# ========================================================================================

def load_dotenv_file(filepath: str = ENV_FILE) -> Dict[str, str]:
    """
    Parses a local .env file and sets values into os.environ if not already defined.
    Does not depend on external packages, ensuring 100% portable execution.
    """
    loaded: Dict[str, str] = {}
    if not os.path.exists(filepath):
        return loaded

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                key = k.strip()
                val = v.strip().strip("'\"")
                loaded[key] = val
                if key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        _append_to_audit_log(
            "SYS_WARN", student_id="-", roll="-", student_name="System",
            attendance_date="-", status="-", to_email="-", outcome="CONFIG_WARN",
            details=f"Failed to read .env file: {type(e).__name__}"
        )
    return loaded


# Automatically load .env upon module import
load_dotenv_file()


def get_brevo_config() -> Dict[str, Any]:
    """
    Retrieves Brevo API configuration from environment variables with fallback to config.json.
    Ensures credentials are never printed or returned in plain text logs.
    """
    # Reload .env in case it was updated during the application session
    load_dotenv_file()

    api_key = os.environ.get("BREVO_API_KEY", "").strip()
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "").strip()
    sender_name = os.environ.get("BREVO_SENDER_NAME", "").strip()
    institution = os.environ.get("BREVO_INSTITUTION_NAME", "").strip()
    mentor = os.environ.get("BREVO_MENTOR_NAME", "").strip()

    # Secondary fallback to email_config.json if environment variable not set
    if (not api_key or not sender_email) and os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
                if not api_key:
                    api_key = cfg_data.get("brevo_api_key", "").strip()
                if not sender_email:
                    sender_email = cfg_data.get("brevo_sender_email", "").strip()
                if not sender_name:
                    sender_name = cfg_data.get("brevo_sender_name", "").strip()
                if not institution:
                    institution = cfg_data.get("school_name", "").strip()
                if not mentor:
                    mentor = cfg_data.get("mentor_name", "").strip()
        except Exception:
            pass

    # Default fallback values for presentation
    if not sender_name:
        sender_name = "FaceAttend Biometrics - KIIT University"
    if not institution:
        institution = "School of Computer Engineering, KIIT University"
    if not mentor:
        mentor = "Mr. Rakesh Kumar Rai"

    is_configured = bool(api_key and sender_email and is_valid_email(sender_email))

    return {
        "api_key": api_key,
        "sender_email": sender_email,
        "sender_name": sender_name,
        "institution_name": institution,
        "mentor_name": mentor,
        "is_configured": is_configured
    }


def mask_secret(secret: str, prefix_len: int = 8, suffix_len: int = 4) -> str:
    """Masks sensitive API keys for safe display in UI and audit logs."""
    if not secret:
        return "[NOT SET]"
    if len(secret) <= prefix_len + suffix_len:
        return "•" * len(secret)
    return f"{secret[:prefix_len]}{'•' * (len(secret) - prefix_len - suffix_len)}{secret[-suffix_len:]}"


def is_valid_email(email_str: str) -> bool:
    """Validates email format using standard regular expressions."""
    if not email_str or not isinstance(email_str, str):
        return False
    clean = email_str.strip()
    return bool(EMAIL_REGEX.match(clean))


# ========================================================================================
# 2. Audit Logging
# ========================================================================================

def _append_to_audit_log(entry_type: str, student_id: str, roll: str, student_name: str,
                         attendance_date: str, status: str, to_email: str, outcome: str,
                         details: str, provider_message_id: str = ""):
    """
    Appends a standardized notification entry to attendance_records/email_notifications.log.
    Never logs API keys, auth headers, or raw email contents.
    """
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg_id_part = f" | MessageID: {provider_message_id}" if provider_message_id else ""
        log_line = (
            f"[{now_str}] [{entry_type}] Outcome: {outcome} | Student: {student_name} "
            f"(ID: {student_id}, Roll: {roll}) | Date: {attendance_date} | Status: {status.upper()} | "
            f"To: {to_email}{msg_id_part} | Details: {details}\n"
        )
        os.makedirs(os.path.dirname(os.path.abspath(LOG_FILE)), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
    except Exception:
        pass


# ========================================================================================
# 3. Email Content & HTML Template Generation
# ========================================================================================

def build_email_content(student_name: str, roll: str, dep: str = "",
                        date_str: str = "", time_str: str = "", status: str = "PRESENT",
                        mentor_name: str = "Mr. Rakesh Kumar Rai",
                        institution_name: str = "School of Computer Engineering, KIIT University") -> Tuple[str, str, str]:
    """
    Constructs standardized Subject, Plain-Text Body, and Rich HTML Body.

    Requirements Adherence:
    - Present Subject: FaceAttend: Attendance Confirmation - [Student Name] (PRESENT)
    - Absent Subject:  FaceAttend: Absence Notification - [Student Name] (ABSENT)
    """
    status_clean = (status or "PRESENT").strip().upper()
    is_present = (status_clean == "PRESENT")
    
    student_display = student_name.strip() or "Student"
    roll_display = roll.strip() or "N/A"
    dep_display = dep.strip() or "Computer Science and Engineering"
    now = datetime.now()
    date_display = date_str.strip() or now.strftime("%d/%m/%Y")
    time_display = time_str.strip() or now.strftime("%I:%M:%S %p")

    # Standardized subjects
    if is_present:
        subject = f"FaceAttend: Attendance Confirmation - {student_display} (PRESENT)"
        headline = "Attendance Confirmation Notice"
        status_badge_color = "#10b981"
        status_badge_bg = "#ecfdf5"
        status_icon = "✓"
        note = (
            f"This is an automated biometric confirmation from the FaceAttend System. "
            f"Your ward, <strong>{student_display}</strong>, has successfully checked into their academic session "
            f"and has been verified as <strong>PRESENT</strong>."
        )
        plain_note = (
            f"This is an automated biometric confirmation from the FaceAttend System. "
            f"Your ward, {student_display}, has successfully checked into their academic session "
            f"and has been verified as PRESENT."
        )
    else:
        subject = f"FaceAttend: Absence Notification - {student_display} (ABSENT)"
        headline = "Absence Notification Alert"
        status_badge_color = "#ef4444"
        status_badge_bg = "#fef2f2"
        status_icon = "✗"
        note = (
            f"This is an important academic notification from the FaceAttend System. "
            f"Your ward, <strong>{student_display}</strong>, has been recorded as <strong>ABSENT</strong> "
            f"for their scheduled academic session today ({date_display}). If this absence was unexpected, "
            f"please contact the department mentor promptly."
        )
        plain_note = (
            f"This is an important academic notification from the FaceAttend System. "
            f"Your ward, {student_display}, has been recorded as ABSENT "
            f"for their scheduled academic session today ({date_display}). If this absence was unexpected, "
            f"please contact the department mentor promptly."
        )

    # Plain text fallback
    plain_text = f"""============================================================
FACEATTEND BIOMETRIC ATTENDANCE NOTIFICATION
{institution_name}
============================================================

Dear Parent / Guardian,

{headline}:
------------------------------------------------------------
• Student Name:     {student_display}
• Roll Number:      {roll_display}
• Department/Course:{dep_display}
• Attendance Date:  {date_display}
• Logged Time:      {time_display}
• Attendance Status:{status_clean}
• Faculty Mentor:   {mentor_name}
• Institution:      {institution_name}
------------------------------------------------------------

{plain_note}

Automated Dispatch by FaceAttend Biometric Attendance System.
Please do not reply directly to this automated email.
============================================================
"""

    # Modern, responsive HTML email template
    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b1329; margin: 0; padding: 20px; }}
  .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.3); border: 1px solid #1e293b; }}
  .header {{ background: linear-gradient(135deg, #071a35 0%, #030b18 100%); padding: 26px 22px; text-align: center; color: #ffffff; border-bottom: 2px solid #0284c7; }}
  .header h1 {{ margin: 0; font-size: 19px; font-weight: 700; color: #38bdf8; letter-spacing: 0.5px; }}
  .header p {{ margin: 5px 0 0 0; font-size: 12px; color: #94a3b8; }}
  .content {{ padding: 26px 24px; color: #0f172a; }}
  .badge-container {{ text-align: center; margin: 18px 0; }}
  .badge {{ display: inline-block; padding: 8px 22px; border-radius: 9999px; font-size: 15px; font-weight: 700; color: {status_badge_color}; background-color: {status_badge_bg}; border: 1.5px solid {status_badge_color}; }}
  .details-box {{ background: #f8fafc; border-radius: 8px; padding: 16px 18px; margin: 18px 0; border-left: 4px solid {status_badge_color}; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; }}
  .row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #e2e8f0; font-size: 13px; }}
  .row:last-child {{ border-bottom: none; }}
  .label {{ color: #64748b; font-weight: 600; }}
  .value {{ color: #0f172a; font-weight: 700; text-align: right; }}
  .note {{ font-size: 13px; color: #475569; line-height: 1.5; margin: 14px 0; }}
  .footer {{ background: #f8fafc; padding: 16px 20px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>FACEATTEND BIOMETRIC SYSTEM</h1>
    <p>{institution_name}</p>
  </div>
  <div class="content">
    <p style="font-size: 14px; color: #1e293b; margin-top: 0;">Dear Parent / Guardian,</p>
    <div class="badge-container">
      <div class="badge">{status_icon} &nbsp; {status_clean}</div>
    </div>
    <p class="note">{note}</p>
    <div class="details-box">
      <div class="row"><span class="label">Student Name:</span><span class="value">{student_display}</span></div>
      <div class="row"><span class="label">Roll Number:</span><span class="value">{roll_display}</span></div>
      <div class="row"><span class="label">Department:</span><span class="value">{dep_display}</span></div>
      <div class="row"><span class="label">Attendance Date:</span><span class="value">{date_display}</span></div>
      <div class="row"><span class="label">Verification Time:</span><span class="value">{time_display}</span></div>
      <div class="row"><span class="label">Faculty Mentor:</span><span class="value">{mentor_name}</span></div>
      <div class="row"><span class="label">Institution:</span><span class="value">{institution_name}</span></div>
    </div>
  </div>
  <div class="footer">
    <p style="margin: 0 0 3px 0;">Automated Notification by FaceAttend Ultra Attendance System</p>
    <p style="margin: 0;">Kalinga Institute of Industrial Technology, Bhubaneswar, Odisha – 751024</p>
  </div>
</div>
</body>
</html>
"""
    return subject, plain_text, html_body


# ========================================================================================
# 4. Brevo API Client (HTTPS POST)
# ========================================================================================

def send_brevo_email(to_email: str, to_name: str, subject: str,
                     html_content: str, text_content: str,
                     config: Optional[Dict[str, Any]] = None,
                     timeout: int = 12) -> Tuple[bool, str, Optional[str]]:
    """
    Transmits a transactional email via the official Brevo REST API v3.
    
    Parameters:
    -----------
    to_email, to_name : str
        Recipient details.
    subject, html_content, text_content : str
        Email content payload.
    config : Optional[Dict[str, Any]]
        Optional config override (used for testing and credential dependency injection).
    timeout : int
        HTTP socket timeout in seconds.

    Returns:
    --------
    Tuple[bool, str, Optional[str]]
        (success, message, provider_message_id)
    """
    cfg = config or get_brevo_config()
    api_key = cfg.get("api_key", "").strip()
    sender_email = cfg.get("sender_email", "").strip()
    sender_name = cfg.get("sender_name", "FaceAttend Biometrics").strip()

    if not api_key:
        return False, "Brevo API Key is missing. Please set BREVO_API_KEY in .env.", None
    if not sender_email or not is_valid_email(sender_email):
        return False, "Brevo Sender Email is missing or invalid. Please set BREVO_SENDER_EMAIL in .env.", None
    if not to_email or not is_valid_email(to_email):
        return False, f"Recipient email address '{to_email}' is invalid.", None

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key
    }

    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email
        },
        "to": [
            {
                "email": to_email.strip(),
                "name": to_name.strip() or "Parent / Guardian"
            }
        ],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": text_content
    }

    try:
        response = requests.post(
            BREVO_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )

        status_code = response.status_code
        # Successful Brevo API response: HTTP 201 Created (or 200/202)
        if status_code in (200, 201, 202):
            try:
                res_data = response.json()
                msg_id = res_data.get("messageId", "")
            except Exception:
                msg_id = "accepted_no_id"

            return True, f"Email accepted by Brevo API (Message ID: {msg_id})", msg_id

        # Handle specific Brevo HTTP error responses with sanitized descriptions
        err_detail = ""
        try:
            err_json = response.json()
            err_detail = err_json.get("message") or err_json.get("code") or ""
        except Exception:
            err_detail = response.text[:200]

        if status_code == 401:
            err_msg = "Brevo Authentication Failed (HTTP 401): Invalid API Key. Please verify BREVO_API_KEY."
        elif status_code == 403:
            err_msg = (
                f"Brevo Sender Forbidden (HTTP 403): Sender '{sender_email}' is unverified in your Brevo account. "
                f"Please verify it under Senders & IP (https://app.brevo.com/senders)."
            )
        elif status_code == 400:
            err_msg = f"Brevo Bad Request (HTTP 400): {err_detail or 'Invalid email parameters'}"
        elif status_code == 402:
            err_msg = f"Brevo Sending Limit / Credits Exceeded (HTTP 402): {err_detail or 'Account limit reached'}"
        elif status_code == 429:
            err_msg = "Brevo Rate Limit Exceeded (HTTP 429): Please wait before sending further notifications."
        else:
            err_msg = f"Brevo API Error (HTTP {status_code}): {err_detail or 'Service error'}"

        return False, err_msg, None

    except requests.exceptions.Timeout:
        return False, "Brevo API connection timed out (12s). Check your internet connection.", None
    except requests.exceptions.ConnectionError:
        return False, "Could not connect to Brevo API (DNS/Network Error). Check network connectivity.", None
    except Exception as ex:
        return False, f"Unexpected transmission error: {type(ex).__name__}", None


# ========================================================================================
# 5. Core Notification Dispatcher (Duplicate Prevention & Database Sync)
# ========================================================================================

def send_parent_attendance_notification(student_id: str, roll: str, student_name: str,
                                        dep: str = "", date_str: str = "", time_str: str = "",
                                        status: str = "PRESENT", parent_email: str = "",
                                        force: bool = False,
                                        config: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, str]:
    """
    Main notification dispatcher with duplicate prevention, database tracking, and audit logging.

    Parameters:
    -----------
    student_id : str
        Student ID (e.g. '1' or '23053645').
    roll, student_name, dep : str
        Student identity fields.
    date_str, time_str : str
        Session timestamp strings.
    status : str
        'PRESENT' or 'ABSENT'.
    parent_email : str
        Registered parent email address.
    force : bool
        If True, bypasses daily duplicate check (used for explicit manual user resends).

    Returns:
    --------
    Tuple[bool, str, str]
        (success_flag, user_message, outcome_code)
        Outcome codes: 'ACCEPTED', 'FAILED', 'SKIPPED_DUPLICATE', 'INVALID_RECIPIENT', 'CONFIG_ERROR'
    """
    try:
        from database.db_manager import (
            has_notification_been_sent,
            record_notification_attempt,
            get_student_by_id,
            get_student_by_roll
        )

        clean_sid = str(student_id).strip()
        clean_roll = str(roll).strip()
        clean_name = str(student_name).strip()
        clean_status = (status or "PRESENT").strip().upper()
        now = datetime.now()
        clean_date = (date_str or now.strftime("%d/%m/%Y")).strip()
        clean_time = (time_str or now.strftime("%I:%M:%S %p")).strip()

        # If missing student fields, attempt database lookup
        if not clean_sid or not clean_roll or not clean_name or not parent_email:
            s_profile = None
            if clean_sid:
                s_profile = get_student_by_id(clean_sid)
            if not s_profile and clean_roll:
                s_profile = get_student_by_roll(clean_roll)
            if s_profile:
                clean_sid = clean_sid or str(s_profile.get("student_id", ""))
                clean_roll = clean_roll or str(s_profile.get("roll", ""))
                clean_name = clean_name or str(s_profile.get("name", ""))
                dep = dep or str(s_profile.get("dep", ""))
                if not parent_email:
                    parent_email = str(s_profile.get("parent_email", "")).strip()

        clean_email = (parent_email or "").strip()

        # 1. Parent Email Address Validation
        if not clean_email or not is_valid_email(clean_email):
            err_msg = (
                f"Cannot send notification: Student '{clean_name}' (Roll: {clean_roll}) "
                f"has no valid parent email registered in the database."
            )
            record_notification_attempt(
                student_id=clean_sid,
                roll=clean_roll,
                attendance_date=clean_date,
                status=clean_status,
                recipient_email=clean_email,
                delivery_result="INVALID_RECIPIENT",
                error_details="Parent email address is missing or invalid"
            )
            _append_to_audit_log(
                "INVALID_EMAIL", clean_sid, clean_roll, clean_name, clean_date, clean_status,
                clean_email or "[BLANK]", "INVALID_RECIPIENT", "Missing or invalid parent email"
            )
            return False, err_msg, "INVALID_RECIPIENT"

        # 2. Duplicate Prevention Check
        if not force:
            already_accepted = has_notification_been_sent(clean_sid, clean_date, clean_status)
            if already_accepted:
                skip_msg = (
                    f"Duplicate Notification Skipped: A '{clean_status}' notification was already "
                    f"delivered to parent ({clean_email}) for student {clean_name} today ({clean_date})."
                )
                record_notification_attempt(
                    student_id=clean_sid,
                    roll=clean_roll,
                    attendance_date=clean_date,
                    status=clean_status,
                    recipient_email=clean_email,
                    delivery_result="SKIPPED_DUPLICATE",
                    error_details="Duplicate notification prevented (already delivered today)"
                )
                _append_to_audit_log(
                    "DUPLICATE_SKIP", clean_sid, clean_roll, clean_name, clean_date, clean_status,
                    clean_email, "SKIPPED_DUPLICATE", "Already sent and accepted today"
                )
                return False, skip_msg, "SKIPPED_DUPLICATE"

        # 3. Brevo Configuration Check
        cfg = config or get_brevo_config()
        if not cfg.get("is_configured", False):
            cfg_err = (
                "Brevo Transactional Email API is not configured. Please set BREVO_API_KEY and "
                "BREVO_SENDER_EMAIL in your '.env' file or via Attendance > Email Settings."
            )
            record_notification_attempt(
                student_id=clean_sid,
                roll=clean_roll,
                attendance_date=clean_date,
                status=clean_status,
                recipient_email=clean_email,
                delivery_result="CONFIG_ERROR",
                error_details="BREVO_API_KEY or BREVO_SENDER_EMAIL missing"
            )
            _append_to_audit_log(
                "CONFIG_ERROR", clean_sid, clean_roll, clean_name, clean_date, clean_status,
                clean_email, "CONFIG_ERROR", "Missing API key or Sender Email in .env"
            )
            return False, cfg_err, "CONFIG_ERROR"

        # 4. Generate Professional Content
        subject, plain_text, html_body = build_email_content(
            student_name=clean_name,
            roll=clean_roll,
            dep=dep,
            date_str=clean_date,
            time_str=clean_time,
            status=clean_status,
            mentor_name=cfg.get("mentor_name", "Mr. Rakesh Kumar Rai"),
            institution_name=cfg.get("institution_name", "School of Computer Engineering, KIIT University")
        )

        # 5. Dispatch via Brevo REST API
        ok, provider_msg, provider_msg_id = send_brevo_email(
            to_email=clean_email,
            to_name=f"{clean_name} Parent/Guardian",
            subject=subject,
            html_content=html_body,
            text_content=plain_text,
            config=cfg
        )

        # 6. Record Outcome and Audit
        if ok and provider_msg_id:
            record_notification_attempt(
                student_id=clean_sid,
                roll=clean_roll,
                attendance_date=clean_date,
                status=clean_status,
                recipient_email=clean_email,
                delivery_result="ACCEPTED",
                provider_message_id=provider_msg_id,
                error_details=""
            )
            _append_to_audit_log(
                "ACCEPTED", clean_sid, clean_roll, clean_name, clean_date, clean_status,
                clean_email, "ACCEPTED", "Accepted by Brevo API", provider_message_id=provider_msg_id
            )
            success_msg = f"Email notification successfully accepted by Brevo for parent ({clean_email})!"
            return True, success_msg, "ACCEPTED"
        else:
            record_notification_attempt(
                student_id=clean_sid,
                roll=clean_roll,
                attendance_date=clean_date,
                status=clean_status,
                recipient_email=clean_email,
                delivery_result="FAILED",
                provider_message_id="",
                error_details=provider_msg
            )
            _append_to_audit_log(
                "FAILED", clean_sid, clean_roll, clean_name, clean_date, clean_status,
                clean_email, "FAILED", provider_msg
            )
            return False, provider_msg, "FAILED"
    except Exception as ex:
        err_msg = f"Unexpected transmission error: {type(ex).__name__}"
        _append_to_audit_log(
            "SYS_ERROR",
            clean_sid if 'clean_sid' in locals() else str(student_id),
            clean_roll if 'clean_roll' in locals() else str(roll),
            clean_name if 'clean_name' in locals() else str(student_name),
            clean_date if 'clean_date' in locals() else datetime.now().strftime("%d/%m/%Y"),
            clean_status if 'clean_status' in locals() else str(status),
            clean_email if 'clean_email' in locals() else str(parent_email),
            "FAILED", err_msg
        )
        return False, err_msg, "FAILED"


# Backward-compatible function alias
def load_email_config() -> Dict[str, Any]:
    """Backward-compatible loader alias returning current Brevo configuration."""
    return get_brevo_config()


def save_email_config(config: Dict[str, Any]) -> bool:
    """Backward-compatible saver alias persisting to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception:
        return False


def send_attendance_email(student_name: str, roll: str, dep: str = "",
                          date_str: str = "", time_str: str = "", status: str = "PRESENT",
                          parent_email: str = "", department: str = "", student_id: str = "",
                          force: bool = False, **kwargs) -> Tuple[bool, str]:
    """
    Synchronous wrapper matching legacy signature.
    Routes directly to Brevo Transactional Email Dispatcher.
    """
    actual_dep = dep or department or kwargs.get("department", "General")
    ok, msg, _ = send_parent_attendance_notification(
        student_id=student_id,
        roll=roll,
        student_name=student_name,
        dep=actual_dep,
        date_str=date_str,
        time_str=time_str,
        status=status,
        parent_email=parent_email,
        force=force
    )
    return ok, msg


def send_attendance_email_async(student_name: str, roll: str, dep: str = "",
                                date_str: str = "", time_str: str = "", status: str = "PRESENT",
                                parent_email: str = "", callback=None, department: str = "",
                                student_id: str = "", force: bool = False, **kwargs):
    """
    Non-blocking background thread wrapper for send_parent_attendance_notification.
    Guarantees that face recognition and UI loops NEVER freeze or stutter.
    Supports deterministic synchronization via the returned Thread or optional completion_event.
    """
    actual_dep = dep or department or kwargs.get("department", "General")
    completion_event = kwargs.get("completion_event")
    
    def _worker():
        try:
            ok, msg, outcome = send_parent_attendance_notification(
                student_id=student_id,
                roll=roll,
                student_name=student_name,
                dep=actual_dep,
                date_str=date_str,
                time_str=time_str,
                status=status,
                parent_email=parent_email,
                force=force,
                config=kwargs.get("config")
            )
            if callback:
                try:
                    callback(ok, msg)
                except Exception:
                    pass
        finally:
            if completion_event is not None and hasattr(completion_event, "set"):
                try:
                    completion_event.set()
                except Exception:
                    pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t


# ========================================================================================
# 6. Test Email Configuration Utility
# ========================================================================================

def test_brevo_connection(recipient_email: str,
                           config: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Tests Brevo API connectivity, credentials, and sender verification by dispatching
    a diagnostic test email to the specified recipient.
    """
    if not recipient_email or not is_valid_email(recipient_email):
        return False, "Please provide a valid recipient email address for testing."

    cfg = config or get_brevo_config()
    if not cfg.get("is_configured", False):
        return False, "Brevo credentials are not configured. Set BREVO_API_KEY and BREVO_SENDER_EMAIL in .env."

    now = datetime.now()
    subject = "FaceAttend: Brevo API Diagnostic Test Notice"
    plain_text = f"""FaceAttend Biometric System - Brevo Diagnostic Test
Timestamp: {now.strftime("%Y-%m-%d %H:%M:%S")}
Sender: {cfg.get('sender_name')} <{cfg.get('sender_email')}>
Status: Brevo Transactional Email API Connection Verified!
"""
    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; background: #071a35; color: #ffffff; padding: 24px;">
  <div style="max-width: 500px; margin: auto; background: #030b18; padding: 24px; border-radius: 8px; border: 1px solid #0284c7;">
    <h2 style="color: #38bdf8; margin-top: 0;">✓ Brevo API Connection Verified!</h2>
    <p>This is a diagnostic verification email from the <strong>FaceAttend Biometric System</strong>.</p>
    <p><strong>Configured Sender:</strong> {cfg.get('sender_name')} &lt;{cfg.get('sender_email')}&gt;</p>
    <p><strong>Timestamp:</strong> {now.strftime("%d/%m/%Y %I:%M:%S %p")}</p>
    <hr style="border-color: #1e293b;">
    <p style="font-size: 11px; color: #94a3b8;">FaceAttend Biometrics • KIIT University</p>
  </div>
</body>
</html>"""

    ok, msg, msg_id = send_brevo_email(
        to_email=recipient_email,
        to_name="FaceAttend Administrator",
        subject=subject,
        html_content=html_body,
        text_content=plain_text,
        config=cfg
    )
    if ok:
        _append_to_audit_log(
            "TEST_EMAIL", student_id="-", roll="-", student_name="Test",
            attendance_date=now.strftime("%d/%m/%Y"), status="TEST",
            to_email=recipient_email, outcome="ACCEPTED",
            details="Diagnostic configuration test succeeded", provider_message_id=msg_id or ""
        )
        return True, f"Success! Brevo accepted the diagnostic test email.\n\nProvider Message ID:\n{msg_id}"
    else:
        _append_to_audit_log(
            "TEST_EMAIL", student_id="-", roll="-", student_name="Test",
            attendance_date=now.strftime("%d/%m/%Y"), status="TEST",
            to_email=recipient_email, outcome="FAILED",
            details=msg
        )
        return False, msg


def preview_email_in_browser(student_name: str = "Ved Prakash Pandey", 
                             roll: str = "23053645", 
                             dep: str = "Computer Science & Engineering", 
                             date_str: str = "", 
                             time_str: str = "", 
                             status: str = "PRESENT", 
                             parent_email: str = "") -> str:
    """
    Renders and launches the exact HTML parent notification email in the default web browser.
    Ensures seamless offline demonstration and visual inspection without consuming API credits.
    """
    now = datetime.now()
    date_str = date_str or now.strftime("%d/%m/%Y")
    time_str = time_str or now.strftime("%I:%M:%S %p")

    cfg = get_brevo_config()
    subject, _, html_body = build_email_content(
        student_name=student_name,
        roll=roll,
        dep=dep,
        date_str=date_str,
        time_str=time_str,
        status=status,
        mentor_name=cfg.get("mentor_name", "Mr. Rakesh Kumar Rai"),
        institution_name=cfg.get("institution_name", "School of Computer Engineering, KIIT University")
    )

    preview_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{subject}</title>
<style>
  body {{ margin: 0; padding: 0; background-color: #030b18; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
  .client-bar {{ background-color: #071a35; color: #f8fafc; padding: 12px 24px; border-bottom: 2px solid #0284c7; }}
  .client-bar h2 {{ margin: 0 0 4px 0; font-size: 15px; color: #38bdf8; display: flex; align-items: center; gap: 8px; }}
  .meta-row {{ font-size: 12px; color: #94a3b8; margin: 2px 0; }}
  .meta-val {{ color: #ffffff; font-weight: 600; }}
  .email-wrapper {{ max-width: 620px; margin: 24px auto; box-shadow: 0 8px 24px rgba(0,0,0,0.5); border-radius: 12px; overflow: hidden; }}
</style>
</head>
<body>
  <div class="client-bar">
    <h2><span>✉</span> FaceAttend HTML Parent Notification Preview (Brevo Template)</h2>
    <div class="meta-row">Recipient: <span class="meta-val">{parent_email or '[Parent Email from Database]'}</span></div>
    <div class="meta-row">Subject: <span class="meta-val">{subject}</span></div>
    <div class="meta-row">Timestamp: <span class="meta-val">{date_str} at {time_str}</span></div>
  </div>
  <div class="email-wrapper">
    {html_body}
  </div>
</body>
</html>"""

    with open(PREVIEW_FILE, "w", encoding="utf-8") as f:
        f.write(preview_html)

    file_url = f"file:///{os.path.abspath(PREVIEW_FILE).replace(os.sep, '/')}"
    try:
        webbrowser.open(file_url)
    except Exception:
        pass
    return file_url


# ========================================================================================
# 7. Interactive Brevo Configuration Modal Dialog
# ========================================================================================

def open_email_config_dialog(parent_root):
    """
    Renders an interactive Cyber-Themed configuration modal dialog allowing
    administrators to inspect/update Brevo API credentials, test connectivity,
    and review audit logs.
    """
    import tkinter as tk
    from tkinter import ttk, messagebox

    cfg = get_brevo_config()
    dlg = tk.Toplevel(parent_root)
    dlg.title("FaceAttend - Brevo API Email Notification Settings")

    # Responsive window calculation
    screen_w = dlg.winfo_screenwidth()
    screen_h = dlg.winfo_screenheight()
    win_w = min(740, max(640, int(screen_w * 0.60)))
    win_h = min(580, max(500, int(screen_h * 0.80)))
    x = max(10, (screen_w - win_w) // 2)
    y = max(10, (screen_h - win_h) // 2 - 20)

    dlg.geometry(f"{win_w}x{win_h}+{x}+{y}")
    dlg.minsize(620, 480)
    dlg.resizable(True, True)
    dlg.config(bg="#030b18")
    dlg.transient(parent_root)
    dlg.grab_set()

    # 1. Action Bar (Pinned to BOTTOM FIRST so it is NEVER cut off)
    btn_bar = tk.Frame(dlg, bg="#030b18", padx=14, pady=10)
    btn_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # 2. Header Banner (TOP)
    hdr = tk.Frame(dlg, bg="#071a35", padx=16, pady=10, bd=1, relief=tk.SOLID)
    hdr.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(10, 6))

    tk.Label(hdr, text="⚡ Brevo Transactional Email Notification Engine", 
             font=("Segoe UI", 12, "bold"), fg="#38bdf8", bg="#071a35").pack(anchor="w")
    tk.Label(hdr, text="Official Brevo REST API v3 (No SMTP • No Google App Passwords • HTTPS Delivery)", 
             font=("Segoe UI", 9), fg="#94a3b8", bg="#071a35").pack(anchor="w", pady=(2, 0))

    # 3. Main Form Box
    main_frame = tk.Frame(dlg, bg="#030b18")
    main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=(0, 6))

    var_api_key = tk.StringVar(value=cfg.get("api_key", ""))
    var_sender_email = tk.StringVar(value=cfg.get("sender_email", ""))
    var_sender_name = tk.StringVar(value=cfg.get("sender_name", "FaceAttend Biometrics - KIIT University"))
    var_test_recipient = tk.StringVar(value="")
    var_show_key = tk.BooleanVar(value=False)

    entry_opts = {
        "font": ("Segoe UI", 9), "bg": "#06152b", "fg": "#ffffff",
        "insertbackground": "#38bdf8", "bd": 1, "relief": tk.SOLID,
        "highlightthickness": 1, "highlightbackground": "#1e3a5f"
    }

    # SECTION 1: Credentials
    sec_cred = tk.LabelFrame(main_frame, text=" 🔑 Brevo API Credentials & Verified Sender ", 
                             font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#091f40", 
                             bd=1, relief=tk.SOLID, padx=14, pady=8)
    sec_cred.pack(fill=tk.X, pady=(0, 8))
    sec_cred.columnconfigure(1, weight=1)

    # Row 0: API Key
    tk.Label(sec_cred, text="Brevo API Key (v3):", font=("Segoe UI", 9, "bold"), 
             fg="#cbd5e1", bg="#091f40").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
    key_frame = tk.Frame(sec_cred, bg="#091f40")
    key_frame.grid(row=0, column=1, sticky="ew", pady=4)
    key_entry = tk.Entry(key_frame, textvariable=var_api_key, show="•", **entry_opts)
    key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def toggle_key_visibility():
        if var_show_key.get():
            key_entry.config(show="")
        else:
            key_entry.config(show="•")

    chk_show = tk.Checkbutton(key_frame, text="Show", variable=var_show_key,
                              font=("Segoe UI", 8), bg="#091f40", fg="#94a3b8",
                              selectcolor="#06152b", activebackground="#091f40",
                              activeforeground="#38bdf8", command=toggle_key_visibility)
    chk_show.pack(side=tk.LEFT, padx=6)

    # Row 1: Sender Email
    tk.Label(sec_cred, text="Verified Sender Email:", font=("Segoe UI", 9, "bold"), 
             fg="#cbd5e1", bg="#091f40").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
    tk.Entry(sec_cred, textvariable=var_sender_email, **entry_opts).grid(row=1, column=1, sticky="ew", pady=4)

    # Row 2: Sender Name
    tk.Label(sec_cred, text="Sender Display Name:", font=("Segoe UI", 9, "bold"), 
             fg="#cbd5e1", bg="#091f40").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
    tk.Entry(sec_cred, textvariable=var_sender_name, **entry_opts).grid(row=2, column=1, sticky="ew", pady=4)

    # Info Notice
    info_text = (
        "💡 Setup Guide:\n"
        "• API keys start with 'xkeysib-...'. Generate one at: https://app.brevo.com/settings/keys/api\n"
        "• Sender email MUST be verified under Senders & IP: https://app.brevo.com/senders\n"
        "• Free plan provides 300 free emails/day. Settings persist to your local '.env' file."
    )
    tk.Label(sec_cred, text=info_text, font=("Segoe UI", 8), fg="#94a3b8", bg="#091f40", justify=tk.LEFT).grid(
        row=3, column=0, columnspan=2, sticky="w", pady=(4, 2)
    )

    # SECTION 2: Diagnostic Testing
    sec_test = tk.LabelFrame(main_frame, text=" 🧪 Diagnostic Connectivity Test ", 
                             font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#091f40", 
                             bd=1, relief=tk.SOLID, padx=14, pady=8)
    sec_test.pack(fill=tk.X, pady=(0, 4))
    sec_test.columnconfigure(1, weight=1)

    tk.Label(sec_test, text="Test Recipient Email:", font=("Segoe UI", 9, "bold"), 
             fg="#cbd5e1", bg="#091f40").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
    tk.Entry(sec_test, textvariable=var_test_recipient, **entry_opts).grid(row=0, column=1, sticky="ew", pady=4)

    test_actions = tk.Frame(sec_test, bg="#091f40")
    test_actions.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 2))

    def do_run_test():
        recipient = var_test_recipient.get().strip()
        if not recipient or not is_valid_email(recipient):
            messagebox.showwarning(
                "Input Required", 
                "Please enter a valid recipient email address to test delivery.", 
                parent=dlg
            )
            return

        temp_cfg = {
            "api_key": var_api_key.get().strip(),
            "sender_email": var_sender_email.get().strip(),
            "sender_name": var_sender_name.get().strip() or "FaceAttend Biometrics",
            "is_configured": bool(var_api_key.get().strip() and var_sender_email.get().strip())
        }

        ok, msg = test_brevo_connection(recipient, config=temp_cfg)
        if ok:
            messagebox.showinfo("Test Email Accepted!", msg, parent=dlg)
        else:
            messagebox.showerror("Delivery Error", msg, parent=dlg)

    def do_preview_html():
        preview_email_in_browser(
            student_name="Ved Prakash Pandey",
            roll="23053645",
            dep="Computer Science and Engineering",
            status="PRESENT",
            parent_email=var_test_recipient.get().strip() or "[Parent Email]"
        )

    tk.Button(test_actions, text="🚀 Send Test Email via Brevo API", font=("Segoe UI", 9, "bold"), 
              bg="#0284c7", fg="#ffffff", activebackground="#0369a1", bd=0, 
              cursor="hand2", padx=12, pady=4, command=do_run_test).pack(side=tk.LEFT, padx=(0, 6))

    tk.Button(test_actions, text="👁 Preview HTML Template", font=("Segoe UI", 9), 
              bg="#10b981", fg="#ffffff", activebackground="#059669", bd=0, 
              cursor="hand2", padx=10, pady=4, command=do_preview_html).pack(side=tk.LEFT, padx=4)

    # 4. Save and Close Actions
    def do_save():
        key = var_api_key.get().strip()
        sender_email = var_sender_email.get().strip()
        sender_name = var_sender_name.get().strip() or "FaceAttend Biometrics - KIIT University"

        # Update running os.environ immediately
        if key:
            os.environ["BREVO_API_KEY"] = key
        if sender_email:
            os.environ["BREVO_SENDER_EMAIL"] = sender_email
        if sender_name:
            os.environ["BREVO_SENDER_NAME"] = sender_name

        # Persist to .env file
        env_lines = [
            "# FaceAttend Brevo Email Configuration",
            f"BREVO_API_KEY={key}",
            f"BREVO_SENDER_EMAIL={sender_email}",
            f"BREVO_SENDER_NAME={sender_name}",
            f"BREVO_INSTITUTION_NAME=School of Computer Engineering, KIIT University",
            f"BREVO_MENTOR_NAME=Mr. Rakesh Kumar Rai\n"
        ]
        try:
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(env_lines))
        except Exception as e:
            messagebox.showwarning("Notice", f"Could not write to .env file: {e}", parent=dlg)

        # Also persist to config/email_config.json for backward compatibility
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "brevo_api_key": key,
                    "brevo_sender_email": sender_email,
                    "brevo_sender_name": sender_name,
                    "school_name": "School of Computer Engineering, KIIT University",
                    "mentor_name": "Mr. Rakesh Kumar Rai"
                }, f, indent=4)
        except Exception:
            pass

        messagebox.showinfo("Saved", "Brevo configuration successfully saved to .env!", parent=dlg)
        dlg.destroy()

    def do_view_logs():
        if os.path.exists(LOG_FILE):
            os.system(f'notepad.exe "{LOG_FILE}"')
        else:
            messagebox.showinfo("Notice", "No email notification logs recorded yet.", parent=dlg)

    tk.Button(btn_bar, text="💾 Save Configuration (.env)", font=("Segoe UI", 9, "bold"), 
              bg="#0084ff", fg="#ffffff", activebackground="#006cd4", bd=0, 
              cursor="hand2", padx=14, pady=6, command=do_save).pack(side=tk.LEFT, padx=4)

    tk.Button(btn_bar, text="📋 View Audit Log", font=("Segoe UI", 9), 
              bg="#334155", fg="#cbd5e1", activebackground="#475569", bd=0, 
              cursor="hand2", padx=10, pady=6, command=do_view_logs).pack(side=tk.LEFT, padx=4)

    tk.Button(btn_bar, text="✕ Close", font=("Segoe UI", 9), 
              bg="#1e293b", fg="#94a3b8", activebackground="#334155", bd=0, 
              cursor="hand2", padx=10, pady=6, command=dlg.destroy).pack(side=tk.RIGHT, padx=4)
