"""
========================================================================================
Database Manager & Transactional Storage Engine
========================================================================================
Module: database/db_manager.py
Author: Siddharth Singh & Santosh Sah (Database Architecture & Transactional Safety)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module serves as the centralized, thread-safe persistence engine for the Facial
Recognition Attendance Management System. It abstracts all SQL relational database
interactions across three core tables: `users` (administrative accounts), `students`
(enrolled student profiles and academic taxonomy), and `attendance` (timestamped biometric logs).

High-Concurrency Engine Settings & Anti-Lock Architecture:
----------------------------------------------------------
1. Write-Ahead Logging (`PRAGMA journal_mode = WAL;`):
   - SQLite's default rollback journal locks the entire database file during writes,
     starving concurrent readers (such as live camera loops or GUI tables).
   - In WAL mode, writes are appended to a separate `-wal` file while readers query the
     main database file concurrently without blocking or contention.
2. Extended Busy Timeout (`PRAGMA busy_timeout = 60000;` and `timeout=60.0`):
   - Configures a 60-second hardware wait-and-retry loop before throwing `sqlite3.OperationalError: database is locked`.
3. Normal Synchronous Mode (`PRAGMA synchronous = NORMAL;`):
   - Significantly accelerates write I/O while guaranteeing full transactional ACID durability
     in WAL mode.
4. Foreign Key Enforcement (`PRAGMA foreign_keys = ON;`):
   - Ensures relational integrity across dependent database operations.
========================================================================================
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Set

# Cryptographic and authentication security utilities
from utils.security import (
    hash_password,
    verify_password,
    hash_security_answer,
    verify_security_answer,
    is_password_hashed,
    is_security_answer_hashed,
    is_hashed
)

# Resolve absolute path to database directory and SQLite storage file
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
DB_PATH = os.path.join(DB_DIR, "attendance_system.db")


def get_connection() -> sqlite3.Connection:
    """
    Establishes and returns a concurrency-tuned SQLite connection.

    Configuration:
    --------------
    - `timeout=60.0`: 60-second busy timeout for acquiring locks.
    - `check_same_thread=False`: Allows cross-thread cursor execution safely.
    - `PRAGMA foreign_keys = ON`: Enforces relational constraints.
    - `PRAGMA journal_mode = WAL`: Write-Ahead Logging for high-throughput reads/writes.
    - `PRAGMA busy_timeout = 60000`: 60,000ms engine busy timeout.
    - `PRAGMA synchronous = NORMAL`: Fast yet safe disk flushing in WAL mode.

    Returns:
    --------
    sqlite3.Connection
        Configured SQLite connection object.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=60.0, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 60000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def migrate_user_credentials(conn: sqlite3.Connection):
    """
    Safely migrates existing administrative accounts from plaintext to PBKDF2-HMAC-SHA256.
    Ensures zero silent lockouts: users can continue using existing passwords and security answers.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, password, security_a FROM users")
    users = cursor.fetchall()
    for uid, email, pwd, sec_a in users:
        updates = []
        params = []
        if pwd and not is_password_hashed(pwd):
            updates.append("password = ?")
            params.append(hash_password(pwd))
        if sec_a and not is_security_answer_hashed(sec_a):
            updates.append("security_a = ?")
            params.append(hash_security_answer(sec_a))
        if updates:
            params.append(uid)
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
    conn.commit()


def deduplicate_existing_records(conn: sqlite3.Connection):
    """
    Safely resolves legacy duplicate records prior to unique constraint enforcement.
    Retains the latest validated records and removes redundant attempts.
    """
    cursor = conn.cursor()
    
    # 1. Deduplicate attendance table
    cursor.execute("""
        SELECT student_id, date, COUNT(*) as cnt 
        FROM attendance 
        GROUP BY student_id, date 
        HAVING cnt > 1
    """)
    att_dupes = cursor.fetchall()
    for sid, dt, count in att_dupes:
        cursor.execute("""
            SELECT attendance_id FROM attendance 
            WHERE student_id = ? AND date = ? 
            ORDER BY attendance_id DESC
        """, (sid, dt))
        ids = [r[0] for r in cursor.fetchall()]
        keep_id = ids[0]
        del_ids = ids[1:]
        cursor.execute(f"DELETE FROM attendance WHERE attendance_id IN ({','.join(['?']*len(del_ids))})", del_ids)

    # 2. Deduplicate email_notifications table
    cursor.execute("""
        SELECT student_id, attendance_date, status, COUNT(*) as cnt 
        FROM email_notifications 
        GROUP BY student_id, attendance_date, status 
        HAVING cnt > 1
    """)
    notif_dupes = cursor.fetchall()
    for sid, dt, st, count in notif_dupes:
        cursor.execute("""
            SELECT id, delivery_result FROM email_notifications 
            WHERE student_id = ? AND attendance_date = ? AND status = ? 
            ORDER BY id DESC
        """, (sid, dt, st))
        rows = cursor.fetchall()
        accepted_ids = [r[0] for r in rows if r[1] == 'ACCEPTED']
        keep_id = accepted_ids[0] if accepted_ids else rows[0][0]
        del_ids = [r[0] for r in rows if r[0] != keep_id]
        if del_ids:
            cursor.execute(f"DELETE FROM email_notifications WHERE id IN ({','.join(['?']*len(del_ids))})", del_ids)


def initialize_database():
    """
    Initializes the relational database schema, creates tables and unique integrity indexes,
    executes safe credential migrations, and guarantees thread-safe WAL operation without
    hardcoding any administrative credentials.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # ---------------------------------------------------------------------
        # 1. Users Table (Administrative Accounts & Cryptographic Credentials)
        # ---------------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fname TEXT NOT NULL,
                lname TEXT NOT NULL,
                contact TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                security_q TEXT NOT NULL,
                security_a TEXT NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # ---------------------------------------------------------------------
        # 2. Students Table (Enrolled Student Profiles & Academic Taxonomy)
        # ---------------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                dep TEXT NOT NULL,
                course TEXT NOT NULL,
                year TEXT NOT NULL,
                semester TEXT NOT NULL,
                name TEXT NOT NULL,
                division TEXT NOT NULL,
                roll TEXT NOT NULL,
                gender TEXT NOT NULL,
                dob TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                teacher TEXT NOT NULL,
                photo_sample TEXT DEFAULT 'No',
                parent_email TEXT DEFAULT ''
            );
        """)
        
        # Schema migration: verify parent_email column exists if table previously created
        cursor.execute("PRAGMA table_info(students)")
        student_columns = [col[1] for col in cursor.fetchall()]
        if "parent_email" not in student_columns:
            cursor.execute("ALTER TABLE students ADD COLUMN parent_email TEXT DEFAULT '';")
        
        # ---------------------------------------------------------------------
        # 3. Attendance Records Table (Biometric Verification Logs & Integrity Index)
        # ---------------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                roll TEXT NOT NULL,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                time TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT DEFAULT 'Present'
            );
        """)
        
        # ---------------------------------------------------------------------
        # 4. Email Notifications Tracking Table (Duplicate Prevention & Audit)
        # ---------------------------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                roll TEXT NOT NULL,
                attendance_date TEXT NOT NULL,
                status TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                delivery_result TEXT NOT NULL,
                provider_message_id TEXT DEFAULT '',
                error_details TEXT DEFAULT '',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Deduplicate existing records before applying unique constraints
        deduplicate_existing_records(conn)

        # Enforce unique indexes for attendance and notification integrity
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_attendance_student_date 
            ON attendance(student_id, date);
        """)
        
        cursor.execute("DROP INDEX IF EXISTS idx_email_notif_student_date_status;")
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_email_notif_student_date_status_unique 
            ON email_notifications(student_id, attendance_date, status);
        """)
        
        # Migrate any remaining unhashed credentials safely to PBKDF2
        migrate_user_credentials(conn)
        
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# User Authentication & Credential Recovery Helpers
# =============================================================================

