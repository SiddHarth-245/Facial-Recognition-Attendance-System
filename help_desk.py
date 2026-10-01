"""
========================================================================================
Institutional Help Desk & Technical Support Module (FaceAttend Cyber-Blue Edition)
========================================================================================
Module: help_desk.py
Author: Risan Shrestha (Lead Developer - UI Architecture & Interactive Portals)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module provides the administrative Technical Support and Help Desk directory for the
Facial Recognition Attendance Management System. It renders all 6 project developer email
addresses and module assignments with interactive 1-click mailto hyperlinks, institutional
roll numbers, and faculty mentorship guidance.

Developer Directory:
--------------------
1. Ved Prakash Pandey (23053645) - Face Detection Module       -> 23053645@kiit.ac.in
2. Siddharth Singh    (23053720) - Student Management          -> 23053720@kiit.ac.in
3. Deepak Sah         (23053920) - System Testing & SQA        -> 23053920@kiit.ac.in
4. Santosh Sah        (23053926) - Attendance System           -> 23053926@kiit.ac.in
5. Anshudeep Shah     (23053930) - Login & Security Subsystem  -> 23053930@kiit.ac.in
6. Risan Shrestha     (23053941) - UI Architecture & Dashboard -> 23053941@kiit.ac.in

Faculty Mentorship: Mr. Rakesh Kumar Rai (KIIT University)
========================================================================================
"""

import os
import webbrowser
import tkinter as tk
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

# Assets folder path
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Complete developer directory with roles, roll numbers, and official institutional emails
DEVELOPER_CONTACTS = [
    {
        "name": "Ved Prakash Pandey",
        "roll": "23053645",
        "role": "Face Detection & Camera Module",
        "email": "23053645@kiit.ac.in",
        "badge_color": "#dc2626"
    },
    {
        "name": "Siddharth Singh",
        "roll": "23053720",
        "role": "Student Management & Datasets",
        "email": "23053720@kiit.ac.in",
        "badge_color": "#2563eb"
    },
    {
        "name": "Deepak Sah",
        "roll": "23053920",
        "role": "System Testing & Quality Assurance",
        "email": "23053920@kiit.ac.in",
        "badge_color": "#9333ea"
    },
    {
        "name": "Santosh Sah",
        "roll": "23053926",
        "role": "Attendance Records & CSV Sync",
        "email": "23053926@kiit.ac.in",
        "badge_color": "#16a34a"
    },
    {
        "name": "Anshudeep Shah",
        "roll": "23053930",
        "role": "Login Portal & Security Subsystem",
        "email": "23053930@kiit.ac.in",
        "badge_color": "#ea580c"
    },
    {
        "name": "Risan Shrestha",
        "roll": "23053941",
        "role": "UI Design & Central Dashboard",
        "email": "23053941@kiit.ac.in",
        "badge_color": "#0891b2"
    }
]


