"""
========================================================================================
Developer Information & Engineering Team Showcase Module (FaceAttend Cyber-Blue Edition)
========================================================================================
Module: developer.py
Author: Risan Shrestha & Anshudeep Shah (UI Design & Architectural Showcase)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module provides the Developer Portfolio and Institutional Attribution Window for the
Facial Recognition Attendance Management System. It presents a high-tech dark cybernetic UI
theme (`#030b18` / `#071a35`) displaying individual profile cards for all 6 student developers,
including official KIIT University Roll Numbers, technical roles, system competencies,
institutional email contact hyperlinks, and prominent faculty mentorship attribution under
Mr. Rakesh Kumar Rai.

Team Taxonomy & Contributions:
------------------------------
1. Ved Prakash Pandey (23053645 | 23053645@kiit.ac.in):
   - Face Detection Module (Live Video Stream, 2x Downsampling Pipeline, Haar Cascade & Dataset Generation).
2. Siddharth Singh (23053720 | 23053720@kiit.ac.in):
   - Student Management (29+ Engineering Branches, Academic Cohorts, CRUD Persistence & Model Training).
3. Deepak Sah (23053920 | 23053920@kiit.ac.in):
   - System Testing (Automated Test Suites, Model Validation, Boundary Edge-Cases & Verification).
4. Santosh Sah (23053926 | 23053926@kiit.ac.in):
   - Attendance System (Dual-Persistence Synchronization, SQLite Transactions & CSV Import/Export).
5. Anshudeep Shah (23053930 | 23053930@kiit.ac.in):
   - Login & Security (User Portal, Dynamic Biometric HUD Animation & Password Recovery).
6. Risan Shrestha (23053941 | 23053941@kiit.ac.in):
   - UI & Dashboard (Main Dashboard Layout, 8 Photographic Action Cards, Responsive Geometry & Help Desk).
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

# Assets folder path for developer portraits and UI backgrounds
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Metadata dictionary list of all 6 core project developers
DEVELOPERS = [
    {
        "name": "VED PRAKASH PANDEY",
        "roll": "23053645",
        "role": "Face Detection Module",
        "img": "dev_1.jpg",
        "skills": "Camera Live Feed, Face Recognition & Photo Dataset",
        "email": "23053645@kiit.ac.in",
        "badge_color": "#dc2626"
    },
    {
        "name": "SIDDHARTH SINGH",
        "roll": "23053720",
        "role": "Student Management",
        "img": "dev_2.jpg",
        "skills": "Student Details, Database Storage & Record Management",
        "email": "23053720@kiit.ac.in",
        "badge_color": "#2563eb"
    },
    {
        "name": "DEEPAK SAH",
        "roll": "23053920",
        "role": "System Testing",
        "img": "dev_4.jpg",
        "skills": "Software Testing, System Verification & Bug Fixing",
        "email": "23053920@kiit.ac.in",
        "badge_color": "#9333ea"
    },
    {
        "name": "SANTOSH SAH",
        "roll": "23053926",
        "role": "Attendance System",
        "img": "dev_3.jpg",
        "skills": "Attendance Records, CSV File Export & Daily Tracking",
        "email": "23053926@kiit.ac.in",
        "badge_color": "#16a34a"
    },
    {
        "name": "ANSHUDEEP SHAH",
        "roll": "23053930",
        "role": "Login & Security",
        "img": "dev_5.jpg",
        "skills": "User Login Portal, Registration & Password Reset",
        "email": "23053930@kiit.ac.in",
        "badge_color": "#ea580c"
    },
    {
        "name": "RISAN SHRESTHA",
        "roll": "23053941",
        "role": "UI & Dashboard",
        "img": "dev_6.jpg",
        "skills": "Main Dashboard Design, Window Layouts & Button Icons",
        "email": "23053941@kiit.ac.in",
        "badge_color": "#0891b2"
    }
]


class DeveloperWindow:
    """
    Developer Information Window GUI Controller.
    
    Renders a responsive 3x2 grid of developer profile cards with portraits,
    role badges, roll numbers, skill sets, and mailto hyperlinks.
    """

    def __init__(self, root: tk.Tk):
        """
        Initializes the Developer window, responsive screen dimensions, and photo cache.

        Parameters:
        -----------
        root : tk.Tk or tk.Toplevel
            Parent Tkinter root window instance.
        """
        self.root = root
        self.root.title("FaceAttend - Project Developer & Engineering Team")
        
        # Calculate dynamic responsive screen dimensions (96% width x 94% height)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1320, int(screen_w * 0.96))
        win_h = min(820, int(screen_h * 0.94))
        x = (screen_w - win_w) // 2
        y = max(5, (screen_h - win_h) // 2 - 20)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.config(bg="#030b18")
        
        # Image reference cache to preserve PhotoImage objects in memory
        self.photos_cache = []
        self.setup_ui()

    def setup_ui(self):
        """Constructs the Developer UI header, 3x2 card grid, and mentorship footer."""
        # -------------------------------------------------------------------------
        # 1. Top Header Bar (Cyber-Blue Dark Styling)
        # -------------------------------------------------------------------------
        top_bar = tk.Frame(self.root, bg="#071a35", height=50, bd=1, relief=tk.SOLID, highlightbackground="#1e3a5f", highlightthickness=1)
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(6, 2))

        lbl_title = tk.Label(
            top_bar, 
            text="DEVELOPER INFORMATION & ENGINEERING TEAM", 
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
        sub_bar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(0, 4))
        lbl_sub = tk.Label(
            sub_bar, 
            text="KIIT Deemed to be University • Department of Computer Science & Engineering • 6-Core Member Architecture", 
            font=("Segoe UI", 9, "bold"), 
            fg="#38bdf8", 
            bg="#06152b"
        )
        lbl_sub.pack(pady=4)

        # -------------------------------------------------------------------------
        # 3. Main 6-Card Grid (3 Columns x 2 Rows)
        # -------------------------------------------------------------------------
        main_frame = tk.Frame(self.root, bg="#030b18")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        for col in range(3):
            main_frame.grid_columnconfigure(col, weight=1)
        for row in range(2):
            main_frame.grid_rowconfigure(row, weight=1)

        for idx, dev in enumerate(DEVELOPERS):
            r = idx // 3
            c = idx % 3
            self.create_dev_card(main_frame, dev, row=r, col=c)

        # -------------------------------------------------------------------------
        # 4. Prominent Faculty Mentorship Guidance Footer Strip
        # -------------------------------------------------------------------------
        guide_frame = tk.Frame(self.root, bg="#071a35", bd=1, relief=tk.SOLID, highlightbackground="#1e3a5f", highlightthickness=1)
        guide_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(4, 6))

        inner_guide = tk.Frame(guide_frame, bg="#071a35")
        inner_guide.pack(pady=6)

        lbl_guide_title = tk.Label(
            inner_guide, 
            text="UNDER THE ACADEMIC GUIDANCE OF :", 
            font=("Segoe UI", 9, "bold"), 
            fg="#94a3b8", 
            bg="#071a35"
        )
        lbl_guide_title.pack(side=tk.LEFT, padx=(0, 10))

        lbl_guide_name = tk.Label(
            inner_guide, 
            text="Mr. Rakesh Kumar Rai", 
            font=("Segoe UI", 12, "bold"), 
            fg="#38bdf8", 
            bg="#071a35"
        )
        lbl_guide_name.pack(side=tk.LEFT, padx=(0, 10))

        lbl_guide_inst = tk.Label(
            inner_guide,
            text="|  KIIT Deemed to be University, Bhubaneswar",
            font=("Segoe UI", 9),
            fg="#cbd5e1",
            bg="#071a35"
        )
        lbl_guide_inst.pack(side=tk.LEFT)

    def create_dev_card(self, parent: tk.Widget, dev: dict, row: int, col: int):
        """
        Constructs an individual developer profile card widget.
        """
        card = tk.Frame(
            parent, 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1
        )
        card.grid(row=row, column=col, padx=6, pady=4, sticky="nsew")

        inner_frame = tk.Frame(card, bg="#071a35")
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # Left Panel: Portrait Image
        photo_frame = tk.Frame(inner_frame, bg="#071a35")
        photo_frame.pack(side=tk.LEFT, padx=(0, 12))

        img_path = os.path.join(ASSETS_DIR, dev["img"])
        photo_obj = None

        if os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path).convert("RGBA").resize((125, 125), Image.Resampling.LANCZOS)
                photo_obj = ImageTk.PhotoImage(pil_img, master=self.root)
            except Exception:
                pass

        if photo_obj:
            self.photos_cache.append(photo_obj)
            lbl_img = tk.Label(
                photo_frame, 
                image=photo_obj, 
                bg="#071a35", 
                bd=1, 
                relief=tk.SOLID, 
                highlightbackground="#38bdf8", 
                highlightthickness=1
            )
            lbl_img.image = photo_obj
            lbl_img.pack()
        else:
            lbl_placeholder = tk.Label(
                photo_frame, 
                text="👤\n[Photo]", 
                font=("Segoe UI", 10), 
                bg="#091f40", 
                fg="#38bdf8", 
                width=14, 
                height=6
            )
            lbl_placeholder.pack()

        # Right Panel: Metadata details
        info_frame = tk.Frame(inner_frame, bg="#071a35")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Technical Role Badge
        lbl_role_badge = tk.Label(
            info_frame, 
            text=dev["role"], 
            font=("Segoe UI", 8, "bold"), 
            bg=dev["badge_color"], 
            fg="#ffffff", 
            padx=8, 
            pady=2
        )
        lbl_role_badge.pack(anchor="w", pady=(0, 3))

        # Developer Name
        lbl_name = tk.Label(
            info_frame, 
            text=dev["name"], 
            font=("Segoe UI", 11, "bold"), 
            fg="#ffffff", 
            bg="#071a35",
            anchor="w"
        )
        lbl_name.pack(anchor="w")

        # Official KIIT Roll Number
        lbl_roll = tk.Label(
            info_frame, 
            text=f"Roll No: {dev['roll']}", 
            font=("Segoe UI", 9, "bold"), 
            fg="#38bdf8", 
            bg="#071a35",
            anchor="w"
        )
        lbl_roll.pack(anchor="w", pady=(0, 3))

        # Module Competencies & Responsibilities
        lbl_skills = tk.Label(
            info_frame, 
            text=dev["skills"], 
            font=("Segoe UI", 8), 
            fg="#94a3b8", 
            bg="#071a35", 
            wraplength=220, 
            justify=tk.LEFT,
            anchor="w"
        )
        lbl_skills.pack(anchor="w", pady=(0, 4))

        # Contact Email Hyperlink Button
        email_btn = tk.Button(
            info_frame, 
            text=f"✉ {dev['email']}", 
            font=("Segoe UI", 8, "underline"), 
            fg="#38bdf8", 
            bg="#071a35", 
            activeforeground="#7dd3fc", 
            activebackground="#071a35", 
            bd=0, 
            cursor="hand2", 
            anchor="w",
            command=lambda mail=dev["email"]: webbrowser.open(f"mailto:{mail}")
        )
        email_btn.pack(anchor="w")


if __name__ == "__main__":
    root = tk.Tk()
    app = DeveloperWindow(root)
    root.mainloop()