def get_user_count() -> int:
    """
    Returns the total number of registered administrative user accounts in SQLite.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


def is_first_run() -> bool:
    """
    Returns True if no administrative accounts exist, indicating first-run setup is required.
    """
    return get_user_count() == 0


def register_user(fname: str, lname: str, contact: str, email: str, 
                  security_q: str, security_a: str, password: str) -> Tuple[bool, str]:
    """
    Registers a new administrative user with PBKDF2-HMAC-SHA256 salted password
    and normalized security answer hashing for maximum credential defense.

    Parameters:
    -----------
    fname, lname, contact, email : str
        User personal and contact information.
    security_q, security_a : str
        Secret security question and normalized answer for password recovery.
    password : str
        User login password.

    Returns:
    --------
    Tuple[bool, str]
        (Success flag, Descriptive status message).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        hashed_pwd = hash_password(password)
        hashed_sec_a = hash_security_answer(security_a)

        cursor.execute("""
            INSERT INTO users (fname, lname, contact, email, security_q, security_a, password)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            fname.strip(), 
            lname.strip(), 
            contact.strip(), 
            email.lower().strip(), 
            security_q, 
            hashed_sec_a, 
            hashed_pwd
        ))
        conn.commit()
        return True, "User registered successfully!"
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    except Exception as e:
        return False, f"Registration failed: {str(e)}"
    finally:
        conn.close()


def verify_login(user_identifier: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Authenticates a user against Email, First Name, Last Name, or Full Name.
    Uses PBKDF2 salted hash comparison with constant-time verification.
    If a legacy plaintext account is encountered, upgrades it in-place seamlessly.

    Parameters:
    -----------
    user_identifier : str
        Supplied email or username.
    password : str
        Supplied password string.

    Returns:
    --------
    Tuple[bool, Optional[Dict[str, Any]], str]
        (Authentication success flag, User profile dict or None, Status message).
    """
    conn = get_connection()
    try:
        clean_id = user_identifier.strip().lower()
        clean_id_nospaces = clean_id.replace(" ", "")
        cursor = conn.cursor()
        
        # Query for matching user account regardless of password first
        cursor.execute("""
            SELECT id, fname, lname, contact, email, security_q, security_a, password
            FROM users 
            WHERE (
                LOWER(email) = ? 
                OR LOWER(fname) = ?
                OR LOWER(lname) = ?
                OR LOWER(TRIM(fname) || ' ' || TRIM(lname)) = ?
                OR LOWER(TRIM(fname) || TRIM(lname)) = ?
                OR REPLACE(LOWER(fname || lname), ' ', '') = ?
            )
        """, (clean_id, clean_id, clean_id, clean_id, clean_id, clean_id_nospaces))
        
        row = cursor.fetchone()
        if not row:
            return False, None, "Access Denied: This account is not registered. Only registered users are authorized to access the system. Please click 'Create Account' to register."
        
        # Verify password for the registered user using PBKDF2 constant-time check
        db_password = row[7]
        if not verify_password(password, db_password):
            return False, None, "Access Denied: Incorrect password for this registered account. Please check your password or reset it via 'Forgot Password?'."
        
        # Auto-upgrade legacy plaintext password if encountered
        if not is_password_hashed(db_password):
            try:
                cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(password), row[0]))
                conn.commit()
            except Exception:
                pass

        user_data = {
            "id": row[0],
            "fname": row[1],
            "lname": row[2],
            "contact": row[3],
            "email": row[4],
            "security_q": row[5],
            "security_a": row[6]
        }
        return True, user_data, "Login successful! Welcome to FaceAttend."
    except Exception as e:
        return False, None, f"Authentication error: {str(e)}"
    finally:
        conn.close()


