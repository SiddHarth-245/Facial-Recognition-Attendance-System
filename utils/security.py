"""
========================================================================================
FaceAttend Security & Cryptographic Hashing Utilities
========================================================================================
Module: utils/security.py
Purpose:
    Provides cryptographic password and security question answer hashing using
    Python's standard library `hashlib.pbkdf2_hmac` (PBKDF2-HMAC-SHA256).

Standards & Design:
    - Algorithm: PBKDF2 with SHA-256 (NIST SP 800-132 compliant).
    - Iteration Count: 200,000 iterations for robust resistance against brute-force / GPU cracking.
    - Salt: 16 bytes (128 bits) of cryptographically secure random bytes via `secrets.token_bytes()`.
    - Format: `pbkdf2:sha256:<iterations>$<salt_hex>$<hash_hex>`
    - Verification: Constant-time comparison using `secrets.compare_digest` to prevent timing attacks.
    - Backward Compatibility: Gracefully handles legacy plaintext credentials during migration.
========================================================================================
"""

import hashlib
import secrets
from typing import Optional

PBKDF2_ITERATIONS = 200_000
SALT_SIZE_BYTES = 16
HASH_PREFIX = "pbkdf2:sha256"


def hash_password(password: str) -> str:
    """
    Computes a salted PBKDF2-HMAC-SHA256 hash for the given password string.

    Parameters:
    -----------
    password : str
        The raw plaintext password.

    Returns:
    --------
    str
        Formatted hash string: 'pbkdf2:sha256:200000$<salt_hex>$<hash_hex>'.
    """
    if not isinstance(password, str):
        password = str(password)
    salt = secrets.token_bytes(SALT_SIZE_BYTES)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS
    )
    return f"{HASH_PREFIX}:{PBKDF2_ITERATIONS}${salt.hex()}${hash_bytes.hex()}"


def is_password_hashed(stored_value: Optional[str]) -> bool:
    """
    Returns True if the stored value matches the PBKDF2 hash schema.
    """
    if not stored_value or not isinstance(stored_value, str):
        return False
    if not stored_value.startswith(f"{HASH_PREFIX}:"):
        return False
    parts = stored_value.split("$")
    return len(parts) == 3


# Alias for general value checking
is_hashed = is_password_hashed


def verify_password(plain_password: str, stored_hash_or_plain: Optional[str]) -> bool:
    """
    Verifies a plaintext password against a stored hash or legacy plaintext string.
    Uses constant-time comparison to protect against side-channel timing analysis.

    Parameters:
    -----------
    plain_password : str
        The user-submitted plaintext password.
    stored_hash_or_plain : Optional[str]
        The password string currently stored in the database.

    Returns:
    --------
    bool
        True if the password matches; False otherwise.
    """
    if stored_hash_or_plain is None or not isinstance(plain_password, str):
        return False

    if is_password_hashed(stored_hash_or_plain):
        try:
            parts = stored_hash_or_plain.split("$")
            if len(parts) != 3:
                return False
            meta, salt_hex, expected_hash_hex = parts
            iterations = int(meta.split(":")[2])
            salt = bytes.fromhex(salt_hex)
            test_hash = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt,
                iterations
            )
            return secrets.compare_digest(test_hash.hex(), expected_hash_hex)
        except Exception:
            return False

    # Legacy plaintext fallback (enables seamless zero-lockout login and in-place upgrade)
    return secrets.compare_digest(plain_password, stored_hash_or_plain)


def normalize_security_answer(answer: str) -> str:
    """
    Normalizes a security question answer by stripping surrounding whitespace and lowercasing.
    """
    if not answer or not isinstance(answer, str):
        return ""
    return answer.strip().lower()


def hash_security_answer(answer: str) -> str:
    """
    Hashes a normalized security question answer.
    """
    norm = normalize_security_answer(answer)
    return hash_password(norm)


def is_security_answer_hashed(stored_value: Optional[str]) -> bool:
    """
    Checks if a stored security answer is already hashed.
    """
    return is_password_hashed(stored_value)


def verify_security_answer(plain_answer: str, stored_hash_or_plain: Optional[str]) -> bool:
    """
    Verifies a user's submitted security answer against the stored hash or legacy plaintext.
    Answers are case-insensitive and whitespace-normalized.
    """
    if stored_hash_or_plain is None:
        return False
    norm_input = normalize_security_answer(plain_answer)

    if is_security_answer_hashed(stored_hash_or_plain):
        return verify_password(norm_input, stored_hash_or_plain)

    # Legacy plaintext comparison
    norm_stored = normalize_security_answer(stored_hash_or_plain)
    return secrets.compare_digest(norm_input, norm_stored)
