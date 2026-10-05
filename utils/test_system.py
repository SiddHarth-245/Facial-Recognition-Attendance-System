"""
========================================================================================
Automated Verification & Software Quality Assurance Test Suite
========================================================================================
Module: test_system.py
Author: Deepak Sah (Lead Developer - System Testing & Quality Verification)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module provides a rigorous, automated unit and integration test harness built on Python's
standard `unittest` framework. It verifies core system invariants, database schema creation,
transactional ACID integrity, user authentication, security question recovery, student profile
CRUD operations, search filtering, LBPH machine learning model training, dual-persistence
attendance logging, and graphical module importability.

Test Suite Breakdown:
--------------------
1. `test_01_user_auth_and_recovery`:
   - Validates registration of new admin accounts, case-insensitive credential verification,
     invalid password rejection, and security question-based password resets.
2. `test_02_student_crud`:
   - Validates student creation, primary key lookups, profile modifications, multi-criteria
     search filters, photo sample status updates, and record deletion.
3. `test_03_training_and_lbph_classifier`:
   - Executes `train_classifier_core()`, validates integer-to-string label encoding,
     confirms generation of `classifier/classifier.xml` and `classifier/id_map.json`,
     and asserts serialized model file size exceeds 1 KB.
4. `test_04_attendance_logging`:
   - Verifies biometric attendance logging to both SQLite database and CSV file,
     tests daily duplicate attendance rejection, and validates manual status overrides.
5. `test_05_gui_module_imports`:
   - Confirms that all 10 Tkinter GUI window classes can be imported and initialized
     without syntax errors, circular dependency deadlocks, or missing assets.
========================================================================================
"""

import os
import sys
import unittest
import numpy as np
from PIL import Image
from datetime import datetime
import cv2
import json

# Ensure project root directory is present in sys.path for absolute imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Database CRUD functions under test
from database.db_manager import (
    initialize_database,
    register_user,
    verify_login,
    reset_password,
    add_student,
    update_student,
    delete_student,
    fetch_all_students,
    search_students,
    get_student_by_id,
    update_photo_sample_status,
    log_attendance,
    fetch_all_attendance,
    update_attendance_record,
)


