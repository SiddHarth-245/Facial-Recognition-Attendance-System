import sys
"""
========================================================================================
Student Management Module - Facial Recognition Attendance Management System
========================================================================================
Module: student.py
Author: Siddharth Singh (Lead Developer - Student Management & Data Operations)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module provides the central administrative graphical user interface (GUI) and data
controller for registering, updating, searching, deleting, and managing student profiles
within the institutional database. In addition to standard CRUD (Create, Read, Update,
Delete) workflows, this module integrates an automated Computer Vision pipeline that uses
OpenCV and Haar Cascade Classifiers to capture, equalize, standardize, and store 100 face
photographic samples per student for downstream LBPH biometric training.

Key System Features:
-------------------
1. Next-Gen FaceAttend Cyber-Blue Enterprise Interface:
   - High-DPI Per-Monitor Scaled UI with Midnight Cyber palette (#030b18 / #071a35).
   - Glassmorphic form panels with cyan (#38bdf8) active highlights and crisp typography.
   - Custom Cyber-Themed Treeview table with high-contrast alternating rows.
2. Comprehensive Academic Categorization:
   - Supports 29+ academic branches categorized into Core Engineering, Emerging Technologies,
     and Interdisciplinary/Niche domains.
   - Supports degrees (B.Tech, M.Tech, BCA, MCA, FE, SE, TE, BE), academic cohorts up to 2030-2031,
     and 8 semesters.
3. OpenCV Live Dataset Acquisition:
   - Resilient DirectShow camera acquisition with dropped-frame tolerance.
   - Real-time frontal face detection via Haar Cascades with sensitive multi-scale parameters.
   - Histogram equalization (`cv2.equalizeHist`) and spatial normalization (`200x200` pixels).
   - Dynamic HUD visual feedback in a dedicated "Cropped Face" window.
4. Automated Re-training Trigger:
   - Immediately triggers `train_classifier_core()` upon dataset capture or deletion.
========================================================================================
"""

import os
import cv2
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from PIL import Image, ImageTk

# Enable Windows Per-Monitor High-DPI Awareness
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Import Database Manager CRUD functions for persistent storage operations
from database.db_manager import (
    add_student,
    update_student,
    delete_student,
    fetch_all_students,
    search_students,
    update_photo_sample_status,
)

# Define filesystem paths for assets and facial image dataset storage
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure the facial dataset directory exists on disk
os.makedirs(DATA_DIR, exist_ok=True)


