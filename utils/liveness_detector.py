"""
========================================================================================
Interactive Facial Liveness & Anti-Spoofing Challenge Engine
FaceAttend Cyber-Blue Ultra Security Architecture
========================================================================================
Module: utils/liveness_detector.py
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module provides an interactive, randomized active-liveness challenge pipeline
to mitigate presentation attacks (e.g., printed photographs, static portrait images,
or looped/prerecorded video clips presented to the webcam).

Operational Flow & Security Constraints:
----------------------------------------
1. Randomized Multi-Action Challenge:
   - When a student's face is detected and initially identified by LBPH, the system
     generates a fresh, randomized sequence of distinct behavioral actions
     (e.g., 'turn_left -> blink', 'blink -> turn_right', 'look_up -> return_center').
   - Randomized sequences prevent simple prerecorded replay attacks from passing.

2. Face-Tracking Continuity:
   - The challenge is strictly bound to the SpatialFaceTracker track_id.
   - If the face is lost, occluded, or swapped with another face/tracker during the
     challenge, the session immediately terminates and fails closed.

3. Strict Fail-Closed Policy:
   - If a challenge fails, expires, or detection becomes uncertain, attendance is
     NEVER recorded in SQLite or CSV.
   - The system displays clear diagnostic feedback and allows a retry or manual
     instructor review.

4. 2D Sensor Disclaimer:
   - This software-only active challenge reduces trivial photo/replay spoofing on standard
     2D webcams, but cannot guarantee prevention against sophisticated deepfakes, 3D masks,
     or live interactive video injection. Depth/IR hardware or human oversight is
     recommended for high-security environments.
========================================================================================
"""

import time
import random
from collections import deque
from typing import Dict, List, Tuple, Optional, Any
import cv2
import numpy as np


class LivenessAction:
    """Supported interactive challenge action primitives."""
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    LOOK_UP = "look_up"
    RETURN_CENTER = "return_center"
    BLINK = "blink"


ACTION_TITLES: Dict[str, str] = {
    LivenessAction.TURN_LEFT: "Turn Head Left",
    LivenessAction.TURN_RIGHT: "Turn Head Right",
    LivenessAction.LOOK_UP: "Look / Tilt Up",
    LivenessAction.RETURN_CENTER: "Return to Center",
    LivenessAction.BLINK: "Blink Both Eyes",
}

ACTION_ICONS: Dict[str, str] = {
    LivenessAction.TURN_LEFT: "⮜",
    LivenessAction.TURN_RIGHT: "⮞",
    LivenessAction.LOOK_UP: "⮝",
    LivenessAction.RETURN_CENTER: "⊙",
    LivenessAction.BLINK: "👁",
}

ACTION_INSTRUCTIONS: Dict[str, str] = {
    LivenessAction.TURN_LEFT: "Please slowly turn your head to your LEFT",
    LivenessAction.TURN_RIGHT: "Please slowly turn your head to your RIGHT",
    LivenessAction.LOOK_UP: "Please tilt your head / look slightly UP",
    LivenessAction.RETURN_CENTER: "Please face forward directly at the camera",
    LivenessAction.BLINK: "Please clearly blink both of your eyes",
}

# Permitted challenge presets (each sequence is a coherent 2-action chain)
CHALLENGE_PRESETS: List[Tuple[str, str]] = [
    (LivenessAction.TURN_LEFT, LivenessAction.BLINK),
    (LivenessAction.BLINK, LivenessAction.TURN_RIGHT),
    (LivenessAction.LOOK_UP, LivenessAction.RETURN_CENTER),
    (LivenessAction.TURN_RIGHT, LivenessAction.BLINK),
    (LivenessAction.TURN_LEFT, LivenessAction.RETURN_CENTER),
    (LivenessAction.BLINK, LivenessAction.LOOK_UP),
    (LivenessAction.TURN_RIGHT, LivenessAction.RETURN_CENTER),
    (LivenessAction.LOOK_UP, LivenessAction.BLINK),
]


def generate_random_challenge() -> List[str]:
    """Returns a fresh randomized 2-action challenge sequence."""
    choice = random.choice(CHALLENGE_PRESETS)
    return list(choice)


