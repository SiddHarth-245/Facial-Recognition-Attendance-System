"""
========================================================================================
Automated Verification Suite: Interactive Facial Liveness & Anti-Spoofing Engine
FaceAttend Cyber-Blue Ultra Security Architecture
========================================================================================
Test Module: utils/test_liveness_detection.py
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Coverage Scope:
----------------
1. Randomized multi-action challenge generation and diversity.
2. Geometric and textural pose/feature extraction.
3. Directional head turn detection (Turn Left, Turn Right, Look Up, Return Center).
4. Eye blink state machine (Open -> Closed -> Open vs. static photo rejection).
5. Successful end-to-end multi-step challenge verification.
6. Challenge expiration and step timeout enforcement (fail-closed).
7. Face-tracker continuity protection (track_id swap detection and abort).
8. Strict fail-closed attendance guarantees (never write DB or CSV on failed liveness).
9. Database-level deduplication and CSV mirror synchronization (no CSV on DB rejection).

All database and filesystem operations run in isolated temporary sandbox paths
to preserve production data and existing student records intact.
========================================================================================
"""

import sys
import os
import unittest
import tempfile
import shutil
import sqlite3
import csv
import time
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.liveness_detector import (
    LivenessAction,
    LivenessChallengeSession,
    FacePoseAnalyzer,
    generate_random_challenge,
    CHALLENGE_PRESETS,
    ACTION_TITLES,
    ACTION_INSTRUCTIONS
)