class StudentManagementSystem:
    """
    Student Management System GUI and Event Controller.
    
    Manages the student administrative form, data validation, database persistence,
    Treeview tabular browsing/filtering, and the OpenCV camera capture session.
    """

    def __init__(self, root: tk.Tk):
        """
        Initializes the Student Management window, screen geometry, state variables,
        and GUI components.

        Parameters:
        -----------
        root : tk.Tk or tk.Toplevel
            The parent Tkinter window instance hosting this application interface.
        """
        self.root = root
        self.root.title("FaceAttend - Student Management & Enrollment")
        
        # Calculate dynamic screen geometry to fit 96% width and 92% height responsively
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1366, int(screen_w * 0.96))
        win_h = min(780, int(screen_h * 0.92))
        x = (screen_w - win_w) // 2
        y = max(5, (screen_h - win_h) // 2 - 20)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.config(bg="#030b18")
        
        # -------------------------------------------------------------------------
        # Form State Variables (Bound to Entry widgets and Comboboxes)
        # -------------------------------------------------------------------------
        self.var_dep = tk.StringVar(value="Select Department")
        self.var_course = tk.StringVar(value="Select Course")
        self.var_year = tk.StringVar(value="Select Year")
        self.var_semester = tk.StringVar(value="Select Semester")
        self.var_student_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_division = tk.StringVar(value="Select Division")
        self.var_roll = tk.StringVar()
        self.var_gender = tk.StringVar(value="Male")
        self.var_dob = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_address = tk.StringVar()
        self.var_teacher = tk.StringVar()
        self.var_parent_email = tk.StringVar()
        self.var_radio_photo = tk.StringVar(value="Take Photo Sample")
        
        # Table Search State Variables
        self.var_search_by = tk.StringVar(value="Select Option")
        self.var_search_txt = tk.StringVar()
        
        # Persistent image cache list to prevent Tkinter garbage collection
        self._images = []
        
        # Apply modern Cyber-Blue ttk styles
        self._apply_theme_styles()
        
        # Initialize User Interface layout, digital clock, and data table records
        self.setup_ui()
        self.update_clock()
        self.load_students_table()

    def _apply_theme_styles(self):
        """Configures ttk styles for treeview, comboboxes, and scrollbars."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Treeview styling
        style.configure(
            "Cyber.Treeview",
            background="#071830",
            foreground="#f8fafc",
            fieldbackground="#071830",
            rowheight=26,
            font=("Segoe UI", 9)
        )
        style.configure(
            "Cyber.Treeview.Heading",
            background="#0a2244",
            foreground="#38bdf8",
            relief="flat",
            font=("Segoe UI", 9, "bold")
        )
        style.map("Cyber.Treeview", background=[("selected", "#0084ff")], foreground=[("selected", "#ffffff")])
        style.map("Cyber.Treeview.Heading", background=[("active", "#0f3260")])

        # Combobox styling
        style.configure(
            "TCombobox",
            fieldbackground="#091f40",
            background="#0f2e5a",
            foreground="#ffffff",
            darkcolor="#1e3a5f",
            lightcolor="#1e3a5f",
            arrowcolor="#38bdf8",
            bordercolor="#1e3a5f"
        )
        style.map("TCombobox", fieldbackground=[("readonly", "#091f40")], foreground=[("readonly", "#ffffff")])

        # Scrollbar styling
        style.configure(
            "Cyber.Vertical.TScrollbar",
            troughcolor="#030b18",
            background="#1e3a5f",
            darkcolor="#1e3a5f",
            lightcolor="#1e3a5f",
            bordercolor="#030b18",
            arrowcolor="#38bdf8"
        )

    def setup_ui(self):
        """Constructs the visual hierarchy of the Student Management window."""
        # -------------------------------------------------------------------------
        # 1. Top Photographic Header Banner
        # -------------------------------------------------------------------------
        header_path = os.path.join(ASSETS_DIR, "student_header.png")
        if os.path.exists(header_path):
            img_hdr = Image.open(header_path).resize((1366, 110), Image.Resampling.LANCZOS)
            photo_hdr = ImageTk.PhotoImage(img_hdr)
            self._images.append(photo_hdr)
            lbl_header = tk.Label(self.root, image=photo_hdr, bg="#030b18")
            lbl_header.pack(side=tk.TOP, fill=tk.X)

        # -------------------------------------------------------------------------
        # 2. Sub-Header Title & Digital Clock Strip
        # -------------------------------------------------------------------------
        title_strip = tk.Frame(self.root, bg="#071933", height=38)
        title_strip.pack(side=tk.TOP, fill=tk.X)

        # Real-Time Digital Clock Badge (Top-Left)
        self.lbl_clock = tk.Label(
            title_strip, 
            text="00:00:00 PM", 
            font=("Segoe UI", 9, "bold"), 
            bg="#0d2346", 
            fg="#38bdf8", 
            bd=1, 
            relief=tk.SOLID, 
            padx=10, 
            pady=2
        )
        self.lbl_clock.place(x=12, y=6)

        # Central Header Title
        lbl_center_title = tk.Label(
            title_strip, 
            text="STUDENT ENROLLMENT & BIOMETRIC REPOSITORY", 
            font=("Segoe UI", 12, "bold"), 
            fg="#ffffff", 
            bg="#071933"
        )
        lbl_center_title.pack(pady=6)

        # Navigation Back Button (Top-Right)
        btn_back = tk.Button(
            title_strip, 
            text="✕  Back", 
            font=("Segoe UI", 9, "bold"), 
            bg="#0f213d", 
            fg="#ef4444", 
            activebackground="#1e3a5f", 
            activeforeground="#f87171", 
            bd=1, 
            relief=tk.SOLID, 
            padx=16, 
            pady=1,
            cursor="hand2",
            command=self.root.destroy
        )
        btn_back.place(relx=0.985, rely=0.5, anchor=tk.E)

        # -------------------------------------------------------------------------
        # 3. Main Body Split Container
        # -------------------------------------------------------------------------
        body_frame = tk.Frame(self.root, bg="#030b18")
        body_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 8))

        # =========================================================================
        # LEFT SECTION: Student Information Form Container
        # =========================================================================
        left_box = tk.LabelFrame(
            body_frame, 
            text=" 👤 Student Information Entry ", 
            font=("Segoe UI", 10, "bold"), 
            fg="#38bdf8", 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID
        )
        left_box.place(relx=0.0, rely=0.0, relwidth=0.44, relheight=1.0)

        # -------------------------------------------------------------------------
        # Group 1: Academic Information
        # -------------------------------------------------------------------------
        grp_course = tk.LabelFrame(
            left_box, 
            text=" Academic Course Details ", 
            font=("Segoe UI", 9, "bold"), 
            fg="#38bdf8", 
            bg="#091f40", 
            bd=1, 
            relief=tk.SOLID
        )
        grp_course.pack(fill=tk.X, padx=8, pady=(4, 4))

        lbl_style = {"font": ("Segoe UI", 8, "bold"), "bg": "#091f40", "fg": "#94a3b8"}

        # Department / Branch Selection Dropdown (29+ Engineering Disciplines)
        tk.Label(grp_course, text="Department:", **lbl_style).grid(row=0, column=0, sticky="w", padx=6, pady=2)
        combo_dep = ttk.Combobox(
            grp_course, textvariable=self.var_dep, font=("Segoe UI", 8), state="readonly", width=17,
            values=[
                "Select Department",
                "Computer Science and Engineering (CSE)",
                "Information Technology (IT)",
                "Electronics and Communication Engineering (ECE)",
                "Electrical Engineering (EE)",
                "Electrical and Electronics Engineering (EEE)",
                "Mechanical Engineering (ME)",
                "Civil Engineering (CE)",
                "Chemical Engineering",
                "Artificial Intelligence and Machine Learning (AI/ML)",
                "Data Science",
                "Cybersecurity",
                "Internet of Things (IoT)",
                "Cloud Computing",
                "Blockchain Technology",
                "Aerospace Engineering",
                "Biotechnology",
                "Automobile Engineering",
                "Robotics and Automation",
                "Mechatronics Engineering",
                "Environmental Engineering",
                "Agricultural Engineering",
                "Biomedical Engineering",
                "Petroleum Engineering",
                "Textile Engineering",
                "Mining Engineering",
                "Metallurgical Engineering",
                "Production and Industrial Engineering",
                "Food Technology",
                "Marine Engineering",
                "Computer", "IT", "Civil", "Mechanical", "Electrical", "Electronics"
            ]
        )
        combo_dep.grid(row=0, column=1, padx=4, pady=2)

        # Academic Course Dropdown
        tk.Label(grp_course, text="Course:", **lbl_style).grid(row=0, column=2, sticky="w", padx=6, pady=2)
        combo_course = ttk.Combobox(
            grp_course, textvariable=self.var_course, font=("Segoe UI", 8), state="readonly", width=13,
            values=["Select Course", "B.Tech", "M.Tech", "BCA", "MCA", "FE", "SE", "TE", "BE"]
        )
        combo_course.grid(row=0, column=3, padx=4, pady=2)

        # Academic Batch Year Dropdown
        tk.Label(grp_course, text="Year:", **lbl_style).grid(row=1, column=0, sticky="w", padx=6, pady=2)
        combo_year = ttk.Combobox(
            grp_course, textvariable=self.var_year, font=("Segoe UI", 8), state="readonly", width=17,
            values=[
                "Select Year", 
                "2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025", 
                "2025-2026", "2026-2027", "2027-2028", "2028-2029", "2029-2030", "2030-2031"
            ]
        )
        combo_year.grid(row=1, column=1, padx=4, pady=2)

        # Semester Dropdown
        tk.Label(grp_course, text="Semester:", **lbl_style).grid(row=1, column=2, sticky="w", padx=6, pady=2)
        combo_sem = ttk.Combobox(
            grp_course, textvariable=self.var_semester, font=("Segoe UI", 8), state="readonly", width=13,
            values=["Select Semester", "Semester-1", "Semester-2", "Semester-3", "Semester-4", "Semester-5", "Semester-6", "Semester-7", "Semester-8"]
        )
        combo_sem.grid(row=1, column=3, padx=4, pady=2)

        # -------------------------------------------------------------------------
        # Group 2: Student Identity & Contact Information
        # -------------------------------------------------------------------------
        grp_class = tk.LabelFrame(
            left_box, 
            text=" Personal & Academic Profile ", 
            font=("Segoe UI", 9, "bold"), 
            fg="#38bdf8", 
            bg="#091f40", 
            bd=1, 
            relief=tk.SOLID
        )
        grp_class.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 4))

        entry_opts = {
            "font": ("Segoe UI", 9), 
            "bg": "#06152b", 
            "fg": "#ffffff", 
            "insertbackground": "#38bdf8", 
            "bd": 1, 
            "relief": tk.SOLID, 
            "highlightthickness": 1, 
            "highlightbackground": "#1e3a5f", 
            "highlightcolor": "#38bdf8"
        }

        # Student ID & Name
        tk.Label(grp_class, text="StudentID:", **lbl_style).grid(row=0, column=0, sticky="w", padx=6, pady=3)
        tk.Entry(grp_class, textvariable=self.var_student_id, width=16, **entry_opts).grid(row=0, column=1, padx=4, pady=3)

        tk.Label(grp_class, text="Full Name:", **lbl_style).grid(row=0, column=2, sticky="w", padx=6, pady=3)
        tk.Entry(grp_class, textvariable=self.var_name, width=16, **entry_opts).grid(row=0, column=3, padx=4, pady=3)

        # Division & Roll No
        tk.Label(grp_class, text="Division:", **lbl_style).grid(row=1, column=0, sticky="w", padx=6, pady=3)
        combo_div = ttk.Combobox(
            grp_class, textvariable=self.var_division, font=("Segoe UI", 8), state="readonly", width=14,
            values=["Select Division", "A", "B", "C", "D"]
        )
        combo_div.grid(row=1, column=1, padx=4, pady=3)

        tk.Label(grp_class, text="Roll No:", **lbl_style).grid(row=1, column=2, sticky="w", padx=6, pady=3)
        tk.Entry(grp_class, textvariable=self.var_roll, width=16, **entry_opts).grid(row=1, column=3, padx=4, pady=3)

        # Gender & DOB
        tk.Label(grp_class, text="Gender:", **lbl_style).grid(row=2, column=0, sticky="w", padx=6, pady=3)
        combo_gen = ttk.Combobox(
            grp_class, textvariable=self.var_gender, font=("Segoe UI", 8), state="readonly", width=14,
            values=["Male", "Female", "Other"]
        )
        combo_gen.grid(row=2, column=1, padx=4, pady=3)

        tk.Label(grp_class, text="DOB:", **lbl_style).grid(row=2, column=2, sticky="w", padx=6, pady=3)
        tk.Entry(grp_class, textvariable=self.var_dob, width=16, **entry_opts).grid(row=2, column=3, padx=4, pady=3)

        # Email & Phone
        tk.Label(grp_class, text="Email:", **lbl_style).grid(row=3, column=0, sticky="w", padx=6, pady=3)
        tk.Entry(grp_class, textvariable=self.var_email, width=16, **entry_opts).grid(row=3, column=1, padx=4, pady=3)

        tk.Label(grp_class, text="Phone:", **lbl_style).grid(row=3, column=2, sticky="w", padx=6, pady=3)
        tk.Entry(grp_class, textvariable=self.var_phone, width=16, **entry_opts).grid(row=3, column=3, padx=4, pady=3)

        # Address & Teacher/Mentor
        tk.Label(grp_class, text="Address:", **lbl_style).grid(row=4, column=0, sticky="w", padx=6, pady=3)
        tk.Entry(grp_class, textvariable=self.var_address, width=16, **entry_opts).grid(row=4, column=1, padx=4, pady=3)

        tk.Label(grp_class, text="Mentor:", **lbl_style).grid(row=4, column=2, sticky="w", padx=6, pady=3)
        tk.Entry(grp_class, textvariable=self.var_teacher, width=16, **entry_opts).grid(row=4, column=3, padx=4, pady=3)

        # Parent Email & Blank Button & Test Notification
        tk.Label(grp_class, text="Parent Email:", **lbl_style).grid(row=5, column=0, sticky="w", padx=6, pady=3)
        
        parent_email_frame = tk.Frame(grp_class, bg="#091f40")
        parent_email_frame.grid(row=5, column=1, sticky="w", padx=4, pady=3)
        tk.Entry(parent_email_frame, textvariable=self.var_parent_email, width=11, **entry_opts).pack(side=tk.LEFT)
        tk.Button(
            parent_email_frame, 
            text="⌫ Blank", 
            font=("Segoe UI", 7, "bold"), 
            bg="#ef4444", 
            fg="#ffffff", 
            activebackground="#dc2626", 
            activeforeground="#ffffff", 
            bd=0, 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=4, 
            pady=2, 
            command=lambda: self.var_parent_email.set("")
        ).pack(side=tk.LEFT, padx=(3, 0))

        tk.Label(grp_class, text="Parent Alert:", **lbl_style).grid(row=5, column=2, sticky="w", padx=6, pady=3)
        btn_alert_frame = tk.Frame(grp_class, bg="#091f40")
        btn_alert_frame.grid(row=5, column=3, sticky="w", padx=4, pady=3)

        tk.Button(
            btn_alert_frame, 
            text="✉ Email Parent", 
            font=("Segoe UI", 8, "bold"), 
            bg="#0284c7", 
            fg="#ffffff", 
            activebackground="#0369a1", 
            activeforeground="#ffffff", 
            bd=0, 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=5, 
            pady=2, 
            command=self.handle_email_parent
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_alert_frame, 
            text="👁 Preview", 
            font=("Segoe UI", 8, "bold"), 
            bg="#10b981", 
            fg="#ffffff", 
            activebackground="#059669", 
            activeforeground="#ffffff", 
            bd=0, 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=5, 
            pady=2, 
            command=self.handle_preview_parent_email
        ).pack(side=tk.LEFT, padx=(3, 0))

        tk.Button(
            btn_alert_frame, 
            text="⚙ Settings", 
            font=("Segoe UI", 8), 
            bg="#334155", 
            fg="#cbd5e1", 
            activebackground="#475569", 
            activeforeground="#ffffff", 
            bd=0, 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=4, 
            pady=2, 
            command=self.handle_open_email_settings
        ).pack(side=tk.LEFT, padx=(3, 0))

        # Photo Sample Radio Buttons
        row_sub = tk.Frame(grp_class, bg="#091f40")
        row_sub.grid(row=6, column=0, columnspan=4, sticky="ew", padx=6, pady=3)

        tk.Radiobutton(
            row_sub, text="Take Photo Sample", variable=self.var_radio_photo, 
            value="Take Photo Sample", bg="#091f40", fg="#38bdf8", 
            selectcolor="#06152b", activebackground="#091f40", activeforeground="#38bdf8"
        ).pack(side=tk.LEFT, padx=4)

        tk.Radiobutton(
            row_sub, text="No Photo Sample", variable=self.var_radio_photo, 
            value="No Photo Sample", bg="#091f40", fg="#94a3b8", 
            selectcolor="#06152b", activebackground="#091f40", activeforeground="#ffffff"
        ).pack(side=tk.LEFT, padx=4)

        # -------------------------------------------------------------------------
        # Action Buttons (CRUD Operations)
        # -------------------------------------------------------------------------
        btn_bar1 = tk.Frame(left_box, bg="#071a35")
        btn_bar1.pack(fill=tk.X, padx=8, pady=(4, 2))

        btn_base = {
            "font": ("Segoe UI", 9, "bold"),
            "bd": 0,
            "relief": tk.FLAT,
            "cursor": "hand2"
        }

        tk.Button(btn_bar1, text="💾 Save", bg="#0084ff", fg="#ffffff", activebackground="#006cd4", activeforeground="#ffffff", command=self.handle_save, **btn_base).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, ipady=4)
        tk.Button(btn_bar1, text="🔄 Update", bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff", command=self.handle_update, **btn_base).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, ipady=4)
        tk.Button(btn_bar1, text="🗑 Delete", bg="#dc2626", fg="#ffffff", activebackground="#b91c1c", activeforeground="#ffffff", command=self.handle_delete, **btn_base).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, ipady=4)
        tk.Button(btn_bar1, text="↺ Reset", bg="#334155", fg="#ffffff", activebackground="#475569", activeforeground="#ffffff", command=self.handle_reset, **btn_base).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, ipady=4)

        # Primary Photo Capture Button
        btn_bar2 = tk.Frame(left_box, bg="#071a35")
        btn_bar2.pack(fill=tk.X, padx=8, pady=(2, 6))

        self.btn_take_photo = tk.Button(
            btn_bar2, text="📷 Take / Update 100 Photo Samples ➔", 
            bg="#10b981", fg="#ffffff", activebackground="#059669", activeforeground="#ffffff",
            command=self.handle_take_photo_sample, **btn_base
        )
        self.btn_take_photo.pack(fill=tk.X, ipady=6)

        # =========================================================================
        # RIGHT SECTION: Student Directory Table & Search System
        # =========================================================================
        right_box = tk.LabelFrame(
            body_frame, 
            text=" 📋 Enrolled Student Records Directory ", 
            font=("Segoe UI", 10, "bold"), 
            fg="#38bdf8", 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID
        )
        right_box.place(relx=0.45, rely=0.0, relwidth=0.55, relheight=1.0)

        # Search System Bar
        grp_search = tk.Frame(right_box, bg="#091f40", bd=1, relief=tk.SOLID)
        grp_search.pack(fill=tk.X, padx=8, pady=(6, 6))

        tk.Label(grp_search, text="Search By:", font=("Segoe UI", 9, "bold"), bg="#091f40", fg="#38bdf8").pack(side=tk.LEFT, padx=(8, 4), pady=4)
        
        combo_search = ttk.Combobox(
            grp_search, textvariable=self.var_search_by, font=("Segoe UI", 8), state="readonly", width=14,
            values=["Select Option", "Student ID", "Roll No", "Phone No", "Department", "Parent Email"]
        )
        combo_search.pack(side=tk.LEFT, padx=4, pady=4)

        tk.Entry(grp_search, textvariable=self.var_search_txt, width=16, **entry_opts).pack(side=tk.LEFT, padx=4, pady=4)

        tk.Button(grp_search, text="🔍 Search", bg="#0084ff", fg="#ffffff", activebackground="#006cd4", activeforeground="#ffffff", command=self.handle_search, **btn_base).pack(side=tk.LEFT, padx=4, ipady=2)
        tk.Button(grp_search, text="Show All", bg="#334155", fg="#ffffff", activebackground="#475569", activeforeground="#ffffff", command=self.load_students_table, **btn_base).pack(side=tk.LEFT, padx=4, ipady=2)

        # Treeview Table Container
        table_frame = tk.Frame(right_box, bg="#071a35")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, style="Cyber.Vertical.TScrollbar")

        columns = ("dep", "course", "year", "sem", "id", "name", "div", "roll", "gender", "dob", "email", "phone", "address", "teacher", "photo", "parent_email")
        self.student_table = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show="headings", 
            xscrollcommand=scroll_x.set, 
            yscrollcommand=scroll_y.set,
            style="Cyber.Treeview"
        )
        
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.student_table.xview)
        scroll_y.config(command=self.student_table.yview)

        # Configure Column Headers & Widths
        col_meta = [
            ("dep", "Department", 140),
            ("course", "Course", 80),
            ("year", "Year", 80),
            ("sem", "Semester", 80),
            ("id", "StudentID", 80),
            ("name", "Name", 120),
            ("div", "Division", 60),
            ("roll", "Roll No", 80),
            ("gender", "Gender", 70),
            ("dob", "DOB", 80),
            ("email", "Student Email", 130),
            ("phone", "Phone", 90),
            ("address", "Address", 120),
            ("teacher", "Mentor", 100),
            ("photo", "Sample", 65),
            ("parent_email", "Parent Email", 140)
        ]

        for cid, heading, width in col_meta:
            self.student_table.heading(cid, text=heading)
            self.student_table.column(cid, width=width, anchor=tk.CENTER)

        self.student_table.pack(fill=tk.BOTH, expand=True)
        self.student_table.bind("<ButtonRelease-1>", self.handle_row_selection)

    def update_clock(self):
        """Updates digital clock label every 1000 ms."""
        now = datetime.now()
        time_str = now.strftime("%I:%M:%S %p")
        try:
            self.lbl_clock.config(text=time_str)
        except Exception:
            pass
        self.root.after(1000, self.update_clock)

    def get_form_data(self) -> dict:
        """Extracts and standardizes form input parameters."""
        return {
            "dep": self.var_dep.get(),
            "course": self.var_course.get(),
            "year": self.var_year.get(),
            "semester": self.var_semester.get(),
            "student_id": self.var_student_id.get().strip(),
            "name": self.var_name.get().strip(),
            "division": self.var_division.get(),
            "roll": self.var_roll.get().strip(),
            "gender": self.var_gender.get(),
            "dob": self.var_dob.get().strip(),
            "email": self.var_email.get().strip(),
            "phone": self.var_phone.get().strip(),
            "address": self.var_address.get().strip(),
            "teacher": self.var_teacher.get().strip(),
            "photo_sample": "Yes" if self.var_radio_photo.get() == "Take Photo Sample" else "No",
            "parent_email": self.var_parent_email.get().strip()
        }

    def validate_form(self, data: dict) -> tuple:
        """Validates form parameters before database persistence."""
        if data["dep"] == "Select Department":
            return False, "Please select a valid Department."
        if not data["student_id"]:
            return False, "Student ID cannot be empty."
        if not data["name"]:
            return False, "Student Name cannot be empty."
        if not data["roll"]:
            return False, "Roll Number cannot be empty."
        return True, ""

    def handle_save(self):
        """Persists a new student profile into the SQLite database."""
        data = self.get_form_data()
        valid, msg = self.validate_form(data)
        if not valid:
            messagebox.showerror("Validation Error", msg, parent=self.root)
            return

        success, msg = add_student(data)
        if success:
            messagebox.showinfo("Success", "Student record registered successfully!", parent=self.root)
            self.load_students_table()
        else:
            messagebox.showerror("Database Error", msg, parent=self.root)

    def handle_update(self):
        """Updates an existing student profile matching `var_student_id`."""
        data = self.get_form_data()
        if not data["student_id"]:
            messagebox.showerror("Selection Error", "Please select a student record to update.", parent=self.root)
            return

        success, msg = update_student(data)
        if success:
            messagebox.showinfo("Success", "Student details updated successfully!", parent=self.root)
            self.load_students_table()
        else:
            messagebox.showerror("Database Error", msg, parent=self.root)

    def handle_delete(self):
        """Deletes a student record and associated photographic sample files."""
        sid = self.var_student_id.get().strip()
        if not sid:
            messagebox.showerror("Selection Error", "Please select a StudentID to delete.", parent=self.root)
            return

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete student ID {sid}?", parent=self.root):
            success, msg = delete_student(sid)
            if success:
                try:
                    import glob
                    old_samples = glob.glob(os.path.join(DATA_DIR, f"user.{sid}.*.jpg"))
                    for f in old_samples:
                        try:
                            os.remove(f)
                        except Exception:
                            pass
                    from modules.train import train_classifier_core
                    train_classifier_core()
                except Exception as ex:
                    print(f"Post-delete notice: {ex}")

                messagebox.showinfo("Success", "Student and dataset deleted successfully!", parent=self.root)
                self.handle_reset()
                self.load_students_table()
            else:
                messagebox.showerror("Error", msg, parent=self.root)

    def handle_reset(self):
        """Resets all form state variables back to default."""
        self.var_dep.set("Select Department")
        self.var_course.set("Select Course")
        self.var_year.set("Select Year")
        self.var_semester.set("Select Semester")
        self.var_student_id.set("")
        self.var_name.set("")
        self.var_division.set("Select Division")
        self.var_roll.set("")
        self.var_gender.set("Male")
        self.var_dob.set("")
        self.var_email.set("")
        self.var_phone.set("")
        self.var_address.set("")
        self.var_teacher.set("")
        self.var_parent_email.set("")
        self.var_radio_photo.set("Take Photo Sample")

    def load_students_table(self):
        """Fetches all registered students from SQLite and populates Treeview table."""
        rows = fetch_all_students()
        self.student_table.delete(*self.student_table.get_children())
        for row in rows:
            self.student_table.insert("", tk.END, values=row)

    def handle_search(self):
        """Performs substring SQL search matching selected criteria and query."""
        by = self.var_search_by.get()
        txt = self.var_search_txt.get().strip()
        if by == "Select Option" or not txt:
            self.load_students_table()
            return
        rows = search_students(by, txt)
        self.student_table.delete(*self.student_table.get_children())
        for row in rows:
            self.student_table.insert("", tk.END, values=row)

    def handle_row_selection(self, event):
        """Transfers selected student record values into input form for editing."""
        item = self.student_table.focus()
        row = self.student_table.item(item).get("values")
        if row:
            self.var_dep.set(row[0])
            self.var_course.set(row[1])
            self.var_year.set(row[2])
            self.var_semester.set(row[3])
            self.var_student_id.set(row[4])
            self.var_name.set(row[5])
            self.var_division.set(row[6])
            self.var_roll.set(row[7])
            self.var_gender.set(row[8])
            self.var_dob.set(row[9])
            self.var_email.set(row[10])
            self.var_phone.set(row[11])
            self.var_address.set(row[12])
            self.var_teacher.set(row[13])
            self.var_radio_photo.set("Take Photo Sample" if row[14] == "Yes" else "No Photo Sample")
            if len(row) > 15:
                self.var_parent_email.set(row[15] if row[15] is not None else "")
            else:
                self.var_parent_email.set("")

    def handle_test_parent_email(self):
        """Sends an immediate test attendance notification to the parent's email address."""
        p_email = self.var_parent_email.get().strip()
        if not p_email:
            messagebox.showwarning(
                "Parent Email Required", 
                "Please enter a Parent Email address before testing notification.", 
                parent=self.root
            )
            return

        name = self.var_name.get().strip() or "Student"
        roll = self.var_roll.get().strip() or "N/A"
        dep = self.var_dep.get() if self.var_dep.get() != "Select Department" else "General"
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%I:%M:%S %p")

        def on_complete(ok, msg):
            if ok:
                self.root.after(0, lambda: messagebox.showinfo(
                    "Parent Email Delivered",
                    f"Notification successfully delivered to parent!\n\n"
                    f"Recipient: {p_email}\n"
                    f"Student: {name} (Roll: {roll})\nStatus: Present\n\n"
                    f"Status: {msg}",
                    parent=self.root
                ))
            else:
                self.root.after(0, lambda: messagebox.showerror(
                    "Email Dispatch Notice",
                    f"Could not deliver email to parent:\n\n{msg}\n\n"
                    f"Recipient: {p_email}\n\n"
                    f"Resolution:\n"
                    f"1. Open Attendance window > Email Settings (or check .env file)\n"
                    f"2. Ensure BREVO_API_KEY and verified BREVO_SENDER_EMAIL are configured.",
                    parent=self.root
                ))

        try:
            from utils.email_notifier import send_attendance_email_async
            send_attendance_email_async(
                student_name=name,
                roll=roll,
                department=dep,
                date_str=date_str,
                time_str=time_str,
                status="Present",
                parent_email=p_email,
                callback=on_complete
            )
        except Exception as ex:
            messagebox.showerror("Dispatch Error", f"Failed to dispatch test notification:\n{str(ex)}", parent=self.root)

    def handle_preview_parent_email(self):
        """Generates and opens the formatted HTML parent email in the default browser."""
        p_email = self.var_parent_email.get().strip()
        name = self.var_name.get().strip() or "Student"
        roll = self.var_roll.get().strip() or "N/A"
        dep = self.var_dep.get() if self.var_dep.get() != "Select Department" else "Computer Science & Engineering"
        try:
            from utils.email_notifier import preview_email_in_browser
            preview_email_in_browser(
                student_name=name,
                roll=roll,
                dep=dep,
                status="PRESENT",
                parent_email=p_email
            )
        except Exception as ex:
            messagebox.showerror("Preview Error", str(ex), parent=self.root)

    def handle_email_parent(self):
        """Sends an attendance notification email to the parent of the currently displayed student via Brevo API."""
        p_email = self.var_parent_email.get().strip()
        if not p_email:
            messagebox.showwarning(
                "Parent Email Required",
                "Please enter or select a student with a registered Parent Email address first.",
                parent=self.root
            )
            return

        sid = self.var_id.get().strip() or "N/A"
        name = self.var_name.get().strip() or "Student"
        roll = self.var_roll.get().strip() or "N/A"
        dep = self.var_dep.get() if self.var_dep.get() != "Select Department" else "Computer Science & Engineering"
        now = datetime.now()
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%I:%M:%S %p")

        try:
            from utils.email_notifier import send_parent_attendance_notification
            ok, msg, outcome = send_parent_attendance_notification(
                student_id=sid,
                roll=roll,
                student_name=name,
                dep=dep,
                date_str=date_str,
                time_str=time_str,
                status="PRESENT",
                parent_email=p_email,
                force=True
            )
            if ok:
                messagebox.showinfo(
                    "Email Accepted by Brevo",
                    f"Attendance notification successfully accepted by Brevo API!\n\n"
                    f"• Recipient: {p_email}\n"
                    f"• Student: {name} (Roll: {roll})\n"
                    f"• Status: PRESENT\n\n"
                    f"{msg}",
                    parent=self.root
                )
            else:
                messagebox.showerror("Delivery Error", f"Failed to deliver notification:\n\n{msg}", parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error", f"Transmission error: {ex}", parent=self.root)

    def handle_open_email_settings(self):
        """Opens the interactive parent email notification configuration dialog."""
        try:
            from utils.email_notifier import open_email_config_dialog
            open_email_config_dialog(self.root)
        except Exception as ex:
            messagebox.showerror("Settings Error", str(ex), parent=self.root)

    # -------------------------------------------------------------------------
    # OpenCV Face Capture Logic & Dataset Generation Pipeline
    # -------------------------------------------------------------------------
    def handle_take_photo_sample(self):
        """Validates student profile and launches background sample acquisition."""
        if getattr(self, "is_capturing", False):
            messagebox.showinfo("In Progress", "A photo sample capture session is already in progress. Please complete or cancel it first.", parent=self.root)
            return

        student_id = self.var_student_id.get().strip()
        name = self.var_name.get().strip()
        
        if not student_id or not name:
            messagebox.showerror("Error", "Student ID and Student Name are required before taking photo samples!", parent=self.root)
            return

        data = self.get_form_data()
        data["photo_sample"] = "Yes"
        add_student(data)
        update_student(data)

        self.is_capturing = True
        if hasattr(self, "btn_take_photo") and self.btn_take_photo.winfo_exists():
            self.btn_take_photo.config(state=tk.DISABLED, text="⏳ Initializing Camera Studio...", bg="#475569")

        threading.Thread(target=self._capture_samples_worker, args=(student_id, name), daemon=True).start()

    def _capture_samples_worker(self, student_id: str, name: str):
        """Background worker thread capturing 100 high-clarity 200x200 multi-angle face images."""
        cap = None
        win_capture = "FaceAttend - High-Fidelity 100 Photo Sampling Studio"
        try:
            candidates = [
                os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml"),
                os.path.join(BASE_DIR, "classifier", "haarcascade_frontalface_default.xml"),
                os.path.join(getattr(cv2.data, 'haarcascades', ''), "haarcascade_frontalface_default.xml")
            ]
            face_classifier = None
            for p in candidates:
                if p and os.path.exists(p) and os.path.getsize(p) > 10000:
                    c = cv2.CascadeClassifier(p)
                    if not c.empty():
                        face_classifier = c
                        break

            if face_classifier is None or face_classifier.empty():
                self.root.after(0, lambda: messagebox.showerror("Error", "Could not load 'haarcascade_frontalface_default.xml'.", parent=self.root))
                return

            # Comprehensive multi-backend camera acquisition with fallback negotiation
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
            for backend in backends:
                for idx in [0, 1, 2]:
                    try:
                        temp_cap = cv2.VideoCapture(idx, backend)
                        if not temp_cap.isOpened():
                            temp_cap.release()
                            continue

                        # Read initial frames to test stream validity
                        success = False
                        for _ in range(10):
                            ret_t, frame_t = temp_cap.read()
                            if ret_t and frame_t is not None and frame_t.size > 0:
                                success = True
                                break
                            import time
                            time.sleep(0.04)

                        if success:
                            # Try setting HD 720p resolution
                            try:
                                temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                                temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                                temp_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            except Exception:
                                pass

                            ret_w, frame_w = temp_cap.read()
                            if ret_w and frame_w is not None and frame_w.size > 0:
                                cap = temp_cap
                                break
                            else:
                                # Fall back to default resolution
                                temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                                temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                                ret_w2, frame_w2 = temp_cap.read()
                                if ret_w2 and frame_w2 is not None and frame_w2.size > 0:
                                    cap = temp_cap
                                    break
                        temp_cap.release()
                    except Exception:
                        pass
                if cap is not None:
                    break

            if cap is None or not cap.isOpened():
                from modules.face_recognition import diagnose_camera_issue
                diag_msg = diagnose_camera_issue()
                self.root.after(0, lambda m=diag_msg: messagebox.showerror("Webcam Device Issue", m, parent=self.root))
                return

            # Sensor warm-up (flush 6 frames so auto-exposure and white balance settle)
            for _ in range(6):
                cap.read()

            sample_count = 0
            max_samples = 100
            cv2.namedWindow(win_capture, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win_capture, 720, 560)
            try:
                cv2.setWindowProperty(win_capture, cv2.WND_PROP_TOPMOST, 1)
            except Exception:
                pass

            clahe_engine = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            consecutive_empty = 0
            last_capture_time = 0.0
            capture_interval = 0.22  # ~4-5 clear, unblurred photos per second
            transition_until = 0.0
            transition_text = ""
            current_phase = 1
            last_sharpness_status = "STABILIZING"
            last_sharpness_val = 0.0

            while True:
                ret, frame = cap.read()
                if not ret or frame is None or frame.size == 0:
                    consecutive_empty += 1
                    if consecutive_empty > 25:
                        break
                    import time
                    time.sleep(0.01)
                    continue
                consecutive_empty = 0

                import time
                now_t = time.time()
                display_frame = frame.copy()
                h_f, w_f = display_frame.shape[:2]

                # Guided 3-Phase Multi-Pose Schedule (Center, Left Profile, Right Profile)
                if sample_count < 35:
                    phase_title = "PHASE 1/3: LOOK STRAIGHT (Frontal Pose)"
                    phase_sub = "Hold head steady and look directly at camera"
                    phase_color = (0, 255, 120)  # Neon Green
                    if current_phase != 1:
                        current_phase = 1
                elif sample_count < 68:
                    if current_phase == 1:
                        current_phase = 2
                        transition_until = now_t + 2.0  # 2.0s transition countdown
                        transition_text = "GET READY: SLOWLY TURN HEAD TO LEFT <-"
                    phase_title = "PHASE 2/3: TURN HEAD LEFT <- (Left Profile)"
                    phase_sub = "Turn head slightly to the LEFT and hold steady"
                    phase_color = (0, 235, 255)  # Cyan
                else:
                    if current_phase == 2:
                        current_phase = 3
                        transition_until = now_t + 2.0  # 2.0s transition countdown
                        transition_text = "GET READY: SLOWLY TURN HEAD TO RIGHT ->"
                    phase_title = "PHASE 3/3: TURN HEAD RIGHT -> (Right Profile)"
                    phase_sub = "Turn head slightly to the RIGHT and hold steady"
                    phase_color = (0, 160, 255)  # Vivid Orange / Blue

                is_in_transition = (now_t < transition_until)

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                enhanced_gray = clahe_engine.apply(gray)
                faces = face_classifier.detectMultiScale(
                    enhanced_gray, 
                    scaleFactor=1.1, 
                    minNeighbors=5, 
                    minSize=(70, 70)  # Filter out small or distant blurry detections
                )

                face_saved_this_frame = False

                for (x, y, w, h) in faces:
                    # Filter valid facial aspect ratio
                    aspect = w / float(max(1, h))
                    if not (0.75 <= aspect <= 1.30):
                        continue

                    face_raw = gray[y:y+h, x:x+w]
                    if face_raw.size == 0:
                        continue

                    # Sharpness verification (variance of Laplacian) to reject motion-blurred frames
                    sharpness = float(cv2.Laplacian(face_raw, cv2.CV_64F).var())
                    last_sharpness_val = sharpness
                    is_sharp = (sharpness >= 55.0)

                    # Dynamic bounding box color reflecting sharpness
                    box_color = phase_color if is_sharp else (0, 180, 255)
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), box_color, 2)
                    c_len = min(24, w // 4)
                    cv2.line(display_frame, (x, y), (x + c_len, y), (255, 255, 255), 2)
                    cv2.line(display_frame, (x, y), (x, y + c_len), (255, 255, 255), 2)
                    cv2.line(display_frame, (x + w, y), (x + w - c_len, y), (255, 255, 255), 2)
                    cv2.line(display_frame, (x + w, y), (x + w, y + c_len), (255, 255, 255), 2)
                    cv2.line(display_frame, (x, y + h), (x + c_len, y + h), (255, 255, 255), 2)
                    cv2.line(display_frame, (x, y + h), (x, y + h - c_len), (255, 255, 255), 2)
                    cv2.line(display_frame, (x + w, y + h), (x + w - c_len, y + h), (255, 255, 255), 2)
                    cv2.line(display_frame, (x + w, y + h), (x + w, y + h - c_len), (255, 255, 255), 2)

                    # Capture photo sample if sharp, not transitioning, and pacing interval met
                    if not is_in_transition and (now_t - last_capture_time >= capture_interval):
                        if is_sharp:
                            sample_count += 1
                            last_capture_time = now_t
                            last_sharpness_status = "CAPTURED"
                            face_saved_this_frame = True

                            # High-fidelity Lanczos4 normalization + Histogram Equalization
                            face_resized = cv2.resize(face_raw, (200, 200), interpolation=cv2.INTER_LANCZOS4)
                            face_crop = cv2.equalizeHist(face_resized)
                            file_name = f"user.{student_id}.{sample_count}.jpg"
                            file_path = os.path.join(DATA_DIR, file_name)
                            cv2.imwrite(file_path, face_crop)
                        else:
                            last_sharpness_status = "HOLD STEADY (BLUR)"
                    break  # Only process primary centered face

                # Top Guidance HUD Banner
                cv2.rectangle(display_frame, (0, 0), (w_f, 72), (15, 23, 42), -1)
                cv2.line(display_frame, (0, 72), (w_f, 72), phase_color, 2)

                if is_in_transition:
                    cv2.putText(display_frame, transition_text, (20, 46), cv2.FONT_HERSHEY_DUPLEX, 0.72, (0, 240, 255), 2, cv2.LINE_AA)
                else:
                    cv2.putText(display_frame, phase_title, (20, 28), cv2.FONT_HERSHEY_DUPLEX, 0.60, phase_color, 2, cv2.LINE_AA)
                    cv2.putText(display_frame, f"{phase_sub}  |  Student: {name} (ID: {student_id})", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (226, 232, 240), 1, cv2.LINE_AA)

                    # Sharpness telemetry badge
                    if last_sharpness_status == "CAPTURED" and face_saved_this_frame:
                        cv2.putText(display_frame, "[OK] CRISP & CLEAR SAVED", (w_f - 240, 28), cv2.FONT_HERSHEY_DUPLEX, 0.44, (0, 255, 120), 1, cv2.LINE_AA)
                    elif last_sharpness_status == "HOLD STEADY (BLUR)":
                        cv2.putText(display_frame, "[!] HOLD STILL (BLUR DETECTED)", (w_f - 275, 28), cv2.FONT_HERSHEY_DUPLEX, 0.44, (0, 180, 255), 1, cv2.LINE_AA)

                # Bottom Progress Bar
                cv2.rectangle(display_frame, (0, h_f - 44), (w_f, h_f), (15, 23, 42), -1)
                cv2.line(display_frame, (0, h_f - 44), (w_f, h_f - 44), (51, 65, 85), 1)

                progress_ratio = min(1.0, sample_count / float(max_samples))
                bar_w = int((w_f - 40) * progress_ratio)
                cv2.rectangle(display_frame, (20, h_f - 26), (w_f - 20, h_f - 14), (30, 41, 59), -1)
                if bar_w > 0:
                    cv2.rectangle(display_frame, (20, h_f - 26), (20 + bar_w, h_f - 14), phase_color, -1)

                status_str = f"Progress: {sample_count}/{max_samples} Clear Samples ({int(progress_ratio * 100)}%)  |  Sharpness: {int(last_sharpness_val)}  |  Press 'Q' to Cancel"
                cv2.putText(display_frame, status_str, (20, h_f - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (148, 163, 184), 1, cv2.LINE_AA)

                cv2.imshow(win_capture, display_frame)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), ord('Q'), ord('x'), ord('X'), 27) or sample_count >= max_samples:
                    break

                try:
                    if sample_count > 0 and cv2.getWindowProperty(win_capture, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except Exception:
                    pass

        finally:
            if cap is not None:
                cap.release()
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
            self.is_capturing = False
            self.root.after(0, lambda: self.btn_take_photo.config(state=tk.NORMAL, text="📷 Take / Update 100 Photo Samples ➔", bg="#10b981") if hasattr(self, "btn_take_photo") and self.btn_take_photo.winfo_exists() else None)

        if sample_count > 0:
            update_photo_sample_status(student_id, "Yes")
            self.root.after(0, self.load_students_table)
            try:
                from modules.train import train_classifier_core
                train_classifier_core()
            except Exception as ex:
                print(f"Auto-train notice: {ex}")

            self.root.after(0, lambda: messagebox.showinfo("Result", f"Successfully generated {sample_count} sharp, multi-angle photo samples for {name} (ID: {student_id})!\n\nLBPH Classifier has been re-trained automatically.", parent=self.root))
        else:
            self.root.after(0, lambda: messagebox.showwarning("Warning", "No face samples were captured during the session.", parent=self.root))


if __name__ == "__main__":
    root = tk.Tk()
    app = StudentManagementSystem(root)
    root.mainloop()