class FacePoseAnalyzer:
    """
    Computes normalized head pose indicators, eye openness, and facial motion metrics
    from real-time grayscale crops and bounding boxes.
    """

    @staticmethod
    def extract_features(face_gray: np.ndarray, bbox: Tuple[int, int, int, int], 
                         frame_w: int, frame_h: int, timestamp: Optional[float] = None) -> Dict[str, Any]:
        """
        Extracts structural geometric and textural features from a face crop.

        Parameters:
        -----------
        face_gray : np.ndarray
            Cropped grayscale face image (e.g. 200x200).
        bbox : Tuple[int, int, int, int]
            Bounding box coordinates (x, y, w, h) in original video frame.
        frame_w, frame_h : int
            Full frame dimensions.
        timestamp : float, optional
            Timestamp of the frame.
        """
        if timestamp is None:
            timestamp = time.time()

        bx, by, bw, bh = bbox
        h, w = face_gray.shape[:2]

        # 1. Normalized bounding box coordinates in frame
        box_cx_rel = (bx + bw / 2.0) / max(1, frame_w)
        box_cy_rel = (by + bh / 2.0) / max(1, frame_h)
        aspect = bw / float(max(1, bh))

        # 2. Internal Facial Feature Centroids (Nose & Eye Structure)
        # Central band: y from 25% to 75%
        band = face_gray[int(h * 0.25):int(h * 0.75), :]
        bh_band, bw_band = band.shape[:2]

        # Invert intensity so dark features (pupils, nostrils, mouth) exert high gravitational pull
        weights = 255.0 - band.astype(np.float32)
        weights = np.clip(weights - np.mean(weights), 0, 255)

        col_weights = np.sum(weights, axis=0)
        tot_col = np.sum(col_weights) + 1e-6
        cx_feat = np.sum(np.arange(bw_band) * col_weights) / (tot_col * bw_band)

        row_weights = np.sum(weights, axis=1)
        tot_row = np.sum(row_weights) + 1e-6
        cy_feat = np.sum(np.arange(bh_band) * row_weights) / (tot_row * bh_band)

        # 3. Eye Openness Metric (Standard Deviation + Vertical Edge Energy)
        # Left eye: y in [0.22, 0.48], x in [0.14, 0.46]
        # Right eye: y in [0.22, 0.48], x in [0.54, 0.86]
        l_roi = face_gray[int(h * 0.22):int(h * 0.48), int(w * 0.14):int(w * 0.46)]
        r_roi = face_gray[int(h * 0.22):int(h * 0.48), int(w * 0.54):int(w * 0.86)]

        if l_roi.size > 0 and r_roi.size > 0:
            l_std = float(np.std(l_roi))
            r_std = float(np.std(r_roi))
            l_edge = float(np.mean(np.abs(np.diff(l_roi.astype(np.float32), axis=0))))
            r_edge = float(np.mean(np.abs(np.diff(r_roi.astype(np.float32), axis=0))))
            eye_openness = 0.5 * (l_std + r_std) + 0.5 * (l_edge + r_edge)
        else:
            eye_openness = 50.0

        return {
            "timestamp": timestamp,
            "box_cx": box_cx_rel,
            "box_cy": box_cy_rel,
            "bw": bw,
            "bh": bh,
            "aspect": aspect,
            "cx_feat": cx_feat,
            "cy_feat": cy_feat,
            "eye_openness": eye_openness,
        }


