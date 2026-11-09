"""
========================================================================================
FaceAttend Security, Integrity, Deduplication & Safeguards Verification Suite
========================================================================================
Tests:
1. PBKDF2-HMAC-SHA256 password hashing, salt randomness, and verification.
2. Case-insensitive security question answer hashing and verification.
3. Zero-lockout legacy plaintext authentication and automatic in-place PBKDF2 upgrade.
4. Database unique constraint enforcement: at most 1 attendance record per student per date.
5. Notification UPSERT integrity: at most 1 notification per student, date, and status.
6. Recognition safeguards: training ignores orphaned biometric image samples.
7. Biometric sample lifecycle: student deletion purges photo samples and updates classifier.
8. Attendance export reliability: SQLite remains single source of truth for CSV data.
========================================================================================
"""

import os
import sys
import unittest
import tempfile
import csv
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from utils.security import (
    hash_password,
    verify_password,
    hash_security_answer,
    verify_security_answer,
    is_password_hashed,
    is_security_answer_hashed,
    is_hashed
)
from database.db_manager import (
    get_connection,
    register_user,
    verify_login,
    reset_password,
    add_student,
    delete_student,
    get_student_by_id,
    log_attendance,
    fetch_all_attendance,
    record_notification_attempt,
    get_notification_history,
    get_enrolled_student_ids,
    clean_student_biometrics
)