class HelpDeskWindow:
    """
    Help Desk Window GUI Controller.
    
    Provides technical support directory with all 6 developer emails,
    module specializations, and direct 1-click mailto launching in Cyber-Blue UI.
    """

    def __init__(self, root: tk.Tk):
        """
        Initializes the Help Desk window, responsive geometry, and layout.

        Parameters:
        -----------
        root : tk.Tk or tk.Toplevel
            Parent Tkinter root window instance.
        """
        self.root = root
        self.root.title("FaceAttend - Help Desk & Technical Support Directory")
        
        # Calculate dynamic responsive screen dimensions (92% width x 88% height)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1200, int(screen_w * 0.92))
        win_h = min(720, int(screen_h * 0.88))
        x = (screen_w - win_w) // 2
        y = max(10, (screen_h - win_h) // 2 - 20)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.config(bg="#030b18")
        
        self.setup_ui()

    def setup_ui(self):
        """Constructs the Help Desk header bar, support directory, and developer contact cards."""
        # -------------------------------------------------------------------------
        # 1. Top Header Bar (Cyber-Blue Dark Styling)
        # -------------------------------------------------------------------------
        top_bar = tk.Frame(self.root, bg="#071a35", height=50, bd=1, relief=tk.SOLID, highlightbackground="#1e3a5f", highlightthickness=1)
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(8, 2))

        lbl_title = tk.Label(
            top_bar, 
            text="HELP DESK & TECHNICAL SUPPORT PORTAL", 
            font=("Segoe UI", 16, "bold"), 
            fg="#ffffff", 
            bg="#071a35"
        )
        lbl_title.pack(side=tk.LEFT, padx=16, pady=8)

        # Back Navigation Button (Responsive Top-Right)
        btn_back = tk.Button(
            top_bar, 
            text="✕ Back", 
            font=("Segoe UI", 10, "bold"), 
            bg="#1e293b", 
            fg="#ef4444", 
            activebackground="#334155", 
            activeforeground="#f87171", 
            bd=1, 
            relief=tk.SOLID, 
            padx=16, 
            pady=3,
            cursor="hand2",
            command=self.root.destroy
        )
        btn_back.pack(side=tk.RIGHT, padx=14, pady=8)
        btn_back.bind("<Enter>", lambda e: btn_back.config(bg="#dc2626", fg="#ffffff"))
        btn_back.bind("<Leave>", lambda e: btn_back.config(bg="#1e293b", fg="#ef4444"))

        # -------------------------------------------------------------------------
        # 2. Sub-Title Badge Strip
        # -------------------------------------------------------------------------
        sub_bar = tk.Frame(self.root, bg="#06152b", height=28)
        sub_bar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(0, 6))
        lbl_sub = tk.Label(
            sub_bar, 
            text="Module Engineers & Developer Direct Email Directory (Click any email to open mail client)", 
            font=("Segoe UI", 9, "bold"), 
            fg="#38bdf8", 
            bg="#06152b"
        )
        lbl_sub.pack(pady=4)

        # -------------------------------------------------------------------------
        # 3. Central Card Container
        # -------------------------------------------------------------------------
        main_frame = tk.Frame(self.root, bg="#071a35", bd=1, relief=tk.SOLID, highlightbackground="#1e3a5f", highlightthickness=1)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        # Guidance banner inside main card
        info_banner = tk.Frame(main_frame, bg="#091f40", padx=16, pady=8)
        info_banner.pack(fill=tk.X, padx=16, pady=(14, 10))

        lbl_banner_title = tk.Label(
            info_banner,
            text="📩 Need Technical Assistance or Found a Bug?",
            font=("Segoe UI", 11, "bold"),
            fg="#ffffff",
            bg="#091f40"
        )
        lbl_banner_title.pack(anchor="w")

        lbl_banner_desc = tk.Label(
            info_banner,
            text="For bug reports, OpenCV hardware troubleshooting, model synchronization inquiries, or module integration assistance, reach out directly to the assigned engineer below:",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#091f40"
        )
        lbl_banner_desc.pack(anchor="w", pady=(2, 0))

        # -------------------------------------------------------------------------
        # 4. 2-Column Grid for 6 Developer Contact Cards
        # -------------------------------------------------------------------------
        grid_frame = tk.Frame(main_frame, bg="#071a35")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        for r in range(3):
            grid_frame.grid_rowconfigure(r, weight=1)

        for idx, dev in enumerate(DEVELOPER_CONTACTS):
            row = idx // 2
            col = idx % 2

            dev_box = tk.Frame(
                grid_frame, 
                bg="#091f40", 
                bd=1, 
                relief=tk.SOLID, 
                highlightbackground="#1e3a5f",
                highlightthickness=1,
                padx=14, 
                pady=10
            )
            dev_box.grid(row=row, column=col, padx=8, pady=6, sticky="nsew")

            # Left color indicator strip
            strip = tk.Frame(dev_box, bg=dev["badge_color"], width=4)
            strip.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

            info_box = tk.Frame(dev_box, bg="#091f40")
            info_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Name and Roll
            lbl_name_roll = tk.Label(
                info_box, 
                text=f"{dev['name']}  •  Roll: {dev['roll']}", 
                font=("Segoe UI", 10, "bold"), 
                fg="#ffffff", 
                bg="#091f40", 
                anchor="w"
            )
            lbl_name_roll.pack(fill=tk.X)

            # Role / Module
            lbl_role = tk.Label(
                info_box, 
                text=f"Responsible for: {dev['role']}", 
                font=("Segoe UI", 9), 
                fg="#94a3b8", 
                bg="#091f40", 
                anchor="w"
            )
            lbl_role.pack(fill=tk.X, pady=(2, 0))

            # Clickable Email Hyperlink
            email_addr = dev["email"]
            lbl_email = tk.Label(
                info_box, 
                text=f"✉ {email_addr}", 
                font=("Segoe UI", 9, "bold", "underline"), 
                fg="#38bdf8", 
                bg="#091f40", 
                cursor="hand2", 
                anchor="w"
            )
            lbl_email.pack(fill=tk.X, pady=(4, 0))
            lbl_email.bind("<Button-1>", lambda e, mail=email_addr: self.open_mail(mail))

        # -------------------------------------------------------------------------
        # 5. Mentorship Guidance Footer Strip
        # -------------------------------------------------------------------------
        mentor_frame = tk.Frame(self.root, bg="#071a35", bd=1, relief=tk.SOLID, highlightbackground="#1e3a5f", highlightthickness=1)
        mentor_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(4, 8))

        inner_mentor = tk.Frame(mentor_frame, bg="#071a35")
        inner_mentor.pack(pady=6)

        lbl_m1 = tk.Label(
            inner_mentor, 
            text="Faculty Mentorship & Project Supervisor :", 
            font=("Segoe UI", 9, "bold"), 
            fg="#94a3b8", 
            bg="#071a35"
        )
        lbl_m1.pack(side=tk.LEFT, padx=(0, 8))

        lbl_m2 = tk.Label(
            inner_mentor, 
            text="Mr. Rakesh Kumar Rai", 
            font=("Segoe UI", 11, "bold"), 
            fg="#38bdf8", 
            bg="#071a35"
        )
        lbl_m2.pack(side=tk.LEFT, padx=(0, 8))

        lbl_m3 = tk.Label(
            inner_mentor, 
            text="|  KIIT Deemed to be University, Bhubaneswar", 
            font=("Segoe UI", 9), 
            fg="#cbd5e1", 
            bg="#071a35"
        )
        lbl_m3.pack(side=tk.LEFT)

    def open_mail(self, email_address: str):
        """Launches the default system email client targeting the selected developer's email."""
        try:
            webbrowser.open(f"mailto:{email_address}")
        except Exception:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = HelpDeskWindow(root)
    root.mainloop()