def reset_password(security_q: str, security_a: str, new_password: str, email: Optional[str] = None) -> Tuple[bool, str]:
    """
    Resets user password if security question and case-insensitive answer match.
    Verifies against hashed or legacy plaintext security answers.
    Persists the new password as a secure PBKDF2 hash.

    Parameters:
    -----------
    security_q : str
        Selected security question string.
    security_a : str
        Answer string.
    new_password : str
        New replacement password string.
    email : Optional[str]
        Optional email filter to disambiguate multiple accounts with identical questions/answers.

    Returns:
    --------
    Tuple[bool, str]
        (Success flag, Status message).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if email and email.strip():
            cursor.execute("""
                SELECT id, security_a FROM users 
                WHERE (LOWER(email) = ? OR LOWER(fname) = ?) AND security_q = ?
                ORDER BY id DESC
            """, (email.strip().lower(), email.strip().lower(), security_q))
        else:
            cursor.execute("""
                SELECT id, security_a FROM users 
                WHERE security_q = ?
                ORDER BY id DESC
            """, (security_q,))
        
        candidates = cursor.fetchall()
        matched_user_id = None
        needs_sec_a_upgrade = False

        for uid, stored_sec_a in candidates:
            if verify_security_answer(security_a, stored_sec_a):
                matched_user_id = uid
                needs_sec_a_upgrade = not is_security_answer_hashed(stored_sec_a)
                break

        if not matched_user_id:
            return False, "Security Question or Answer did not match any record."
        
        new_hashed_pwd = hash_password(new_password)
        if needs_sec_a_upgrade:
            cursor.execute("UPDATE users SET password = ?, security_a = ? WHERE id = ?", 
                           (new_hashed_pwd, hash_security_answer(security_a), matched_user_id))
        else:
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_hashed_pwd, matched_user_id))
        conn.commit()
        return True, "Password has been reset successfully!"
    except Exception as e:
        return False, f"Password reset error: {str(e)}"
    finally:
        conn.close()


# =============================================================================
# Student Management CRUD Helpers
# =============================================================================

def add_student(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Inserts a new student profile into the `students` table.

    Parameters:
    -----------
    data : Dict[str, Any]
        Dictionary containing all student attributes.

    Returns:
    --------
    Tuple[bool, str]
        (Success flag, Status message).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO students (
                student_id, dep, course, year, semester, name, division, 
                roll, gender, dob, email, phone, address, teacher, photo_sample, parent_email
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["student_id"].strip(),
            data["dep"],
            data["course"],
            data["year"],
            data["semester"],
            data["name"].strip(),
            data["division"],
            data["roll"].strip(),
            data["gender"],
            data["dob"].strip(),
            data["email"].strip(),
            data["phone"].strip(),
            data["address"].strip(),
            data["teacher"].strip(),
            data.get("photo_sample", "No"),
            data.get("parent_email", "").strip()
        ))
        conn.commit()
        return True, "Student added successfully!"
    except sqlite3.IntegrityError:
        return False, f"Student ID '{data['student_id']}' already exists."
    except Exception as e:
        return False, f"Error adding student: {str(e)}"
    finally:
        conn.close()


def update_student(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Updates an existing student profile matching `student_id`.

    Parameters:
    -----------
    data : Dict[str, Any]
        Dictionary of updated student attributes.

    Returns:
    --------
    Tuple[bool, str]
        (Success flag, Status message).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE students SET
                dep = ?, course = ?, year = ?, semester = ?, name = ?,
                division = ?, roll = ?, gender = ?, dob = ?, email = ?,
                phone = ?, address = ?, teacher = ?, photo_sample = ?, parent_email = ?
            WHERE student_id = ?
        """, (
            data["dep"],
            data["course"],
            data["year"],
            data["semester"],
            data["name"].strip(),
            data["division"],
            data["roll"].strip(),
            data["gender"],
            data["dob"].strip(),
            data["email"].strip(),
            data["phone"].strip(),
            data["address"].strip(),
            data["teacher"].strip(),
            data.get("photo_sample", "No"),
            data.get("parent_email", "").strip(),
            data["student_id"].strip()
        ))
        if cursor.rowcount == 0:
            return False, f"Student ID '{data['student_id']}' not found."
        conn.commit()
        return True, "Student updated successfully!"
    except Exception as e:
        return False, f"Error updating student: {str(e)}"
    finally:
        conn.close()