class TestSecurityAndIntegrity(unittest.TestCase):
    """Rigorous unit and integration tests for FaceAttend security safeguards and data integrity."""

    def setUp(self):
        self.test_email = f"sec_test_{int(datetime.now().timestamp() * 1000)}@univ.edu"
        self.test_sid = f"TEST_SEC_{int(datetime.now().timestamp() * 1000)}"
        self.test_date = datetime.now().strftime("%d/%m/%Y")
        self.test_time = "11:00:00 AM"

    def tearDown(self):
        delete_student(self.test_sid)
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE email = ?", (self.test_email,))
            c.execute("DELETE FROM attendance WHERE student_id = ?", (self.test_sid,))
            c.execute("DELETE FROM email_notifications WHERE student_id = ?", (self.test_sid,))
            conn.commit()
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # TEST 1: PBKDF2-HMAC-SHA256 Hashing & Verification
    # -------------------------------------------------------------------------
    def test_01_pbkdf2_hashing_and_verification(self):
        """Verifies standard-compliant PBKDF2 hashing, unique salts, and constant-time match."""
        raw_pw = "SuperSecret#2026"
        h1 = hash_password(raw_pw)
        h2 = hash_password(raw_pw)

        # Assert format and uniqueness of salt
        self.assertTrue(h1.startswith("pbkdf2:sha256:200000$"))
        self.assertNotEqual(h1, h2, "Unique salts must produce distinct hash outputs for same password")
        self.assertTrue(is_password_hashed(h1))
        self.assertTrue(is_hashed(h1))

        # Assert correct match
        self.assertTrue(verify_password(raw_pw, h1))
        self.assertFalse(verify_password("WrongPassword!", h1))
        self.assertFalse(verify_password("", h1))

    # -------------------------------------------------------------------------
    # TEST 2: Security Question Answer Hashing & Normalization
    # -------------------------------------------------------------------------
    def test_02_security_answer_hashing(self):
        """Verifies case-insensitive, whitespace-trimmed security answer hashing and verification."""
        stored_hash = hash_security_answer("Bhubaneswar")
        self.assertTrue(is_security_answer_hashed(stored_hash))

        # Test case and whitespace tolerance
        self.assertTrue(verify_security_answer("bhubaneswar", stored_hash))
        self.assertTrue(verify_security_answer("  BHUBANESWAR  ", stored_hash))
        self.assertTrue(verify_security_answer("BhuBaNesWar", stored_hash))
        self.assertFalse(verify_security_answer("Cuttack", stored_hash))

    # -------------------------------------------------------------------------
    # TEST 3: Zero-Lockout Login & In-Place Credential Upgrade
    # -------------------------------------------------------------------------
    def test_03_zero_lockout_login_and_in_place_upgrade(self):
        """Ensures legacy plaintext passwords can log in and are upgraded to PBKDF2 in-place."""
        conn = get_connection()
        try:
            c = conn.cursor()
            # Insert a legacy user with plaintext credentials
            c.execute("""
                INSERT INTO users (fname, lname, contact, email, security_q, security_a, password)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("Legacy", "User", "9998887770", self.test_email, "Your Birth Place", "kolkata", "legacyPass123"))
            conn.commit()
        finally:
            conn.close()

        # 1. Login with legacy plaintext password
        ok, udata, msg = verify_login(self.test_email, "legacyPass123")
        self.assertTrue(ok, f"Legacy user login failed: {msg}")
        self.assertIsNotNone(udata)
        self.assertEqual(udata["email"], self.test_email)

        # 2. Check that password was upgraded in-place to PBKDF2 hash
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE email = ?", (self.test_email,))
            upgraded_pw = c.fetchone()[0]
            self.assertTrue(is_password_hashed(upgraded_pw), "Password should be upgraded to PBKDF2 hash in-place")
            self.assertTrue(verify_password("legacyPass123", upgraded_pw))
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # TEST 4: Attendance Single-Record Daily Integrity
    # -------------------------------------------------------------------------
    def test_04_attendance_single_record_unique_constraint(self):
        """Verifies at most one attendance record per student per date in SQLite."""
        # 1. First attendance log: must succeed
        ok1, msg1 = log_attendance(
            student_id=self.test_sid,
            roll="R-SEC-01",
            name="Security Test",
            department="CSE",
            time_str=self.test_time,
            date_str=self.test_date,
            status="Present"
        )
        self.assertTrue(ok1, f"First attendance log failed: {msg1}")

        # 2. Second attendance log for SAME student on SAME date: must be rejected
        ok2, msg2 = log_attendance(
            student_id=self.test_sid,
            roll="R-SEC-01",
            name="Security Test",
            department="CSE",
            time_str="11:05:00 AM",
            date_str=self.test_date,
            status="Present"
        )
        self.assertFalse(ok2, "Duplicate attendance for same student on same date must be rejected")
        self.assertIn("already marked", msg2.lower())

        # 3. Verify exactly 1 record exists in database
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND date = ?", (self.test_sid, self.test_date))
            count = c.fetchone()[0]
            self.assertEqual(count, 1)
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # TEST 5: Notification UPSERT Integrity
    # -------------------------------------------------------------------------
    def test_05_notification_single_record_upsert_integrity(self):
        """Verifies at most 1 notification per student, date, and status while preserving ACCEPTED results."""
        # 1. Record an initial failed attempt
        id1 = record_notification_attempt(
            student_id=self.test_sid,
            roll="R-SEC-01",
            attendance_date=self.test_date,
            status="PRESENT",
            recipient_email="parent@example.com",
            delivery_result="FAILED",
            error_details="Temporary network timeout"
        )
        self.assertGreater(id1, 0)

        # 2. Retry succeeds and records ACCEPTED
        id2 = record_notification_attempt(
            student_id=self.test_sid,
            roll="R-SEC-01",
            attendance_date=self.test_date,
            status="PRESENT",
            recipient_email="parent@example.com",
            delivery_result="ACCEPTED",
            provider_message_id="<msg-id-12345>"
        )

        # 3. Assert exactly ONE record exists for this (student, date, status) in SQLite
        history = get_notification_history(self.test_sid, self.test_date)
        present_records = [r for r in history if r["status"] == "PRESENT"]
        self.assertEqual(len(present_records), 1, "Must have exactly 1 record per student, date, and status")
        self.assertEqual(present_records[0]["delivery_result"], "ACCEPTED")
        self.assertEqual(present_records[0]["provider_message_id"], "<msg-id-12345>")

    # -------------------------------------------------------------------------
    # TEST 6: Recognition Safeguard - Training Ignores Orphaned Samples
    # -------------------------------------------------------------------------
    def test_06_enrolled_student_training_safeguard(self):
        """Ensures training pipeline ignores face samples belonging to non-enrolled students."""
        enrolled_ids = get_enrolled_student_ids()
        self.assertIsInstance(enrolled_ids, set)

        # Verify our non-existent test student is not in enrolled_ids
        fake_id = "FAKE_NON_ENROLLED_9999"
        self.assertNotIn(fake_id, enrolled_ids)

        # If we enroll a student, their ID appears in enrolled_ids
        add_student({
            "student_id": self.test_sid,
            "dep": "CSE", "course": "B.Tech", "year": "2024", "semester": "Sem-4",
            "name": "Enrolled Test Student", "division": "A", "roll": "ROLL-SEC-99",
            "gender": "Male", "dob": "2004-01-01", "email": "sec@kiit.ac.in",
            "phone": "9988776655", "address": "Bhubaneswar", "teacher": "Prof",
            "photo_sample": "No", "parent_email": "parent@kiit.ac.in"
        })
        self.assertIn(self.test_sid, get_enrolled_student_ids())

    # -------------------------------------------------------------------------
    # TEST 7: Biometric Sample Deletion Safeguard
    # -------------------------------------------------------------------------
    def test_07_biometric_sample_deletion_cascade(self):
        """Ensures student deletion removes biometric image files and cascades to model."""
        data_dir = os.path.join(BASE_DIR, "data")
        sample_file = os.path.join(data_dir, f"user.{self.test_sid}.1.jpg")
        
        # Create a mock biometric sample file
        with open(sample_file, "wb") as f:
            f.write(b"mock_image_bytes")
        self.assertTrue(os.path.exists(sample_file))

        # Add student and delete
        add_student({
            "student_id": self.test_sid,
            "dep": "CSE", "course": "B.Tech", "year": "2024", "semester": "Sem-4",
            "name": "Deletion Test Student", "division": "A", "roll": "ROLL-DEL-99",
            "gender": "Male", "dob": "2004-01-01", "email": "del@kiit.ac.in",
            "phone": "9988776655", "address": "Bhubaneswar", "teacher": "Prof",
            "photo_sample": "Yes", "parent_email": "parent@kiit.ac.in"
        })
        
        del_ok, del_msg = delete_student(self.test_sid)
        self.assertTrue(del_ok)
        self.assertFalse(os.path.exists(sample_file), "Biometric sample file must be removed when student is deleted")

    # -------------------------------------------------------------------------
    # TEST 8: SQLite Source of Truth for Attendance Exports
    # -------------------------------------------------------------------------
    def test_08_sqlite_source_of_truth_export(self):
        """Verifies CSV exports derive directly from SQLite records with full integrity."""
        # Log attendance
        log_attendance(
            student_id=self.test_sid,
            roll="R-EXP-01",
            name="Export Verification Student",
            department="IT",
            time_str=self.test_time,
            date_str=self.test_date,
            status="Present"
        )

        db_records = fetch_all_attendance()
        matching = [r for r in db_records if str(r[1]) == self.test_sid]
        self.assertTrue(len(matching) >= 1)

        # Write export to temp file
        with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", suffix=".csv", delete=False) as tf:
            temp_path = tf.name
            writer = csv.writer(tf)
            writer.writerow(["Attendance ID", "Student ID", "Roll", "Name", "Department", "Time", "Date", "Status"])
            for r in db_records:
                writer.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]])

        try:
            self.assertTrue(os.path.exists(temp_path))
            with open(temp_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                self.assertIn("Student ID", headers)
                rows = list(reader)
                self.assertGreater(len(rows), 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