class LivenessChallengeSession:
    """
    State machine controller for an active liveness verification session
    bound to a specific tracked face.
    """

    STATE_IDLE = "IDLE"
    STATE_COLLECTING_BASELINE = "COLLECTING_BASELINE"
    STATE_IN_PROGRESS = "IN_PROGRESS"
    STATE_PASSED = "PASSED"
    STATE_FAILED = "FAILED"
    STATE_EXPIRED = "EXPIRED"

    def __init__(self, step_timeout: float = 4.0, total_timeout: float = 8.5):
        self.step_timeout = step_timeout
        self.total_timeout = total_timeout

        self.state = self.STATE_IDLE
        self.track_id: Optional[int] = None
        self.student_id: Optional[str] = None
        self.student_name: Optional[str] = None
        self.challenge: List[str] = []
        self.current_step: int = 0

        self.start_time: float = 0.0
        self.step_start_time: float = 0.0
        self.last_action_time: float = 0.0

        # Baseline calibration
        self.baseline_frames: List[Dict[str, Any]] = []
        self.baseline: Optional[Dict[str, Any]] = None

        # Action tracking
        self.consecutive_matches: int = 0
        self.required_consecutive_frames: int = 2

        # Blink state tracking
        self.eye_history: deque = deque(maxlen=25)
        self.blink_close_time: Optional[float] = None
        self.blink_detected: bool = False

        self.status_message: str = "Ready"
        self.error_reason: str = ""

    def is_active(self) -> bool:
        """Returns True if a challenge is currently underway."""
        return self.state in (self.STATE_COLLECTING_BASELINE, self.STATE_IN_PROGRESS)

    def is_passed(self) -> bool:
        """Returns True if the challenge was fully completed and verified."""
        return self.state == self.STATE_PASSED

    def is_failed(self) -> bool:
        """Returns True if the challenge failed or timed out."""
        return self.state in (self.STATE_FAILED, self.STATE_EXPIRED)

    def start(self, track_id: int, student_id: str, student_name: str,
              challenge: Optional[List[str]] = None) -> None:
        """
        Initializes a fresh randomized active liveness challenge session.
        """
        self.state = self.STATE_COLLECTING_BASELINE
        self.track_id = track_id
        self.student_id = student_id
        self.student_name = student_name
        self.challenge = challenge if challenge else generate_random_challenge()
        self.current_step = 0

        now = time.time()
        self.start_time = now
        self.step_start_time = now
        self.last_action_time = now

        self.baseline_frames = []
        self.baseline = None
        self.consecutive_matches = 0
        self.eye_history.clear()
        self.blink_close_time = None
        self.blink_detected = False
        self.error_reason = ""
        self.status_message = "Calibrating baseline position..."

    def abort(self, reason: str = "Challenge aborted") -> None:
        """Fails closed immediately."""
        self.state = self.STATE_FAILED
        self.error_reason = reason
        self.status_message = f"Failed: {reason}"

    def update(self, face_gray: np.ndarray, bbox: Tuple[int, int, int, int],
               current_track_id: int, frame_w: int, frame_h: int,
               now: Optional[float] = None) -> Tuple[bool, str]:
        """
        Feeds the current frame into the session state machine.

        Returns:
        --------
        Tuple[bool, str]
            (is_session_passed, status_description)
        """
        if now is None:
            now = time.time()

        if self.state in (self.STATE_PASSED, self.STATE_FAILED, self.STATE_EXPIRED):
            return (self.state == self.STATE_PASSED, self.status_message)

        # 1. Continuity Check: Face tracker must not change or vanish
        if current_track_id != self.track_id:
            self.abort("Face tracker lost or changed")
            return False, self.status_message

        # 2. Global Timeout Check
        if (now - self.start_time) > self.total_timeout:
            self.state = self.STATE_EXPIRED
            self.error_reason = "Total challenge timeout exceeded"
            self.status_message = "Liveness Timeout: Please look directly at the camera to retry."
            return False, self.status_message

        # 3. Extract Current Features
        features = FacePoseAnalyzer.extract_features(face_gray, bbox, frame_w, frame_h, now)
        self.eye_history.append((now, features["eye_openness"]))

        # 4. State: COLLECTING_BASELINE
        if self.state == self.STATE_COLLECTING_BASELINE:
            self.baseline_frames.append(features)
            if len(self.baseline_frames) >= 3:
                # Average baseline measurements
                self.baseline = {
                    "box_cx": float(np.mean([f["box_cx"] for f in self.baseline_frames])),
                    "box_cy": float(np.mean([f["box_cy"] for f in self.baseline_frames])),
                    "bw": float(np.mean([f["bw"] for f in self.baseline_frames])),
                    "bh": float(np.mean([f["bh"] for f in self.baseline_frames])),
                    "aspect": float(np.mean([f["aspect"] for f in self.baseline_frames])),
                    "cx_feat": float(np.mean([f["cx_feat"] for f in self.baseline_frames])),
                    "cy_feat": float(np.mean([f["cy_feat"] for f in self.baseline_frames])),
                    "eye_openness": float(np.mean([f["eye_openness"] for f in self.baseline_frames])),
                }
                self.state = self.STATE_IN_PROGRESS
                self.current_step = 0
                self.step_start_time = now
                self.consecutive_matches = 0
                curr_act = self.challenge[0]
                self.status_message = f"Step 1/2: {ACTION_INSTRUCTIONS.get(curr_act, curr_act)}"
            return False, self.status_message

        # 5. State: IN_PROGRESS
        if self.state == self.STATE_IN_PROGRESS:
            # Per-Step Timeout Check
            if (now - self.step_start_time) > self.step_timeout:
                self.state = self.STATE_EXPIRED
                self.error_reason = f"Step timeout on {self.challenge[self.current_step]}"
                self.status_message = "Liveness Timeout: Action not completed in time. Please retry."
                return False, self.status_message

            current_action = self.challenge[self.current_step]
            is_matched, detail = self._evaluate_action(current_action, features, now)

            if is_matched:
                self.consecutive_matches += 1
                if self.consecutive_matches >= self.required_consecutive_frames:
                    # Current action successfully fulfilled!
                    self.current_step += 1
                    self.consecutive_matches = 0
                    self.step_start_time = now
                    self.blink_close_time = None
                    self.blink_detected = False

                    if self.current_step >= len(self.challenge):
                        # All challenge steps passed!
                        self.state = self.STATE_PASSED
                        self.status_message = "Liveness Verified! Logging attendance..."
                        return True, self.status_message
                    else:
                        next_act = self.challenge[self.current_step]
                        self.status_message = f"Step {self.current_step+1}/{len(self.challenge)}: {ACTION_INSTRUCTIONS.get(next_act, next_act)}"
            else:
                # Reset consecutive count on non-matching frame
                self.consecutive_matches = 0

            return False, self.status_message

        return False, self.status_message

    def _evaluate_action(self, action: str, current: Dict[str, Any], now: float) -> Tuple[bool, str]:
        """Evaluates whether current frame features satisfy the active action requirement."""
        if not self.baseline:
            return False, "No baseline"

        # Yaw shift (internal features + box shift)
        yaw_delta = ((current["cx_feat"] - self.baseline["cx_feat"]) * 0.6 +
                     (current["box_cx"] - self.baseline["box_cx"]) * 0.4)

        # Pitch shift (vertical feature movement + box displacement)
        pitch_delta = ((current["cy_feat"] - self.baseline["cy_feat"]) * 0.6 +
                       (current["box_cy"] - self.baseline["box_cy"]) * 0.4)

        # 1. TURN_LEFT
        # User turns head to their left -> nose points towards camera right (positive yaw)
        if action == LivenessAction.TURN_LEFT:
            if yaw_delta > 0.016 or (current["box_cx"] - self.baseline["box_cx"]) > 0.018:
                return True, f"Turn Left detected (yaw={yaw_delta:.3f})"
            return False, f"Waiting for Turn Left (yaw={yaw_delta:.3f})"

        # 2. TURN_RIGHT
        # User turns head to their right -> nose points towards camera left (negative yaw)
        if action == LivenessAction.TURN_RIGHT:
            if yaw_delta < -0.016 or (current["box_cx"] - self.baseline["box_cx"]) < -0.018:
                return True, f"Turn Right detected (yaw={yaw_delta:.3f})"
            return False, f"Waiting for Turn Right (yaw={yaw_delta:.3f})"

        # 3. LOOK_UP
        # Head tilts up -> box and features shift upwards (-Y coordinate in image)
        if action == LivenessAction.LOOK_UP:
            if pitch_delta < -0.016 or (current["box_cy"] - self.baseline["box_cy"]) < -0.018:
                return True, f"Look Up detected (pitch={pitch_delta:.3f})"
            return False, f"Waiting for Look Up (pitch={pitch_delta:.3f})"

        # 4. RETURN_CENTER
        # User returns to baseline orientation
        if action == LivenessAction.RETURN_CENTER:
            if abs(yaw_delta) < 0.018 and abs(pitch_delta) < 0.018:
                return True, "Centered position verified"
            return False, f"Centering required (dyaw={yaw_delta:.3f}, dpitch={pitch_delta:.3f})"

        # 5. BLINK
        # Eye openness must drop below threshold (closed) then rebound to open within 0.08s - 1.2s
        if action == LivenessAction.BLINK:
            base_open = max(10.0, self.baseline["eye_openness"])
            curr_open = current["eye_openness"]
            ratio = curr_open / base_open

            if ratio < 0.80:
                if self.blink_close_time is None:
                    self.blink_close_time = now
            elif ratio >= 0.85 and self.blink_close_time is not None:
                duration = now - self.blink_close_time
                if 0.08 <= duration <= 1.20:
                    self.blink_detected = True
                    self.blink_close_time = None
                    return True, f"Blink verified ({duration:.2f}s)"
                else:
                    self.blink_close_time = None

            if self.blink_detected:
                return True, "Blink verified"
            return False, f"Waiting for blink (ratio={ratio:.2f})"

        return False, "Unknown action"

    def get_hud_details(self) -> Dict[str, Any]:
        """
        Returns structured details for drawing HUD banners and guidance overlays.
        """
        now = time.time()
        elapsed_step = max(0.0, now - self.step_start_time)
        remaining_step = max(0.0, self.step_timeout - elapsed_step)

        if self.state == self.STATE_COLLECTING_BASELINE:
            return {
                "title": "LIVENESS CHECK: CALIBRATING",
                "instruction": "Look directly at the camera...",
                "step_str": "Step 0/2",
                "icon": "🎯",
                "color": (255, 190, 0),  # Amber (BGR)
                "progress_ratio": min(1.0, len(self.baseline_frames) / 3.0),
                "remaining_seconds": self.step_timeout,
                "state": self.state,
            }

        elif self.state == self.STATE_IN_PROGRESS:
            curr_act = self.challenge[self.current_step]
            total_steps = len(self.challenge)
            step_num = self.current_step + 1
            icon = ACTION_ICONS.get(curr_act, "➔")
            instr = ACTION_INSTRUCTIONS.get(curr_act, curr_act)
            title = f"LIVENESS CHECK {icon} {ACTION_TITLES.get(curr_act, curr_act).upper()}"

            return {
                "title": title,
                "instruction": instr,
                "step_str": f"Step {step_num}/{total_steps}",
                "icon": icon,
                "color": (0, 220, 255),  # Cyan (BGR)
                "progress_ratio": max(0.0, remaining_step / self.step_timeout),
                "remaining_seconds": remaining_step,
                "state": self.state,
            }

        elif self.state == self.STATE_PASSED:
            return {
                "title": "✓ LIVENESS & IDENTITY VERIFIED",
                "instruction": "Biometric match confirmed. Attendance logged.",
                "step_str": "Complete",
                "icon": "✓",
                "color": (0, 255, 120),  # Neon Green (BGR)
                "progress_ratio": 1.0,
                "remaining_seconds": 0.0,
                "state": self.state,
            }

        elif self.state in (self.STATE_FAILED, self.STATE_EXPIRED):
            return {
                "title": "⚠ LIVENESS VERIFICATION FAILED",
                "instruction": self.status_message,
                "step_str": "Failed",
                "icon": "✕",
                "color": (0, 0, 240),  # Red (BGR)
                "progress_ratio": 0.0,
                "remaining_seconds": 0.0,
                "state": self.state,
            }

        return {
            "title": "READY",
            "instruction": "Position face in reticle",
            "step_str": "--",
            "icon": "●",
            "color": (148, 163, 184),
            "progress_ratio": 0.0,
            "remaining_seconds": 0.0,
            "state": self.state,
        }