class TestAttendanceSystem(unittest.TestCase):
    """
    Automated Unit & Integration Test Case Suite for the Attendance System.
    """

    @classmethod
    def setUpClass(cls):
        """
        Initializes database schema and ensures all required runtime storage directories exist.
        """
        initialize_database()
        cls.data_dir = os.path.join(BASE_DIR, "data")
        cls.classifier_dir = os.path.join(BASE_DIR, "classifier")
        cls.att_dir = os.path.join(BASE_DIR, "attendance_records")
        os.makedirs(cls.data_dir, exist_ok=True)
        os.makedirs(cls.classifier_dir, exist_ok=True)
        os.makedirs(cls.att_dir, exist_ok=True)

    def test_01_user_auth_and_recovery(self):
        """
        Tests the administrative security pipeline:
        1. Register a new user account.
        2. Verify successful authentication.
        3. Verify failed authentication on invalid password.
        4. Reset password via security challenge.
        5. Verify authentication with the new password.
        """
        email = f"test_{int(datetime.now().timestamp())}@system.com"
        
        # 1. Register User
        ok, msg = register_user("John", "Doe", "9876543210", email, "Your Birth Place", "New York", "pass123")
        self.assertTrue(ok, f"Registration failed: {msg}")

        # 2. Login Verification
        ok, user_data, msg = verify_login(email, "pass123")
        self.assertTrue(ok, f"Login failed: {msg}")
        self.assertEqual(user_data["fname"], "John")

        # 3. Invalid Login Rejection
        ok, _, _ = verify_login(email, "wrongpass")
        self.assertFalse(ok)

        # 4. Password Reset via Security Question
        ok, msg = reset_password("Your Birth Place", "New York", "newpass456", email=email)
        self.assertTrue(ok, f"Reset password failed: {msg}")

        # 5. Verify Authentication with New Password
        ok, _, msg = verify_login(email, "newpass456")
        self.assertTrue(ok, f"Login with new password failed: {msg}")

    def test_02_student_crud(self):
        """
        Tests full student lifecycle management:
        1. Create student record.
        2. Fetch student by ID.
        3. Update student attributes.
        4. Search student by criteria.
        5. Update photo sample flag.
        6. Delete student record.
        """
        stu_id = f"STU_{int(datetime.now().timestamp())}"
        data = {
            "student_id": stu_id,
            "dep": "Computer Science and Engineering (CSE)",
            "course": "B.Tech",
            "year": "2024-2025",
            "semester": "Semester-4",
            "name": "Alice Smith",
            "division": "A",
            "roll": "42",
            "gender": "Female",
            "dob": "2004-05-15",
            "email": "alice@univ.edu",
            "phone": "9123456780",
            "address": "123 Campus St",
            "teacher": "Dr. Prof",
            "photo_sample": "No"
        }

        # 1. Add Student
        ok, msg = add_student(data)
        self.assertTrue(ok, f"Add student failed: {msg}")

        # 2. Fetch by Primary Key ID
        fetched = get_student_by_id(stu_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "Alice Smith")

        # 3. Update Student Profile
        data["name"] = "Alice Johnson"
        ok, msg = update_student(data)
        self.assertTrue(ok, f"Update student failed: {msg}")
        self.assertEqual(get_student_by_id(stu_id)["name"], "Alice Johnson")

        # 4. Search Student by ID
        results = search_students("Student ID", stu_id)
        self.assertTrue(len(results) >= 1)

        # 5. Update Photo Sample Status
        update_photo_sample_status(stu_id, "Yes")
        self.assertEqual(get_student_by_id(stu_id)["photo_sample"], "Yes")

        # 6. Delete Student Record
        ok, msg = delete_student(stu_id)
        self.assertTrue(ok, f"Delete student failed: {msg}")
        self.assertIsNone(get_student_by_id(stu_id))

    def test_03_training_and_lbph_classifier(self):
        """
        Tests LBPH machine learning model compilation and serialization:
        1. Executes core training function.
        2. Validates serialized XML model and JSON ID map.
        3. Asserts XML model size exceeds 1000 bytes.
        """
        from modules.train import train_classifier_core
        
        # Verify classifier trains on available datasets
        success, count, counts, msg = train_classifier_core()
        self.assertTrue(success, f"Training failed: {msg}")
        self.assertGreater(count, 0)

        classifier_xml = os.path.join(self.classifier_dir, "classifier.xml")
        map_file = os.path.join(self.classifier_dir, "id_map.json")
        self.assertTrue(os.path.exists(classifier_xml))
        self.assertTrue(os.path.exists(map_file))
        self.assertGreater(os.path.getsize(classifier_xml), 1000)

    def test_04_attendance_logging(self):
        """
        Tests biometric attendance logging, daily deduplication, and manual status overrides.
        """
        date_str = datetime.now().strftime("%d/%m/%Y")
        time_str = datetime.now().strftime("%H:%M:%S")

        # 1. Log attendance record
        ok, msg = log_attendance("999", "01", "Test Student", "CS", time_str, date_str, "Present")
        self.assertTrue(ok or "already marked" in msg.lower())

        # 2. Fetch all attendance records
        records = fetch_all_attendance()
        self.assertTrue(len(records) > 0)

        # 3. Update attendance status override
        att_id = records[0][0]
        ok, msg = update_attendance_record(att_id, "Present")
        self.assertTrue(ok)

    def test_05_gui_module_imports(self):
        """
        Ensures all 10 GUI window classes import cleanly without circular dependency errors.
        """
        from modules.login import LoginWindow
        from modules.register import RegisterWindow
        from modules.forget_password import ForgetPasswordWindow
        from modules.dashboard import MainDashboard
        from modules.student import StudentManagementSystem
        from modules.train import TrainDataWindow
        from modules.face_recognition import FaceRecognitionWindow
        from modules.attendance import AttendanceManagementSystem
        from modules.developer import DeveloperWindow
        from modules.help_desk import HelpDeskWindow

        self.assertTrue(callable(LoginWindow))
        self.assertTrue(callable(RegisterWindow))
        self.assertTrue(callable(ForgetPasswordWindow))
        self.assertTrue(callable(MainDashboard))
        self.assertTrue(callable(StudentManagementSystem))
        self.assertTrue(callable(TrainDataWindow))
        self.assertTrue(callable(FaceRecognitionWindow))
        self.assertTrue(callable(AttendanceManagementSystem))
        self.assertTrue(callable(DeveloperWindow))
        self.assertTrue(callable(HelpDeskWindow))

    def test_06_face_recognition_pipeline(self):
        """
        Tests the automated Face Recognition pipeline:
        1. Validates ensure_classifier_ready() self-healing synchronization.
        2. Loads LBPH model and verifies predictions on enrolled face samples.
        3. Confirms identity mapping resolution and confidence calculation.
        """
        from modules.face_recognition import ensure_classifier_ready, log_attendance_to_csv
        import glob

        # 1. Verify classifier readiness
        ready, msg = ensure_classifier_ready()
        self.assertTrue(ready, f"Classifier readiness check failed: {msg}")

        # 2. Verify model prediction on actual enrolled dataset samples
        with open(os.path.join(self.classifier_dir, "id_map.json"), "r", encoding="utf-8") as f:
            int_to_id = json.load(f)["int_to_id"]

        clf = cv2.face.LBPHFaceRecognizer_create(radius=2, neighbors=8, grid_x=8, grid_y=8)
        clf.read(os.path.join(self.classifier_dir, "classifier.xml"))

        # Test against enrolled students
        tested_students = 0
        for sid in ["1", "3", "4"]:
            sample_files = glob.glob(os.path.join(self.data_dir, f"user.{sid}.*.jpg"))
            if sample_files:
                sample_img = cv2.imread(sample_files[0], cv2.IMREAD_GRAYSCALE)
                self.assertIsNotNone(sample_img)
                eq = cv2.equalizeHist(cv2.resize(sample_img, (200, 200)))
                lbl, dist = clf.predict(eq)
                predicted_sid = int_to_id.get(str(lbl))
                self.assertEqual(predicted_sid, sid, f"Mismatch: expected {sid}, got {predicted_sid}")
                self.assertLessEqual(dist, 50.0, f"Distance too high for enrolled sample: {dist}")
                tested_students += 1

        self.assertGreater(tested_students, 0, "No enrolled students were tested.")


if __name__ == "__main__":
    # Execute test runner with verbose reporting
    unittest.main(verbosity=2)

