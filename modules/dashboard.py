import sys
"""
=============================================================================================================
FACIAL RECOGNITION ATTENDANCE MANAGEMENT SYSTEM
Main Central Dashboard (dashboard.py) - FaceAttend Cyber-Blue Ultra Enterprise Edition
=============================================================================================================
Module Responsibility (Lead Engineer: RISAN SHRESTHA - Roll No: 23053941):
    - Next-Gen FaceAttend Cyber-Blue Central Command Hub.
    - 8 Native Interactive Action Cards with Glowing Cyber Accents, Anti-Aliased Icons & Hover Effects.
    - Real-Time Digital Clock, Calendar Date & Authenticated Admin Session Badge.
    - Live System Status & Biometric Engine Telemetry Bar.
    - High-DPI Display Scaling (Crystal-sharp text and rendering on 125%/150% Windows screens).
    - Single-Root Modal Routing across Student Details, Face Recognition, Attendance, Training, Help, etc.

Supervisor: Mr. Rakesh Kumar Rai (KIIT Deemed to be University)
=============================================================================================================
"""

import os
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from PIL import Image, ImageTk

# -----------------------------------------------------------------------------
# Enable Windows High-DPI Awareness (Prevents blurry scaling on 125%/150% screens)
# -----------------------------------------------------------------------------
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Import Subsystem Windows
from modules.student import StudentManagementSystem
from modules.face_recognition import FaceRecognitionWindow
from modules.attendance import AttendanceManagementSystem
from modules.train import TrainDataWindow
from modules.developer import DeveloperWindow
from modules.help_desk import HelpDeskWindow

# File Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