def clean_student_biometrics(student_id: str) -> int:
    """
    Permanently purges photographic facial training samples associated with a student.
    Enforces privacy and biometric sample retention safeguards.
    """
    import glob
    sid = str(student_id).strip()
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    patterns = [
        os.path.join(data_dir, f"user.{sid}.*.jpg"),
        os.path.join(data_dir, f"user.{sid}.*.png")
    ]
    removed_count = 0
    for p in patterns:
        for f in glob.glob(p):
            try:
                os.remove(f)
                removed_count += 1
            except Exception:
                pass
    return removed_count


def get_enrolled_student_ids() -> Set[str]:
    """
    Fetches the set of active student IDs currently registered in SQLite.
    Used by the training pipeline to ensure only valid enrolled student samples
    are compiled into biometric recognizer models.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM students")
        return {str(r[0]).strip() for r in cursor.fetchall()}
    finally:
        conn.close()


def delete_student(student_id: str) -> Tuple[bool, str]:
    """
    Deletes a student record by ID and purges associated facial biometric training samples.
    Rebuilds or invalidates the facial recognition classifier model to maintain biometric integrity.

    Parameters:
    -----------
    student_id : str
        Target student identifier to remove.

    Returns:
    --------
    Tuple[bool, str]
        (Success flag, Status message).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id.strip(),))
        if cursor.rowcount == 0:
            return False, f"Student ID '{student_id}' not found."
        conn.commit()
    except Exception as e:
        return False, f"Error deleting student: {str(e)}"
    finally:
        conn.close()

    # Purge biometric samples associated with the deleted student
    removed_samples = clean_student_biometrics(student_id)

    # Re-train or invalidate classifier model if biometric samples were removed
    if removed_samples > 0:
        try:
            from modules.train import train_classifier_core
            train_classifier_core()
        except Exception:
            pass

    return True, f"Student deleted successfully ({removed_samples} biometric samples purged)."