class TestLivenessDetectionAndAntiSpoofing(unittest.TestCase):
    """Unit and integration test cases for interactive anti-spoofing challenge verification."""

    def setUp(self):
        """Creates an isolated temporary sandbox environment for each test."""
        self.test_dir = tempfile.mkdtemp(prefix="faceattend_liveness_test_")
        self.test_db_path = os.path.join(self.test_dir, "test_attendance.db")
        self.test_csv_path = os.path.join(self.test_dir, "test_attendance.csv")

        # Initialize minimal SQLite schema for isolated attendance testing
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE attendance (
                attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                roll TEXT NOT NULL,
                name TEXT NOT NULL,
                department TEXT,
                time TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL
            );
        """)
        cur.execute("""
            CREATE UNIQUE INDEX idx_attendance_student_date 
            ON attendance(student_id, date);
        """)
        conn.commit()
        conn.close()

    def tearDown(self):
        """Cleans up the temporary sandbox directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_synthetic_face(self, cx_offset: float = 0.0, cy_offset: float = 0.0,
                               eyes_open: bool = True) -> np.ndarray:
        """
        Synthesizes a 200x200 face image with configurable feature offsets and eye states.
        """
        img = np.full((200, 200), 140, dtype=np.uint8)

        # Central nose/mouth features
        base_cx = int(100 + cx_offset * 100)
        base_cy = int(100 + cy_offset * 100)
        img[max(0, base_cy - 10):min(200, base_cy + 25),
            max(0, base_cx - 15):min(200, base_cx + 15)] = 50

        # Eye regions: y in [44, 96], left x in [28, 92], right x in [108, 172]
        if eyes_open:
            # High-contrast texture representing dark pupil and white sclera
            img[50:80, 40:80] = np.random.randint(20, 220, (30, 40), dtype=np.uint8)
            img[50:80, 120:160] = np.random.randint(20, 220, (30, 40), dtype=np.uint8)
        else:
            # Uniform smooth eyelid skin (low variance, low gradient)
            img[50:80, 40:80] = 140
            img[50:80, 120:160] = 140

        return img

    # -------------------------------------------------------------------------
    # TEST 1: Randomized Challenge Generation & Diversity
    # -------------------------------------------------------------------------
    def test_01_randomized_challenge_generation(self):
        """Verifies that challenge generation produces diverse, valid multi-action sequences."""
        challenges = [tuple(generate_random_challenge()) for _ in range(50)]
        unique_challenges = set(challenges)

        # Ensure all generated challenges are members of approved presets
        preset_set = set(CHALLENGE_PRESETS)
        for ch in unique_challenges:
            self.assertIn(ch, preset_set, f"Unexpected challenge sequence: {ch}")

        # Ensure randomization covers multiple distinct patterns
        self.assertGreater(len(unique_challenges), 2, "Challenge generator lacks sufficient variety.")
        for ch in challenges:
            self.assertEqual(len(ch), 2, "Challenge should contain exactly 2 actions.")
            self.assertNotEqual(ch[0], ch[1], "Consecutive actions in a challenge must be distinct.")

    # -------------------------------------------------------------------------
    # TEST 2: Geometric & Textural Feature Extraction
    # -------------------------------------------------------------------------
    def test_02_face_pose_feature_extraction(self):
        """Verifies structure and bounds of extracted face features."""
        face = self._create_synthetic_face(eyes_open=True)
        bbox = (100, 120, 160, 160)
        feats = FacePoseAnalyzer.extract_features(face, bbox, frame_w=640, frame_h=480, timestamp=10.0)

        required_keys = {"box_cx", "box_cy", "bw", "bh", "aspect", "cx_feat", "cy_feat", "eye_openness", "timestamp"}
        self.assertTrue(required_keys.issubset(feats.keys()), "Missing expected feature keys.")

        self.assertAlmostEqual(feats["aspect"], 1.0, delta=0.01)
        self.assertGreater(feats["eye_openness"], 0.0)
        self.assertEqual(feats["timestamp"], 10.0)

    # -------------------------------------------------------------------------
    # TEST 3: Head Turn Actions (Yaw, Pitch, Center)
    # -------------------------------------------------------------------------
    def test_03_head_turn_actions(self):
        """Verifies detection of Turn Left, Turn Right, Look Up, and Return Center."""
        session = LivenessChallengeSession(step_timeout=5.0, total_timeout=10.0)
        session.start(track_id=1, student_id="ST101", student_name="Alice", challenge=[LivenessAction.TURN_LEFT, LivenessAction.RETURN_CENTER])

        neutral_face = self._create_synthetic_face(cx_offset=0.0, cy_offset=0.0)
        t = 100.0

        # Feed baseline frames
        for _ in range(3):
            session.update(neutral_face, (100, 100, 150, 150), current_track_id=1, frame_w=640, frame_h=480, now=t)
            t += 0.05
        self.assertEqual(session.state, LivenessChallengeSession.STATE_IN_PROGRESS)

        # Turn Left (face shifts rightwards in unmirrored frame coordinates)
        turned_face = self._create_synthetic_face(cx_offset=0.15, cy_offset=0.0)
        for _ in range(3):
            session.update(turned_face, (135, 100, 150, 150), current_track_id=1, frame_w=640, frame_h=480, now=t)
            t += 0.05

        self.assertEqual(session.current_step, 1, "Turn Left action was not recognized.")

        # Return to Center
        for _ in range(3):
            session.update(neutral_face, (100, 100, 150, 150), current_track_id=1, frame_w=640, frame_h=480, now=t)
            t += 0.05

        self.assertEqual(session.state, LivenessChallengeSession.STATE_PASSED)
        self.assertTrue(session.is_passed())

    # -------------------------------------------------------------------------
    # TEST 4: Eye Blink Detection vs. Static Photo Rejection
    # -------------------------------------------------------------------------
    def test_04_eye_blink_detection(self):
        """Verifies that an open -> closed -> open sequence registers a blink, while a static image fails."""
        session = LivenessChallengeSession(step_timeout=5.0, total_timeout=10.0)
        session.start(track_id=1, student_id="ST101", student_name="Bob", challenge=[LivenessAction.BLINK, LivenessAction.TURN_RIGHT])

        open_face = self._create_synthetic_face(eyes_open=True)
        closed_face = self._create_synthetic_face(eyes_open=False)
        t = 100.0

        # Baseline
        for _ in range(3):
            session.update(open_face, (100, 100, 150, 150), current_track_id=1, frame_w=640, frame_h=480, now=t)
            t += 0.05

        # Eyes close (duration ~ 0.25s)
        session.update(closed_face, (100, 100, 150, 150), current_track_id=1, frame_w=640, frame_h=480, now=t)
        t += 0.15
        session.update(closed_face, (100, 100, 150, 150), current_track_id=1, frame_w=640, frame_h=480, now=t)
        t += 0.10

        # Eyes reopen
        for _ in range(3):
            session.update(open_face, (100, 100, 150, 150), current_track_id=1, frame_w=640, frame_h=480, now=t)
            t += 0.05

        self.assertEqual(session.current_step, 1, "Blink was not recognized.")

        # Static Photo Rejection Test: A static open face held without blinking should time out
        static_session = LivenessChallengeSession(step_timeout=1.5, total_timeout=3.0)
        static_session.start(track_id=2, student_id="ST102", student_name="Static", challenge=[LivenessAction.BLINK, LivenessAction.TURN_RIGHT])

        t_stat = 200.0
        for _ in range(3):
            static_session.update(open_face, (100, 100, 150, 150), current_track_id=2, frame_w=640, frame_h=480, now=t_stat)
            t_stat += 0.05

        # Hold static photo without blinking past timeout
        t_stat += 2.0
        static_session.update(open_face, (100, 100, 150, 150), current_track_id=2, frame_w=640, frame_h=480, now=t_stat)
        self.assertTrue(static_session.is_failed(), "Static photo without blinking was not rejected.")
        self.assertFalse(static_session.is_passed())

    # -------------------------------------------------------------------------
    # TEST 5: Successful Multi-Step Challenge End-to-End
    # -------------------------------------------------------------------------
    def test_05_successful_challenge_end_to_end(self):
        """Verifies end-to-end flow from baseline calibration through all challenge steps."""
        session = LivenessChallengeSession(step_timeout=5.0, total_timeout=10.0)
        session.start(track_id=7, student_id="ST777", student_name="Deepak", challenge=[LivenessAction.TURN_RIGHT, LivenessAction.BLINK])

        face_open = self._create_synthetic_face(cx_offset=0.0, eyes_open=True)
        face_right = self._create_synthetic_face(cx_offset=-0.15, eyes_open=True)
        face_closed = self._create_synthetic_face(cx_offset=-0.15, eyes_open=False)
        t = 10.0

        # 1. Baseline
        for _ in range(3):
            session.update(face_open, (100, 100, 150, 150), current_track_id=7, frame_w=640, frame_h=480, now=t)
            t += 0.05

        # 2. Turn Right
        for _ in range(3):
            session.update(face_right, (65, 100, 150, 150), current_track_id=7, frame_w=640, frame_h=480, now=t)
            t += 0.05
        self.assertEqual(session.current_step, 1)

        # 3. Blink
        session.update(face_closed, (65, 100, 150, 150), current_track_id=7, frame_w=640, frame_h=480, now=t)
        t += 0.20
        session.update(face_closed, (65, 100, 150, 150), current_track_id=7, frame_w=640, frame_h=480, now=t)
        t += 0.10
        for _ in range(3):
            session.update(face_right, (65, 100, 150, 150), current_track_id=7, frame_w=640, frame_h=480, now=t)
            t += 0.05

        self.assertTrue(session.is_passed())
        self.assertEqual(session.state, LivenessChallengeSession.STATE_PASSED)

    # -------------------------------------------------------------------------
    # TEST 6: Step Timeout & Expiration Enforcement
    # -------------------------------------------------------------------------
    def test_06_challenge_timeout_expired(self):
        """Verifies that an inactive or sluggish face triggers EXPIRED state."""
        session = LivenessChallengeSession(step_timeout=2.0, total_timeout=4.0)
        session.start(track_id=1, student_id="ST101", student_name="Test", challenge=[LivenessAction.LOOK_UP, LivenessAction.RETURN_CENTER])

        face = self._create_synthetic_face()
        t = 0.0
        for _ in range(3):
            session.update(face, (100, 100, 150, 150), current_track_id=1, frame_w=640, frame_h=480, now=t)
            t += 0.05

        # Advance time beyond step timeout
        t += 2.5
        passed, msg = session.update(face, (100, 100, 150, 150), current_track_id=1, frame_w=640, frame_h=480, now=t)

        self.assertFalse(passed)
        self.assertTrue(session.is_failed())
        self.assertEqual(session.state, LivenessChallengeSession.STATE_EXPIRED)

    # -------------------------------------------------------------------------
    # TEST 7: Face Tracker Swap Abort
    # -------------------------------------------------------------------------
    def test_07_face_tracker_change_abort(self):
        """Verifies that if the face tracker ID changes during challenge, the session fails closed immediately."""
        session = LivenessChallengeSession(step_timeout=5.0, total_timeout=10.0)
        session.start(track_id=1, student_id="ST101", student_name="Alice")

        face = self._create_synthetic_face()
        session.update(face, (100, 100, 150, 150), current_track_id=1, frame_w=640, frame_h=480, now=1.0)

        # Incoming frame with a DIFFERENT track_id (e.g. face substituted or tracker dropped)
        passed, msg = session.update(face, (100, 100, 150, 150), current_track_id=2, frame_w=640, frame_h=480, now=1.1)

        self.assertFalse(passed)
        self.assertTrue(session.is_failed())
        self.assertEqual(session.state, LivenessChallengeSession.STATE_FAILED)
        self.assertIn("tracker", session.error_reason.lower())

    # -------------------------------------------------------------------------
    # TEST 8: Strict Fail-Closed Attendance Guarantee
    # -------------------------------------------------------------------------
    def test_08_fail_closed_attendance_guarantee(self):
        """
        Guarantees that attendance is NEVER recorded in SQLite or CSV when liveness
        is incomplete, failed, expired, or aborted.
        """
        def record_mock_attendance(liveness_session: LivenessChallengeSession, sid: str, roll: str, name: str,
                                   dep: str, date_str: str, time_str: str) -> bool:
            # Replicates the attendance gate condition in modules/face_recognition.py
            if not liveness_session.is_passed():
                # Fail closed: Do NOT record in DB or CSV
                return False

            conn = sqlite3.connect(self.test_db_path)
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO attendance (student_id, roll, name, department, time, date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (sid, roll, name, dep, time_str, date_str, "Present"))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                return False
            conn.close()

            # Mirror to CSV only if DB write succeeded
            with open(self.test_csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([1, roll, name, dep, time_str, date_str, "Present"])
            return True

        # Case A: Challenge in progress (not yet passed)
        sess_in_prog = LivenessChallengeSession()
        sess_in_prog.start(track_id=1, student_id="ST01", student_name="Alice")
        res = record_mock_attendance(sess_in_prog, "ST01", "R01", "Alice", "CSE", "03/11/2026", "10:00:00 AM")
        self.assertFalse(res, "Attendance was incorrectly recorded during active in-progress challenge!")

        # Case B: Challenge failed / timed out
        sess_failed = LivenessChallengeSession()
        sess_failed.abort("Challenge timeout")
        res = record_mock_attendance(sess_failed, "ST01", "R01", "Alice", "CSE", "03/11/2026", "10:00:00 AM")
        self.assertFalse(res, "Attendance was incorrectly recorded after failed liveness challenge!")

        # Case C: Tracker swapped
        sess_swapped = LivenessChallengeSession()
        sess_swapped.start(track_id=1, student_id="ST01", student_name="Alice")
        sess_swapped.update(self._create_synthetic_face(), (100, 100, 150, 150), current_track_id=99, frame_w=640, frame_h=480)
        res = record_mock_attendance(sess_swapped, "ST01", "R01", "Alice", "CSE", "03/11/2026", "10:00:00 AM")
        self.assertFalse(res, "Attendance was incorrectly recorded after tracker change!")

        # Verify database and CSV remain completely empty
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM attendance")
        count = cur.fetchone()[0]
        conn.close()
        self.assertEqual(count, 0, "Database should contain 0 records when liveness fails.")
        self.assertFalse(os.path.exists(self.test_csv_path), "CSV file should not exist when liveness fails.")

    # -------------------------------------------------------------------------
    # TEST 9: Database Deduplication & CSV Mirror Synchronization
    # -------------------------------------------------------------------------
    def test_09_database_deduplication_and_csv_sync(self):
        """
        Verifies that a student can only be marked once per day and that CSV writes
        never occur when the database attendance insert fails or rejects a duplicate.
        """
        sess_passed = LivenessChallengeSession()
        sess_passed.state = LivenessChallengeSession.STATE_PASSED

        def log_isolated_attendance(sid: str, roll: str, name: str, dep: str, date_str: str, time_str: str) -> bool:
            if not sess_passed.is_passed():
                return False

            conn = sqlite3.connect(self.test_db_path)
            try:
                cur = conn.cursor()
                # Deduplication check
                cur.execute("SELECT attendance_id FROM attendance WHERE student_id = ? AND date = ?", (sid, date_str))
                if cur.fetchone():
                    conn.close()
                    return False

                cur.execute("""
                    INSERT INTO attendance (student_id, roll, name, department, time, date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (sid, roll, name, dep, time_str, date_str, "Present"))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                return False
            conn.close()

            # Mirror to CSV ONLY on DB success
            with open(self.test_csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([1, roll, name, dep, time_str, date_str, "Present"])
            return True

        # First mark: Should succeed
        ok1 = log_isolated_attendance("ST01", "R01", "Alice", "CSE", "03/11/2026", "09:30:00 AM")
        self.assertTrue(ok1, "First attendance mark should succeed.")

        # Second mark on SAME date: Should be rejected by database deduplication
        ok2 = log_isolated_attendance("ST01", "R01", "Alice", "CSE", "03/11/2026", "09:35:00 AM")
        self.assertFalse(ok2, "Second attendance mark on same date must be rejected.")

        # Check SQLite row count: Exactly 1
        conn = sqlite3.connect(self.test_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM attendance WHERE student_id = 'ST01' AND date = '03/11/2026'")
        db_count = cur.fetchone()[0]
        conn.close()
        self.assertEqual(db_count, 1, "Database should contain exactly 1 attendance row for student on date.")

        # Check CSV line count: Exactly 1 line
        with open(self.test_csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1, "CSV file must contain exactly 1 entry; no phantom rows when DB rejects.")


if __name__ == "__main__":
    unittest.main()
