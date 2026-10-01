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
from typing import Any, Dict, List, Optional, Tuple

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


def initialize_database():
    """
    Initializes the relational database schema, creating tables and indexes
    if they do not already exist, and pre-seeds the default administrator account.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # ---------------------------------------------------------------------
        # 1. Users Table (Administrative Accounts & Security Challenges)
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
                photo_sample TEXT DEFAULT 'No'
            );
        """)
        
        # ---------------------------------------------------------------------
        # 3. Attendance Records Table (Biometric Verification Logs)
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
        
        # Pre-seed default administrator credentials (if not already existing)
        cursor.execute("""
            INSERT OR IGNORE INTO users (fname, lname, contact, email, security_q, security_a, password)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "Vedprakash", "Pandey", "9876543210", "23053645@kiit.ac.in",
            "Your Birth Place", "City", "admin123"
        ))
        
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# User Authentication & Credential Recovery Helpers
# =============================================================================

def register_user(fname: str, lname: str, contact: str, email: str, 
                  security_q: str, security_a: str, password: str) -> Tuple[bool, str]:
    """
    Registers a new administrative user with transactional safety.

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
        cursor.execute("""
            INSERT INTO users (fname, lname, contact, email, security_q, security_a, password)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            fname.strip(), 
            lname.strip(), 
            contact.strip(), 
            email.lower().strip(), 
            security_q, 
            security_a.strip().lower(), 
            password
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
    Strictly enforces that ONLY registered users in the database can access the system.

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
        
        # Verify password for the registered user
        db_password = row[7]
        if db_password != password:
            return False, None, "Access Denied: Incorrect password for this registered account. Please check your password or reset it via 'Forgot Password?'."
        
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
                SELECT id FROM users 
                WHERE (email = ? OR fname = ?) AND security_q = ? AND LOWER(security_a) = ?
                ORDER BY id DESC
            """, (email.strip().lower(), email.strip(), security_q, security_a.strip().lower()))
        else:
            cursor.execute("""
                SELECT id FROM users 
                WHERE security_q = ? AND LOWER(security_a) = ?
                ORDER BY id DESC
            """, (security_q, security_a.strip().lower()))
        
        row = cursor.fetchone()
        if not row:
            return False, "Security Question or Answer did not match any record."
        
        user_id = row[0]
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, user_id))
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
                roll, gender, dob, email, phone, address, teacher, photo_sample
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            data.get("photo_sample", "No")
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
                phone = ?, address = ?, teacher = ?, photo_sample = ?
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


def delete_student(student_id: str) -> Tuple[bool, str]:
    """
    Deletes a student record by ID.

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
        return True, "Student deleted successfully!"
    except Exception as e:
        return False, f"Error deleting student: {str(e)}"
    finally:
        conn.close()


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
                   roll, gender, dob, email, phone, address, teacher, photo_sample
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
        Selected search criteria ("Student ID", "Roll No", "Phone No", "Student Name", "Department").
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
        "Department": "dep"
    }
    field = field_map.get(search_by, "student_id")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT dep, course, year, semester, student_id, name, division,
                   roll, gender, dob, email, phone, address, teacher, photo_sample
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
                "address": row[12], "teacher": row[13], "photo_sample": row[14]
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
        
        # Check daily deduplication query
        cursor.execute("""
            SELECT attendance_id FROM attendance 
            WHERE student_id = ? AND date = ?
        """, (str(student_id).strip(), date_str))
        existing = cursor.fetchone()
        if existing:
            return False, f"Attendance already marked for {name} ({student_id}) today."
        
        # Insert attendance log
        cursor.execute("""
            INSERT INTO attendance (student_id, roll, name, department, time, date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(student_id).strip(), roll, name, department, time_str, date_str, status))
        conn.commit()
        return True, f"Attendance marked for {name} ({student_id})!"
    except Exception as e:
        return False, f"Error logging attendance: {str(e)}"
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


# Ensure database schema is initialized upon module load
initialize_database()