def fetch_all_students() -> List[Tuple]:
    """
    Queries all enrolled student records ordered by `student_id` ascending.

    Returns:
    --------
    List[Tuple]
        List of student row tuples.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dep, course, year, semester, student_id, name, division,
                   roll, gender, dob, email, phone, address, teacher, photo_sample, parent_email
            FROM students ORDER BY student_id ASC
        """)
        return cursor.fetchall()
    finally:
        conn.close()


def search_students(search_by: str, query: str) -> List[Tuple]:
    """
    Performs a substring `LIKE %query%` search across a designated column.

    Parameters:
    -----------
    search_by : str
        Selected search criteria ("Student ID", "Roll No", "Phone No", "Student Name", "Department", "Parent Email").
    query : str
        Substring to search for.

    Returns:
    --------
    List[Tuple]
        List of matching student record tuples.
    """
    field_map = {
        "Student ID": "student_id",
        "Roll No": "roll",
        "Phone No": "phone",
        "Student Name": "name",
        "Department": "dep",
        "Parent Email": "parent_email"
    }
    field = field_map.get(search_by, "student_id")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT dep, course, year, semester, student_id, name, division,
                   roll, gender, dob, email, phone, address, teacher, photo_sample, parent_email
            FROM students WHERE {field} LIKE ? ORDER BY student_id ASC
        """, (f"%{query.strip()}%",))
        return cursor.fetchall()
    finally:
        conn.close()


def get_student_by_id(student_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the complete profile dictionary of a student matching `student_id`.

    Parameters:
    -----------
    student_id : str
        Target student identifier.

    Returns:
    --------
    Optional[Dict[str, Any]]
        Dictionary of student fields, or None if no record found.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE student_id = ?", (str(student_id).strip(),))
        row = cursor.fetchone()
        if row:
            return {
                "student_id": row[0], "dep": row[1], "course": row[2], "year": row[3],
                "semester": row[4], "name": row[5], "division": row[6], "roll": row[7],
                "gender": row[8], "dob": row[9], "email": row[10], "phone": row[11],
                "address": row[12], "teacher": row[13], "photo_sample": row[14],
                "parent_email": row[15] if len(row) > 15 and row[15] is not None else ""
            }
        return None
    finally:
        conn.close()


def get_student_by_roll(roll: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the complete profile dictionary of a student matching their roll number.

    Parameters:
    -----------
    roll : str
        Target student roll number.

    Returns:
    --------
    Optional[Dict[str, Any]]
        Dictionary of student fields, or None if no record found.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE roll = ? ORDER BY student_id DESC", (str(roll).strip(),))
        row = cursor.fetchone()
        if row:
            return {
                "student_id": row[0], "dep": row[1], "course": row[2], "year": row[3],
                "semester": row[4], "name": row[5], "division": row[6], "roll": row[7],
                "gender": row[8], "dob": row[9], "email": row[10], "phone": row[11],
                "address": row[12], "teacher": row[13], "photo_sample": row[14],
                "parent_email": row[15] if len(row) > 15 and row[15] is not None else ""
            }
        return None
    finally:
        conn.close()


def update_photo_sample_status(student_id: str, status: str = "Yes") -> bool:
    """
    Updates the photo sample indicator flag ('Yes'/'No') for a student.

    Parameters:
    -----------
    student_id : str
        Student ID to update.
    status : str, optional
        Flag status ('Yes' by default).

    Returns:
    --------
    bool
        True if updated successfully; False otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET photo_sample = ? WHERE student_id = ?", (status, str(student_id).strip()))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# =============================================================================
