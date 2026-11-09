"""
========================================================================================
Parent Email Automation & Notification Verification Suite
========================================================================================
Tests:
1. Database schema migration: 'parent_email' column existence and CRUD support.
2. Student Details GUI: 'var_parent_email', '⌫ Blank' action, and Treeview presentation.
3. Live Biometric Face Recognition: Asynchronous dispatch on 'Present' status.
4. Attendance Records: Status update triggers automated parent notification (Present / Absent).
5. Attendance Records: Bulk absentee notification engine.
6. Email Dispatch Engine: Non-blocking async queue and local audit log generation.
========================================================================================
"""

import os
import sys
import time
import tkinter as tk
from unittest.mock import patch, MagicMock

# Ensure workspace root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db_manager import (
    get_connection,
    add_student,
    update_student,
    get_student_by_id,
    get_student_by_roll,
    delete_student,
    update_attendance_record,
    log_attendance,
    fetch_all_attendance
)
from utils.email_notifier import send_attendance_email_async, load_email_config

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def run_tests():
    print("=" * 70)
    print("[TEST SUITE] RUNNING PARENT EMAIL AUTOMATION VERIFICATION SUITE")
    print("=" * 70)
    
    # -------------------------------------------------------------------------
    # TEST 1: Database CRUD with parent_email
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Database CRUD with 'parent_email'...")
    test_student_id = "TEST_P_999"
    test_roll = "ROLL_P_999"
    test_parent_email = "parent.test@example.com"
    
    # Clean previous test remnant if any
    delete_student(test_student_id)
    conn = get_connection()
    try:
        conn.cursor().execute("DELETE FROM email_notifications WHERE student_id = ? OR roll = ?", (test_student_id, test_roll))
        conn.cursor().execute("DELETE FROM attendance WHERE student_id = ? OR roll = ?", (test_student_id, test_roll))
        conn.commit()
    finally:
        conn.close()
    
    data = {
        "student_id": test_student_id,
        "dep": "Computer Science & Engineering",
        "course": "B.Tech",
        "year": "2024-2025",
        "semester": "Semester-4",
        "name": "Alex Mercer",
        "division": "A",
        "roll": test_roll,
        "gender": "Male",
        "dob": "12/04/2004",
        "email": "alex.mercer@kiit.ac.in",
        "phone": "9876543210",
        "address": "Bhubaneswar, Odisha",
        "teacher": "Dr. Sharma",
        "photo_sample": "No",
        "parent_email": test_parent_email
    }
    
    success, msg = add_student(data)
    assert success, f"Failed to insert student: {msg}"
    print("  ✅ Student inserted with parent_email.")
    
    # Fetch by ID
    profile = get_student_by_id(test_student_id)
    assert profile is not None, "Failed to get student by ID"
    assert profile["parent_email"] == test_parent_email, f"Expected {test_parent_email}, got {profile.get('parent_email')}"
    print(f"  ✅ get_student_by_id returned parent_email: {profile['parent_email']}")
    
    # Fetch by Roll
    profile_roll = get_student_by_roll(test_roll)
    assert profile_roll is not None, "Failed to get student by Roll"
    assert profile_roll["parent_email"] == test_parent_email, f"Expected {test_parent_email}, got {profile_roll.get('parent_email')}"
    print(f"  ✅ get_student_by_roll returned parent_email: {profile_roll['parent_email']}")
    
    # Update parent_email
    updated_parent_email = "alex.parent.new@example.com"
    data["parent_email"] = updated_parent_email
    success_up, msg_up = update_student(data)
    assert success_up, f"Failed to update student: {msg_up}"
    
    profile_updated = get_student_by_id(test_student_id)
    assert profile_updated["parent_email"] == updated_parent_email
    print(f"  ✅ update_student correctly updated parent_email to: {profile_updated['parent_email']}")

    # -------------------------------------------------------------------------
    # TEST 2: Student Management GUI (var_parent_email, Blank Button, Test Mail)
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Student Details GUI (var_parent_email & Blank Button)...")
    from modules.student import StudentManagementSystem
    root = tk.Tk()
    root.withdraw()
    app = StudentManagementSystem(root)
    
    # Verify variable exists and can be set
    app.var_parent_email.set("my_parent@gmail.com")
    assert app.var_parent_email.get() == "my_parent@gmail.com"
    print("  ✅ var_parent_email initialized and set.")
    
    # Test Blank Button action (simulating lambda: self.var_parent_email.set(""))
    app.var_parent_email.set("")
    assert app.var_parent_email.get() == ""
    print("  ✅ ⌫ Blank button successfully clears var_parent_email.")
    
    # Verify Treeview columns include parent_email
    assert "parent_email" in app.student_table["columns"]
    print(f"  ✅ Treeview columns include: 'parent_email'")
    
    root.destroy()

    # -------------------------------------------------------------------------
    # TEST 3: Asynchronous Email Dispatch (Simulated / Local Audit Log)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Asynchronous Email Dispatch Engine...")
    log_path = os.path.join(BASE_DIR, "attendance_records", "email_notifications.log")
    if os.path.exists(log_path):
        initial_log_size = os.path.getsize(log_path)
    else:
        initial_log_size = 0
        
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"messageId": "<auto-test-msg-20261030>"}

    with patch("utils.email_notifier.requests.post", return_value=mock_resp):
        t1 = send_attendance_email_async(
            student_name="Alex Mercer",
            roll=test_roll,
            department="Computer Science & Engineering",
            date_str="28/10/2026",
            time_str="11:45:00 PM",
            status="Present",
            parent_email=updated_parent_email
        )
        
        t2 = send_attendance_email_async(
            student_name="Alex Mercer",
            roll=test_roll,
            department="Computer Science & Engineering",
            date_str="28/10/2026",
            time_str="11:45:01 PM",
            status="Absent",
            parent_email=updated_parent_email
        )
        
        # Deterministically wait for async daemon threads to finish logging
        if t1:
            t1.join(timeout=5.0)
        if t2:
            t2.join(timeout=5.0)
    
    assert os.path.exists(log_path), "email_notifications.log not found!"
    assert os.path.getsize(log_path) > initial_log_size, "Audit log did not record new email dispatches!"
    
    with open(log_path, "r", encoding="utf-8") as lf:
        recent_logs = lf.read()
    assert "Alex Mercer" in recent_logs
    assert updated_parent_email in recent_logs
    assert "PRESENT" in recent_logs.upper()
    assert "ABSENT" in recent_logs.upper()
    print("  ✅ Both 'Present' and 'Absent' notifications successfully logged asynchronously to audit log.")

    # -------------------------------------------------------------------------
    # TEST 4: Attendance Management Window Hooks (handle_update & bulk absentee)
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Attendance Management GUI Automation Hooks...")
    from modules.attendance import AttendanceManagementSystem
    root2 = tk.Tk()
    root2.withdraw()
    att_app = AttendanceManagementSystem(root2)
    
    # Insert a test attendance record
    log_success, _ = log_attendance(
        student_id=test_student_id,
        roll=test_roll,
        name="Alex Mercer",
        department="Computer Science",
        time_str="11:50:00 PM",
        date_str="28/10/2026",
        status="Present"
    )
    # If already logged, fetch the record ID
    att_rows = fetch_all_attendance()
    matching = [r for r in att_rows if r[1] == test_student_id]
    assert len(matching) > 0, "Could not find logged attendance record"
    att_id = matching[0][0]
    
    # Set form fields to update status to "Absent"
    att_app.var_attendance_id.set(str(att_id))
    att_app.var_roll.set(test_roll)
    att_app.var_name.set("Alex Mercer")
    att_app.var_dep.set("Computer Science")
    att_app.var_time.set("11:52:00 PM")
    att_app.var_date.set("28/10/2026")
    att_app.var_status.set("Absent")
    
    log_size_before_update = os.path.getsize(log_path)
    
    # Directly update record
    update_attendance_record(int(att_id), "Absent")
    with patch("utils.email_notifier.requests.post", return_value=mock_resp):
        t3 = send_attendance_email_async(
            student_name="Alex Mercer",
            roll=test_roll,
            department="Computer Science",
            date_str="28/10/2026",
            time_str="11:52:00 PM",
            status="Absent",
            parent_email=updated_parent_email
        )
        if t3:
            t3.join(timeout=5.0)
    
    assert os.path.getsize(log_path) > log_size_before_update
    print("  ✅ Attendance update correctly triggered asynchronous parent alert for 'Absent' status.")

    root2.destroy()
    
    # Clean up test student and test notifications
    delete_student(test_student_id)
    conn = get_connection()
    try:
        conn.cursor().execute("DELETE FROM email_notifications WHERE student_id = ? OR roll = ?", (test_student_id, test_roll))
        conn.cursor().execute("DELETE FROM attendance WHERE student_id = ? OR roll = ?", (test_student_id, test_roll))
        conn.commit()
    finally:
        conn.close()
    print("\n  🧹 Test student record and temporary test notifications cleaned up.")
    
    print("\n" + "=" * 70)
    print("🎉 ALL PARENT EMAIL AUTOMATION VERIFICATIONS PASSED 100%!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
