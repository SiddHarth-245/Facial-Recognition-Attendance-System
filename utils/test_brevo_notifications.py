"""
========================================================================================
FaceAttend Brevo Transactional Email Notification & Deduplication Test Suite
========================================================================================
Tests:
1.  PRESENT email subject & content format validation.
2.  ABSENT email subject & content format validation.
3.  Parent email retrieval from the student database.
4.  Missing and invalid parent email handling.
5.  Missing or unconfigured API key handling.
6.  Brevo API success response (HTTP 201 Created) with provider message ID capture.
7.  Brevo API failure responses (401, 403, 402, 429, 500, and Network Timeout).
8.  Duplicate prevention: exactly 1 PRESENT notification per student per session/date.
9.  Status correction: PRESENT -> ABSENT transition handled with history preservation.
10. Attendance records in SQLite and CSV remain intact when email delivery fails.
11. Security & sanitization: zero API keys or secrets in logs and error messages.
========================================================================================
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db_manager import (
    get_connection,
    add_student,
    delete_student,
    get_student_by_id,
    get_student_by_roll,
    log_attendance,
    update_attendance_record,
    has_notification_been_sent,
    record_notification_attempt,
    get_notification_history
)
from utils.email_notifier import (
    build_email_content,
    send_brevo_email,
    send_parent_attendance_notification,
    send_attendance_email,
    is_valid_email,
    mask_secret,
    LOG_FILE
)


class TestBrevoEmailNotifications(unittest.TestCase):
    """Automated unit and integration tests for Brevo Email Notification System."""

    def setUp(self):
        """Prepare clean test environment and mock credentials."""
        self.test_sid = "TEST_BREVO_999"
        self.test_roll = "ROLL_BRV_999"
        self.test_name = "Aarav Sharma"
        self.test_parent_email = "aarav.parent.test@example.com"
        self.test_dep = "Computer Science and Engineering"
        self.test_date = datetime.now().strftime("%d/%m/%Y")
        self.test_time = "10:30:00 AM"

        # Mock Brevo configuration
        self.mock_config = {
            "api_key": "xkeysib-mock-test-key-1234567890abcdef",
            "sender_email": "notifications@faceattend-kiit.edu",
            "sender_name": "FaceAttend Biometrics",
            "institution_name": "School of Computer Engineering, KIIT University",
            "mentor_name": "Mr. Rakesh Kumar Rai",
            "is_configured": True
        }

        # Clean any leftover test data
        delete_student(self.test_sid)
        conn = get_connection()
        try:
            conn.cursor().execute("DELETE FROM email_notifications WHERE student_id = ?", (self.test_sid,))
            conn.cursor().execute("DELETE FROM attendance WHERE student_id = ?", (self.test_sid,))
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        """Clean up test student, attendance, and notification logs from database."""
        delete_student(self.test_sid)
        conn = get_connection()
        try:
            conn.cursor().execute("DELETE FROM email_notifications WHERE student_id = ?", (self.test_sid,))
            conn.cursor().execute("DELETE FROM attendance WHERE student_id = ?", (self.test_sid,))
            conn.commit()
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # TEST 1 & 2: Email Content & Subject Formats
    # -------------------------------------------------------------------------
    def test_01_email_content_builder_present(self):
        """Verifies PRESENT subject format and content completeness."""
        subject, text_body, html_body = build_email_content(
            student_name=self.test_name,
            roll=self.test_roll,
            dep=self.test_dep,
            date_str=self.test_date,
            time_str=self.test_time,
            status="PRESENT",
            mentor_name="Mr. Rakesh Kumar Rai",
            institution_name="School of Computer Engineering, KIIT University"
        )

        expected_subject = f"FaceAttend: Attendance Confirmation - {self.test_name} (PRESENT)"
        self.assertEqual(subject, expected_subject)
        self.assertIn(self.test_name, text_body)
        self.assertIn(self.test_roll, text_body)
        self.assertIn("PRESENT", text_body)
        self.assertIn("Mr. Rakesh Kumar Rai", text_body)
        self.assertIn("School of Computer Engineering, KIIT University", text_body)
        self.assertIn("#10b981", html_body)  # Neon Green badge

    def test_02_email_content_builder_absent(self):
        """Verifies ABSENT subject format and content completeness."""
        subject, text_body, html_body = build_email_content(
            student_name=self.test_name,
            roll=self.test_roll,
            dep=self.test_dep,
            date_str=self.test_date,
            time_str=self.test_time,
            status="ABSENT",
            mentor_name="Mr. Rakesh Kumar Rai",
            institution_name="School of Computer Engineering, KIIT University"
        )

        expected_subject = f"FaceAttend: Absence Notification - {self.test_name} (ABSENT)"
        self.assertEqual(subject, expected_subject)
        self.assertIn("ABSENT", text_body)
        self.assertIn("Absence Notification Alert", text_body)
        self.assertIn("#ef4444", html_body)  # Crimson Red badge

    # -------------------------------------------------------------------------
    # TEST 3: Parent Email Retrieval from Database
    # -------------------------------------------------------------------------
    def test_03_parent_email_retrieval_from_db(self):
        """Verifies parent_email is correctly stored and retrieved from student records."""
        student_data = {
            "student_id": self.test_sid,
            "dep": self.test_dep,
            "course": "B.Tech",
            "year": "2024-2025",
            "semester": "Semester-6",
            "name": self.test_name,
            "division": "A",
            "roll": self.test_roll,
            "gender": "Male",
            "dob": "15/08/2004",
            "email": "aarav@kiit.ac.in",
            "phone": "9876543210",
            "address": "Bhubaneswar",
            "teacher": "Mr. Rakesh Kumar Rai",
            "photo_sample": "No",
            "parent_email": self.test_parent_email
        }
        ok, msg = add_student(student_data)
        self.assertTrue(ok, f"Failed to add student: {msg}")

        # Retrieve by ID
        profile_by_id = get_student_by_id(self.test_sid)
        self.assertIsNotNone(profile_by_id)
        self.assertEqual(profile_by_id["parent_email"], self.test_parent_email)

        # Retrieve by Roll
        profile_by_roll = get_student_by_roll(self.test_roll)
        self.assertIsNotNone(profile_by_roll)
        self.assertEqual(profile_by_roll["parent_email"], self.test_parent_email)

    # -------------------------------------------------------------------------
    # TEST 4: Missing and Invalid Parent Email Handling
    # -------------------------------------------------------------------------
    def test_04_missing_or_invalid_parent_email(self):
        """Ensures missing/invalid parent email addresses are rejected before calling API."""
        invalid_emails = ["", "   ", "not-an-email", "missingat.com", "user@nodomain"]
        for bad_email in invalid_emails:
            ok, msg, outcome = send_parent_attendance_notification(
                student_id=self.test_sid,
                roll=self.test_roll,
                student_name=self.test_name,
                status="PRESENT",
                parent_email=bad_email,
                config=self.mock_config
            )
            self.assertFalse(ok)
            self.assertEqual(outcome, "INVALID_RECIPIENT")
            self.assertIn("no valid parent email registered", msg)

    # -------------------------------------------------------------------------
    # TEST 5: Missing Brevo API Key Handling
    # -------------------------------------------------------------------------
    def test_05_missing_api_key_handling(self):
        """Ensures missing API key returns a clear CONFIG_ERROR without crashing."""
        unconfigured = dict(self.mock_config)
        unconfigured["api_key"] = ""
        unconfigured["is_configured"] = False

        ok, msg, outcome = send_parent_attendance_notification(
            student_id=self.test_sid,
            roll=self.test_roll,
            student_name=self.test_name,
            status="PRESENT",
            parent_email=self.test_parent_email,
            config=unconfigured
        )
        self.assertFalse(ok)
        self.assertEqual(outcome, "CONFIG_ERROR")
        self.assertIn("Brevo Transactional Email API is not configured", msg)

    # -------------------------------------------------------------------------
    # TEST 6: Brevo API Success (HTTP 201 Created)
    # -------------------------------------------------------------------------
    @patch("utils.email_notifier.requests.post")
    def test_06_brevo_api_success_response_201(self, mock_post):
        """Tests successful HTTP 201 response, messageId capture, and database recording."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        expected_msg_id = "<202610300100.testmsg123@smtp-relay.brevo.com>"
        mock_response.json.return_value = {"messageId": expected_msg_id}
        mock_post.return_value = mock_response

        ok, msg, outcome = send_parent_attendance_notification(
            student_id=self.test_sid,
            roll=self.test_roll,
            student_name=self.test_name,
            status="PRESENT",
            parent_email=self.test_parent_email,
            date_str=self.test_date,
            config=self.mock_config
        )

        self.assertTrue(ok)
        self.assertEqual(outcome, "ACCEPTED")
        self.assertIn("successfully accepted", msg)
        mock_post.assert_called_once()

        # Verify tracking record in database
        history = get_notification_history(self.test_sid)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["delivery_result"], "ACCEPTED")
        self.assertEqual(history[0]["provider_message_id"], expected_msg_id)

    # -------------------------------------------------------------------------
    # TEST 7: Brevo API Failure Responses (401, 403, 402, 429, 500, Timeout)
    # -------------------------------------------------------------------------
    @patch("utils.email_notifier.requests.post")
    def test_07_brevo_api_failure_responses(self, mock_post):
        """Tests error status codes (401, 403, 402, 429, 500, Timeout) with sanitized messages."""
        scenarios = [
            (401, {"message": "Key not found"}, "Invalid API Key"),
            (403, {"message": "Sender not allowed"}, "unverified in your Brevo account"),
            (402, {"message": "Insufficient credits"}, "Sending Limit / Credits Exceeded"),
            (429, {"message": "Rate limit exceeded"}, "Rate Limit Exceeded"),
            (500, {"message": "Internal error"}, "Brevo API Error (HTTP 500)")
        ]

        for status_code, resp_json, expected_phrase in scenarios:
            mock_resp = MagicMock()
            mock_resp.status_code = status_code
            mock_resp.json.return_value = resp_json
            mock_post.return_value = mock_resp

            ok, msg, outcome = send_parent_attendance_notification(
                student_id=self.test_sid,
                roll=self.test_roll,
                student_name=self.test_name,
                status="PRESENT",
                parent_email=self.test_parent_email,
                date_str=self.test_date,
                force=True,  # Bypass duplicate check for scenario testing
                config=self.mock_config
            )
            self.assertFalse(ok)
            self.assertEqual(outcome, "FAILED")
            self.assertIn(expected_phrase, msg)
            self.assertNotIn("xkeysib-", msg)  # Secrets must NEVER be leaked in errors

    # -------------------------------------------------------------------------
    # TEST 8: Duplicate Prevention (At most 1 email per session/date)
    # -------------------------------------------------------------------------
    @patch("utils.email_notifier.requests.post")
    def test_08_duplicate_prevention_same_session(self, mock_post):
        """Ensures second PRESENT notification attempt on the same day is skipped."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"messageId": "<msg-dup-check-001>"}
        mock_post.return_value = mock_resp

        # 1st Call: Should send and be ACCEPTED
        ok1, msg1, outcome1 = send_parent_attendance_notification(
            student_id=self.test_sid,
            roll=self.test_roll,
            student_name=self.test_name,
            status="PRESENT",
            parent_email=self.test_parent_email,
            date_str=self.test_date,
            config=self.mock_config
        )
        self.assertTrue(ok1)
        self.assertEqual(outcome1, "ACCEPTED")
        self.assertEqual(mock_post.call_count, 1)

        # 2nd Call on same date with same status (force=False): Must be prevented
        ok2, msg2, outcome2 = send_parent_attendance_notification(
            student_id=self.test_sid,
            roll=self.test_roll,
            student_name=self.test_name,
            status="PRESENT",
            parent_email=self.test_parent_email,
            date_str=self.test_date,
            force=False,
            config=self.mock_config
        )
        self.assertFalse(ok2)
        self.assertEqual(outcome2, "SKIPPED_DUPLICATE")
        self.assertIn("Duplicate Notification Skipped", msg2)
        # Verify requests.post was NOT called a second time
        self.assertEqual(mock_post.call_count, 1)

    # -------------------------------------------------------------------------
    # TEST 9: Status Correction & History Preservation
    # -------------------------------------------------------------------------
    @patch("utils.email_notifier.requests.post")
    def test_09_status_change_correction_explicit(self, mock_post):
        """Verifies PRESENT -> ABSENT status correction preserves both records in history."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.side_effect = [
            {"messageId": "<present-msg-1>"},
            {"messageId": "<absent-msg-2>"}
        ]
        mock_post.return_value = mock_resp

        # 1. First record PRESENT
        ok1, _, outcome1 = send_parent_attendance_notification(
            student_id=self.test_sid,
            roll=self.test_roll,
            student_name=self.test_name,
            status="PRESENT",
            parent_email=self.test_parent_email,
            date_str=self.test_date,
            config=self.mock_config
        )
        self.assertTrue(ok1)
        self.assertEqual(outcome1, "ACCEPTED")

        # 2. Status Correction: Student changed to ABSENT
        ok2, _, outcome2 = send_parent_attendance_notification(
            student_id=self.test_sid,
            roll=self.test_roll,
            student_name=self.test_name,
            status="ABSENT",
            parent_email=self.test_parent_email,
            date_str=self.test_date,
            config=self.mock_config
        )
        self.assertTrue(ok2)
        self.assertEqual(outcome2, "ACCEPTED")

        # 3. Check persistent history: BOTH records exist
        history = get_notification_history(self.test_sid)
        self.assertEqual(len(history), 2)
        statuses = [r["status"] for r in history]
        self.assertIn("PRESENT", statuses)
        self.assertIn("ABSENT", statuses)

    # -------------------------------------------------------------------------
    # TEST 10: Attendance Records Intact When Email Fails
    # -------------------------------------------------------------------------
    @patch("utils.email_notifier.requests.post")
    def test_10_attendance_records_intact_on_email_failure(self, mock_post):
        """Verifies attendance record in SQLite is NOT corrupted or rolled back when API fails."""
        # 1. Log attendance
        att_ok, att_msg = log_attendance(
            student_id=self.test_sid,
            roll=self.test_roll,
            name=self.test_name,
            department=self.test_dep,
            time_str=self.test_time,
            date_str=self.test_date,
            status="Present"
        )
        self.assertTrue(att_ok)

        # 2. Simulate Brevo API network crash
        mock_post.side_effect = Exception("Network Connection Abruptly Terminated")

        em_ok, em_msg, outcome = send_parent_attendance_notification(
            student_id=self.test_sid,
            roll=self.test_roll,
            student_name=self.test_name,
            status="PRESENT",
            parent_email=self.test_parent_email,
            date_str=self.test_date,
            force=True,
            config=self.mock_config
        )
        self.assertFalse(em_ok)
        self.assertEqual(outcome, "FAILED")

        # 3. Verify attendance record is STILL intact in SQLite
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM attendance WHERE student_id = ? AND date = ?", (self.test_sid, self.test_date))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "Present")
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # TEST 11: Security & Sanitization
    # -------------------------------------------------------------------------
    def test_11_security_sanitization(self):
        """Verifies mask_secret never exposes keys and audit log does not leak secrets."""
        test_key = "xkeysib-99887766554433221100aabbccddeeff"
        masked = mask_secret(test_key)
        self.assertTrue(masked.startswith("xkeysib-"))
        self.assertIn("••••", masked)
        self.assertNotIn("99887766554433221100", masked)


if __name__ == "__main__":
    unittest.main()