# Attendance Management Helpers
# =============================================================================

def log_attendance(student_id: str, roll: str, name: str, department: str, 
                   time_str: str, date_str: str, status: str = "Present") -> Tuple[bool, str]:
    """
    Logs a new biometric attendance verification record with daily deduplication.
    Enforces atomic, race-free single-record integrity per student per date in SQLite.

    Parameters:
    -----------
    student_id, roll, name, department : str
        Student identification details.
    time_str, date_str : str
        Timestamp ('HH:MM:SS') and date ('DD/MM/YYYY') strings.
    status : str, optional
        Attendance status ('Present' by default).

    Returns:
    --------
    Tuple[bool, str]
        (Success flag, Status message).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Check daily deduplication query first
        cursor.execute("""
            SELECT attendance_id FROM attendance 
            WHERE student_id = ? AND date = ?
        """, (str(student_id).strip(), str(date_str).strip()))
        existing = cursor.fetchone()
        if existing:
            return False, f"Attendance already marked for {name} ({student_id}) today."
        
        # Insert attendance log with atomic transaction safety
        cursor.execute("""
            INSERT INTO attendance (student_id, roll, name, department, time, date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(student_id).strip(), str(roll).strip(), str(name).strip(), str(department).strip(), str(time_str).strip(), str(date_str).strip(), str(status).strip()))
        conn.commit()
        return True, f"Attendance marked for {name} ({student_id})!"
    except sqlite3.IntegrityError:
        return False, f"Attendance already marked for {name} ({student_id}) today."
    except Exception as e:
        return False, f"Error logging attendance: {str(e)}"
    finally:
        conn.close()


def is_student_marked_today(student_id: str, date_str: str) -> bool:
    """
    Checks if a student already has an attendance record logged for the specified date in SQLite.

    Parameters:
    -----------
    student_id : str
        Student identification key.
    date_str : str
        Date string ('DD/MM/YYYY').

    Returns:
    --------
    bool
        True if attendance was already recorded today, False otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT attendance_id FROM attendance 
            WHERE student_id = ? AND date = ?
        """, (str(student_id).strip(), str(date_str).strip()))
        return cursor.fetchone() is not None
    except Exception:
        return False
    finally:
        conn.close()


def fetch_all_attendance() -> List[Tuple]:
    """
    Fetches all attendance records ordered by `attendance_id` descending (latest first).

    Returns:
    --------
    List[Tuple]
        List of attendance log tuples.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT attendance_id, student_id, roll, name, department, time, date, status
            FROM attendance ORDER BY attendance_id DESC
        """)
        return cursor.fetchall()
    finally:
        conn.close()


def update_attendance_record(attendance_id: int, status: str) -> Tuple[bool, str]:
    """
    Updates the status ('Present'/'Absent') of a specific attendance record.

    Parameters:
    -----------
    attendance_id : int
        Primary key ID of the attendance record.
    status : str
        New attendance status string.

    Returns:
    --------
    Tuple[bool, str]
        (Success flag, Status message).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE attendance SET status = ? WHERE attendance_id = ?", (status, attendance_id))
        conn.commit()
        return True, "Attendance updated successfully!"
    except Exception as e:
        return False, f"Error updating attendance: {str(e)}"
    finally:
        conn.close()


def delete_attendance_record(attendance_id: int) -> Tuple[bool, str]:
    """
    Deletes a specific attendance record by its primary key `attendance_id`.

    Parameters:
    -----------
    attendance_id : int
        Primary key ID of the attendance record.

    Returns:
    --------
    Tuple[bool, str]
        (Success flag, Status message).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM attendance WHERE attendance_id = ?", (int(attendance_id),))
        if cursor.rowcount == 0:
            return False, f"Attendance record #{attendance_id} not found."
        conn.commit()
        return True, f"Attendance record #{attendance_id} deleted successfully!"
    except Exception as e:
        return False, f"Error deleting attendance record: {str(e)}"
    finally:
        conn.close()


# =============================================================================
# Email Notification Tracking & Duplicate Prevention Helpers
# =============================================================================