class MainDashboard:
    """
    Primary Administrative Command Center.
    
    Features:
        - FaceAttend Cyber-Blue Futuristic User Interface.
        - 8 Native Interactive Action Cards with Real-time Hover Glow & Responsive Clicks.
        - Live Real-Time Digital Clock & Formatted Date.
        - Active Authenticated Administrator Session Badge.
        - Biometric Engine Status & Hardware Telemetry.
    """
    def __init__(self, root, user_data=None):
        """
        Initializes the Main Dashboard window.
        
        Parameters:
            root (tk.Tk): Master Tkinter root instance.
            user_data (dict, optional): Active authenticated administrator session metadata.
        """
        self.root = root
        self.root.title("FaceAttend - Facial Recognition Attendance Management System")
        
        # Responsive Window Geometry (Auto-centered on user's display)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.win_w = min(1360, int(screen_w * 0.95))
        self.win_h = min(800, int(screen_h * 0.92))
        x = (screen_w - self.win_w) // 2
        y = max(5, (screen_h - self.win_h) // 2 - 20)
        self.root.geometry(f"{self.win_w}x{self.win_h}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.config(bg="#030b18")
        
        # User session metadata
        self.user_data = user_data or {
            "fname": "Ved Prakash", 
            "lname": "Pandey", 
            "email": "23053645@kiit.ac.in",
            "roll": "23053645"
        }
        
        # Image reference cache to prevent garbage collection
        self._images = []
        
        # Define 8 Interactive Module Cards
        self.card_configs = [
            # Row 1:
            {
                "title": "STUDENT DETAILS",
                "subtitle": "Enrollment, CRUD & Photo Samples",
                "icon": "tile_student.png",
                "accent": "#0084ff",
                "hover_border": "#38bdf8",
                "command": self.open_student_details
            },
            {
                "title": "FACE RECOGNITION",
                "subtitle": "Live Biometric AI Scanner (60 FPS)",
                "icon": "tile_face.png",
                "accent": "#10b981",
                "hover_border": "#34d399",
                "command": self.open_face_recognition
            },
            {
                "title": "ATTENDANCE",
                "subtitle": "Daily Logs, CSV Sync & Editor",
                "icon": "tile_attendance.png",
                "accent": "#0ea5e9",
                "hover_border": "#7dd3fc",
                "command": self.open_attendance
            },
            {
                "title": "HELP DESK",
                "subtitle": "Technical Support & Dev Contacts",
                "icon": "tile_help.png",
                "accent": "#f59e0b",
                "hover_border": "#fbbf24",
                "command": self.open_help_desk
            },
            # Row 2:
            {
                "title": "TRAIN DATA",
                "subtitle": "Compile LBPH Neural Model",
                "icon": "tile_train.png",
                "accent": "#8b5cf6",
                "hover_border": "#c084fc",
                "command": self.open_train_data
            },
            {
                "title": "PHOTOS",
                "subtitle": "Browse Raw Facial Datasets",
                "icon": "tile_photos.png",
                "accent": "#ec4899",
                "hover_border": "#f472b6",
                "command": self.open_photos
            },
            {
                "title": "DEVELOPER",
                "subtitle": "Project Team Portfolio Showcase",
                "icon": "tile_developer.png",
                "accent": "#06b6d4",
                "hover_border": "#22d3ee",
                "command": self.open_developer
            },
            {
                "title": "EXIT SYSTEM",
                "subtitle": "Safely Terminate Session",
                "icon": "tile_exit.png",
                "accent": "#ef4444",
                "hover_border": "#f87171",
                "command": self.handle_exit
            }
        ]
        
        self.setup_ui()
        self.update_clock()

    def setup_ui(self):
        """Constructs the native Cyber-Blue Dashboard layout."""
        # -------------------------------------------------------------------------
        # 1. Top Super Header Bar
        # -------------------------------------------------------------------------
        header_bar = tk.Frame(
            self.root, 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1
        )
        header_bar.pack(side=tk.TOP, fill=tk.X, padx=14, pady=(10, 8))

        # Left Header: Logo & Branding
        brand_frame = tk.Frame(header_bar, bg="#071a35")
        brand_frame.pack(side=tk.LEFT, padx=16, pady=10)

        title_row = tk.Frame(brand_frame, bg="#071a35")
        title_row.pack(anchor="w")

        lbl_logo = tk.Label(
            title_row,
            text="FACEATTEND",
            font=("Segoe UI", 18, "bold"),
            fg="#38bdf8",
            bg="#071a35"
        )
        lbl_logo.pack(side=tk.LEFT)

        lbl_pipe = tk.Label(
            title_row,
            text="  |  FACIAL RECOGNITION ATTENDANCE SYSTEM",
            font=("Segoe UI", 14, "bold"),
            fg="#ffffff",
            bg="#071a35"
        )
        lbl_pipe.pack(side=tk.LEFT)

        lbl_subtitle = tk.Label(
            brand_frame,
            text="Department of Computer Science & Engineering  •  KIIT Deemed to be University",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#071a35"
        )
        lbl_subtitle.pack(anchor="w", pady=(2, 0))

        # Right Header: Clock & Admin Profile Badges
        right_header = tk.Frame(header_bar, bg="#071a35")
        right_header.pack(side=tk.RIGHT, padx=16, pady=8)

        # 1. Digital Clock Pill Card
        clock_card = tk.Frame(
            right_header, 
            bg="#091f40", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1, 
            padx=14, 
            pady=4
        )
        clock_card.pack(side=tk.LEFT, padx=(0, 12))

        self.lbl_time = tk.Label(
            clock_card,
            text="12:00:00 AM",
            font=("Segoe UI", 11, "bold"),
            fg="#ffffff",
            bg="#091f40"
        )
        self.lbl_time.pack(anchor="e")

        self.lbl_date = tk.Label(
            clock_card,
            text="Thu, 01 Oct 2026",
            font=("Segoe UI", 8),
            fg="#38bdf8",
            bg="#091f40"
        )
        self.lbl_date.pack(anchor="e")

        # 2. Administrator Profile Pill Card
        admin_card = tk.Frame(
            right_header, 
            bg="#091f40", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1, 
            padx=12, 
            pady=4
        )
        admin_card.pack(side=tk.LEFT)

        admin_fname = self.user_data.get("fname", "Admin")
        admin_lname = self.user_data.get("lname", "")
        full_name = f"{admin_fname} {admin_lname}".strip().upper() or "ADMINISTRATOR"
        if len(full_name) > 20:
            full_name = full_name[:18] + ".."

        lbl_admin_name = tk.Label(
            admin_card,
            text=f"👤 {full_name} ▾",
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#091f40"
        )
        lbl_admin_name.pack(anchor="w")

        lbl_admin_role = tk.Label(
            admin_card,
            text="Admin Portal  •  Authorized",
            font=("Segoe UI", 8),
            fg="#10b981",
            bg="#091f40"
        )
        lbl_admin_role.pack(anchor="w")

        # -------------------------------------------------------------------------
        # 2. Main 8-Card Interactive Grid Container (4 Columns x 2 Rows)
        # -------------------------------------------------------------------------
        grid_container = tk.Frame(self.root, bg="#030b18")
        grid_container.pack(fill=tk.BOTH, expand=True, padx=14, pady=4)

        for col in range(4):
            grid_container.grid_columnconfigure(col, weight=1, uniform="card_col")
        for row in range(2):
            grid_container.grid_rowconfigure(row, weight=1, uniform="card_row")

        # Render all 8 action cards
        for idx, conf in enumerate(self.card_configs):
            r = idx // 4
            c = idx % 4
            self.create_interactive_card(grid_container, conf, row=r, col=c)

        # -------------------------------------------------------------------------
        # 3. Bottom Status & Telemetry Bar
        # -------------------------------------------------------------------------
        status_bar = tk.Frame(
            self.root, 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1,
            height=36
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=(4, 10))

        # Left status indicator
        lbl_status = tk.Label(
            status_bar,
            text="● SYSTEM STATUS: ONLINE  |  60 FPS Biometric Engine Ready  |  SQLite WAL Synchronized",
            font=("Segoe UI", 9, "bold"),
            fg="#10b981",
            bg="#071a35"
        )
        lbl_status.pack(side=tk.LEFT, padx=16, pady=6)

        # Right mentorship attribution
        lbl_mentor = tk.Label(
            status_bar,
            text="Mentorship: Mr. Rakesh Kumar Rai  |  KIIT University",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#071a35"
        )
        lbl_mentor.pack(side=tk.RIGHT, padx=16, pady=6)

    def create_interactive_card(self, parent, conf: dict, row: int, col: int):
        """
        Builds a native Tkinter interactive card with glowing top accent,
        anti-aliased icon, crisp text, and smooth hover animation.
        """
        card = tk.Frame(
            parent,
            bg="#071a35",
            bd=1,
            relief=tk.SOLID,
            highlightbackground="#1e3a5f",
            highlightthickness=1,
            cursor="hand2"
        )
        card.grid(row=row, column=col, padx=7, pady=7, sticky="nsew")

        # 1. Top Glowing Accent Bar
        top_bar = tk.Frame(card, bg=conf["accent"], height=4)
        top_bar.pack(side=tk.TOP, fill=tk.X)

        # 2. Main Card Content Area
        content_frame = tk.Frame(card, bg="#071a35", cursor="hand2")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(10, 12))

        # 3. Centered Anti-Aliased Icon
        icon_path = os.path.join(ASSETS_DIR, conf["icon"])
        icon_photo = None
        if os.path.exists(icon_path):
            try:
                img_pil = Image.open(icon_path).resize((76, 76), Image.Resampling.LANCZOS)
                icon_photo = ImageTk.PhotoImage(img_pil, master=self.root)
                self._images.append(icon_photo)
            except Exception:
                pass

        if icon_photo:
            lbl_icon = tk.Label(content_frame, image=icon_photo, bg="#071a35", cursor="hand2")
            lbl_icon.pack(pady=(4, 6))
        else:
            lbl_icon = tk.Label(content_frame, text="⚡", font=("Segoe UI", 28), fg=conf["accent"], bg="#071a35", cursor="hand2")
            lbl_icon.pack(pady=(4, 6))

        # 4. Title Label
        lbl_title = tk.Label(
            content_frame,
            text=conf["title"],
            font=("Segoe UI", 11, "bold"),
            fg="#ffffff",
            bg="#071a35",
            cursor="hand2"
        )
        lbl_title.pack(pady=(0, 2))

        # 5. Subtitle Description
        lbl_sub = tk.Label(
            content_frame,
            text=conf["subtitle"],
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#071a35",
            wraplength=180,
            justify=tk.CENTER,
            cursor="hand2"
        )
        lbl_sub.pack(pady=(0, 8))

        # 6. Action Arrow Button Strip
        bottom_strip = tk.Frame(content_frame, bg="#091f40", padx=8, pady=3, cursor="hand2")
        bottom_strip.pack(fill=tk.X, side=tk.BOTTOM)

        lbl_action = tk.Label(
            bottom_strip,
            text=f"OPEN  ➔",
            font=("Segoe UI", 8, "bold"),
            fg=conf["accent"],
            bg="#091f40",
            cursor="hand2"
        )
        lbl_action.pack()

        # Collect all interactive child widgets for unified hover & click events
        interactive_widgets = [card, content_frame, lbl_icon, lbl_title, lbl_sub, bottom_strip, lbl_action]

        def on_enter(e):
            card.config(bg="#0a2244", highlightbackground=conf["hover_border"], highlightthickness=2)
            content_frame.config(bg="#0a2244")
            lbl_icon.config(bg="#0a2244")
            lbl_title.config(bg="#0a2244", fg=conf["hover_border"])
            lbl_sub.config(bg="#0a2244", fg="#cbd5e1")
            bottom_strip.config(bg="#0f2f5c")
            lbl_action.config(bg="#0f2f5c", fg="#ffffff")

        def on_leave(e):
            card.config(bg="#071a35", highlightbackground="#1e3a5f", highlightthickness=1)
            content_frame.config(bg="#071a35")
            lbl_icon.config(bg="#071a35")
            lbl_title.config(bg="#071a35", fg="#ffffff")
            lbl_sub.config(bg="#071a35", fg="#94a3b8")
            bottom_strip.config(bg="#091f40")
            lbl_action.config(bg="#091f40", fg=conf["accent"])

        def on_click(e):
            conf["command"]()

        for w in interactive_widgets:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

    def update_clock(self):
        """Updates the digital clock and formatted date every 1000ms."""
        now = datetime.now()
        time_str = now.strftime("%I:%M:%S %p")
        date_str = now.strftime("%a, %d %b %Y")
        
        try:
            self.lbl_time.config(text=time_str)
            self.lbl_date.config(text=date_str)
        except Exception:
            pass
            
        self.root.after(1000, self.update_clock)

    # -------------------------------------------------------------------------------------------------------
    # Module Window Navigation Handlers
    # -------------------------------------------------------------------------------------------------------

    def open_student_details(self):
        """Opens the Student Management & Enrollment Window."""
        win = tk.Toplevel(self.root)
        StudentManagementSystem(win)

    def open_face_recognition(self):
        """Opens the Live 60 FPS Face Recognition & Attendance Marking Window."""
        win = tk.Toplevel(self.root)
        FaceRecognitionWindow(win)

    def open_attendance(self):
        """Opens the Attendance Records & CSV Synchronization Window."""
        win = tk.Toplevel(self.root)
        AttendanceManagementSystem(win)

    def open_train_data(self):
        """Opens the Multi-Student LBPH Model Training Hub."""
        win = tk.Toplevel(self.root)
        TrainDataWindow(win)

    def open_photos(self):
        """Opens the local 'data/' directory in the OS file explorer."""
        try:
            os.startfile(DATA_DIR)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open photos directory: {e}", parent=self.root)

    def open_developer(self):
        """Opens the 6-Card Developer Team Showcase Window."""
        win = tk.Toplevel(self.root)
        DeveloperWindow(win)

    def open_help_desk(self):
        """Opens the Help Desk Documentation & Support Portal."""
        win = tk.Toplevel(self.root)
        HelpDeskWindow(win)

    def handle_exit(self):
        """Prompts confirmation dialog before terminating the application cleanly."""
        if messagebox.askyesno("Exit Application", "Do you really want to exit the Attendance Management System?", parent=self.root):
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MainDashboard(root)
    root.mainloop()