def has_notification_been_sent(student_id: str, attendance_date: str, status: str) -> bool:
    """
    Checks if a notification for this student, date, and status was already accepted by Brevo API.
    Prevents duplicate emails upon refresh, reload, or app restart.

    Parameters:
    -----------
    student_id : str
        Student ID (e.g. '1' or '23053645').
    attendance_date : str
        Date string (e.g. '30/10/2026').
    status : str
        Attendance status ('Present' or 'Absent').

    Returns:
    --------
    bool
        True if already successfully accepted by email provider; False otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM email_notifications 
            WHERE student_id = ? AND attendance_date = ? AND LOWER(status) = LOWER(?) AND delivery_result = 'ACCEPTED'
            LIMIT 1
        """, (str(student_id).strip(), str(attendance_date).strip(), str(status).strip()))
        return cursor.fetchone() is not None
    except Exception:
        return False
    finally:
        conn.close()


def record_notification_attempt(student_id: str, roll: str, attendance_date: str, 
                                status: str, recipient_email: str, delivery_result: str, 
                                provider_message_id: str = "", error_details: str = "") -> int:
    """
    Persistently logs an email notification dispatch attempt to SQLite for audit and deduplication.
    Uses UPSERT conflict resolution on (student_id, attendance_date, status) to enforce at most
    one notification record per student, date, and status while preserving ACCEPTED delivery proofs.

    Parameters:
    -----------
    student_id, roll, attendance_date, status, recipient_email : str
        Student and session details.
    delivery_result : str
        Outcome: 'ACCEPTED', 'FAILED', 'SKIPPED_DUPLICATE', 'CONFIG_ERROR', 'INVALID_RECIPIENT'.
    provider_message_id : str, optional
        Unique message ID returned by Brevo API (e.g. '<20261030...mailin.fr>').
    error_details : str, optional
        Sanitized error description.

    Returns:
    --------
    int
        Primary key ID of the inserted or updated record (or -1 on error).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        clean_sid = str(student_id).strip()
        clean_roll = str(roll).strip()
        clean_date = str(attendance_date).strip()
        clean_status = str(status).strip().upper()
        clean_email = str(recipient_email).strip()
        clean_result = str(delivery_result).strip()
        clean_msg_id = str(provider_message_id or "").strip()
        clean_err = str(error_details or "").strip()

        cursor.execute("""
            INSERT INTO email_notifications (
                student_id, roll, attendance_date, status, recipient_email, 
                delivery_result, provider_message_id, error_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id, attendance_date, status) DO UPDATE SET
                roll = excluded.roll,
                recipient_email = excluded.recipient_email,
                delivery_result = CASE 
                    WHEN email_notifications.delivery_result = 'ACCEPTED' AND excluded.delivery_result != 'ACCEPTED' 
                    THEN email_notifications.delivery_result 
                    ELSE excluded.delivery_result 
                END,
                provider_message_id = CASE 
                    WHEN excluded.provider_message_id != '' 
                    THEN excluded.provider_message_id 
                    ELSE email_notifications.provider_message_id 
                END,
                error_details = excluded.error_details,
                timestamp = CURRENT_TIMESTAMP
        """, (
            clean_sid,
            clean_roll,
            clean_date,
            clean_status,
            clean_email,
            clean_result,
            clean_msg_id,
            clean_err
        ))
        conn.commit()
        return cursor.lastrowid or -1
    except Exception:
        return -1
    finally:
        conn.close()


def get_notification_history(student_id: Optional[str] = None, 
                             attendance_date: Optional[str] = None, 
                             limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves recent notification tracking records ordered by timestamp descending.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT id, student_id, roll, attendance_date, status, recipient_email, delivery_result, provider_message_id, error_details, timestamp FROM email_notifications"
        conditions = []
        params: List[Any] = []
        if student_id:
            conditions.append("student_id = ?")
            params.append(str(student_id).strip())
        if attendance_date:
            conditions.append("attendance_date = ?")
            params.append(str(attendance_date).strip())
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [
            {
                "id": r[0], "student_id": r[1], "roll": r[2], "date": r[3],
                "status": r[4], "recipient_email": r[5], "delivery_result": r[6],
                "provider_message_id": r[7], "error_details": r[8], "timestamp": r[9]
            }
            for r in rows
        ]
    except Exception:
        return []
    finally:
        conn.close()


# Ensure database schema is initialized upon module load
initialize_database()

