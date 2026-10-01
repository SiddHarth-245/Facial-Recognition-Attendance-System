"""
========================================================================================
Administrative User Registration Module (FaceAttend Cyber-Blue Enterprise Edition)
========================================================================================
Module: register.py
Author: Anshudeep Shah (Lead Developer - Security & Authentication Portals)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module provides the dedicated User Registration graphical interface for onboarding
new system administrators and faculty members into the Facial Recognition Attendance System.
It features a modern split-panel layout containing an inspirational banner on the left and a
multi-field registration form on the right with strict input validation and security question binding.

Security & Validation Features:
------------------------------
1. Field Validation & Integrity:
   - Verifies all required fields (First Name, Last Name, Contact Number, Email, Password, Confirm Password).
   - Validates that selected Security Question is not the default placeholder.
   - Enforces password consistency (`password == confirm_password`).
   - Requires explicit checkbox agreement to Terms & Conditions before submission.
2. Relational Persistence:
   - Calls `register_user(...)` in `database/db_manager.py` to insert the new account into SQLite.
   - Handles unique constraint violations (e.g. duplicate email registrations) gracefully with user dialogs.
3. Callback Workflow:
   - Seamlessly returns control back to the `LoginWindow` upon successful account creation.
========================================================================================
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
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

# Database CRUD helper for inserting new administrative accounts
from database.db_manager import register_user

# Filesystem path to graphical assets
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


class RegisterWindow:
    """
    Administrative User Registration Window GUI Controller.
    
    Constructs the split-screen registration form, captures admin credentials,
    and binds security questions for self-service password recovery.
    """

    def __init__(self, root: tk.Tk, on_login_click=None):
        """
        Initializes the Registration Window, form state variables, and UI layout.

        Parameters:
        -----------
        root : tk.Tk or tk.Toplevel
            Parent Tkinter root window instance.
        on_login_click : callable, optional
            Callback function to navigate back to the Login window.
        """
        self.root = root
        self.root.title("FaceAttend - Administrative User Registration")
        
        # Responsive Window Geometry (Auto-centered on user's display)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1120, int(screen_w * 0.90))
        win_h = min(680, int(screen_h * 0.88))
        x = (screen_w - win_w) // 2
        y = max(10, (screen_h - win_h) // 2 - 20)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.config(bg="#030b18")
        
        self.on_login_click = on_login_click
        self._images = []  # Explicit list holding PhotoImage references
        
        # -------------------------------------------------------------------------
        # Form Input State Variables
        # -------------------------------------------------------------------------
        self.var_fname = tk.StringVar()
        self.var_lname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_security_q = tk.StringVar()
        self.var_security_a = tk.StringVar()
        self.var_password = tk.StringVar()
        self.var_confirm_pass = tk.StringVar()
        self.var_terms = tk.IntVar(value=0)
        
        self.setup_ui()

    def setup_ui(self):
        """Builds the Cyber-Blue registration panel."""
        # -------------------------------------------------------------------------
        # Master Container Frame
        # -------------------------------------------------------------------------
        master_frame = tk.Frame(self.root, bg="#030b18")
        master_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # -------------------------------------------------------------------------
        # Left Panel: Promotional / Inspirational Wallpaper Banner
        # -------------------------------------------------------------------------
        left_frame = tk.Frame(master_frame, bg="#071a35", width=360, bd=1, relief=tk.SOLID, highlightbackground="#1e3a5f", highlightthickness=1)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16))
        left_frame.pack_propagate(False)
        
        banner_path = os.path.join(ASSETS_DIR, "register_banner.png")
        if os.path.exists(banner_path):
            try:
                img_raw = Image.open(banner_path).resize((360, 640), Image.Resampling.LANCZOS)
                self.img_banner = ImageTk.PhotoImage(img_raw, master=self.root)
                self._images.append(self.img_banner)
                lbl_banner = tk.Label(left_frame, image=self.img_banner, bg="#071a35")
                lbl_banner.pack(fill=tk.BOTH, expand=True)
            except Exception:
                self._render_left_fallback(left_frame)
        else:
            self._render_left_fallback(left_frame)
            
        # -------------------------------------------------------------------------
        # Right Panel: Registration Form Card
        # -------------------------------------------------------------------------
        right_card = tk.Frame(master_frame, bg="#071a35", bd=1, relief=tk.SOLID, highlightbackground="#1e3a5f", highlightthickness=1)
        right_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Inner padding frame
        form_inner = tk.Frame(right_card, bg="#071a35")
        form_inner.pack(fill=tk.BOTH, expand=True, padx=35, pady=25)
        
        # Main Header Title & Subtitle
        header_frame = tk.Frame(form_inner, bg="#071a35")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))

        heading = tk.Label(
            header_frame, 
            text="CREATE ADMIN ACCOUNT", 
            font=("Segoe UI", 18, "bold"), 
            fg="#ffffff", 
            bg="#071a35"
        )
        heading.pack(anchor="w")
        
        subheading = tk.Label(
            header_frame,
            text="Onboard new system administrator or faculty coordinator",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#071a35"
        )
        subheading.pack(anchor="w", pady=(2, 0))
        
        # Configure columns for 2-column grid
        form_inner.grid_columnconfigure(0, weight=1)
        form_inner.grid_columnconfigure(1, weight=1)

        # Helper method for creating cyber entries
        def make_cyber_entry(parent, var, show=None):
            return tk.Entry(
                parent,
                textvariable=var,
                show=show if show else "",
                font=("Segoe UI", 10),
                bg="#06152b",
                fg="#ffffff",
                insertbackground="#38bdf8",
                relief=tk.SOLID,
                bd=1,
                highlightthickness=1,
                highlightbackground="#1e3a5f",
                highlightcolor="#38bdf8"
            )

        # Row 1: First Name & Last Name
        lbl_fname = tk.Label(form_inner, text="First Name *", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#071a35")
        lbl_fname.grid(row=1, column=0, sticky="w", padx=(0, 15), pady=(2, 2))
        
        lbl_lname = tk.Label(form_inner, text="Last Name", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg="#071a35")
        lbl_lname.grid(row=1, column=1, sticky="w", pady=(2, 2))
        
        entry_fname = make_cyber_entry(form_inner, self.var_fname)
        entry_fname.grid(row=2, column=0, sticky="ew", padx=(0, 15), ipady=4, pady=(0, 10))
        
        entry_lname = make_cyber_entry(form_inner, self.var_lname)
        entry_lname.grid(row=2, column=1, sticky="ew", ipady=4, pady=(0, 10))
        
        # Row 2: Contact Number & Email Address
        lbl_contact = tk.Label(form_inner, text="Contact No *", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#071a35")
        lbl_contact.grid(row=3, column=0, sticky="w", padx=(0, 15), pady=(2, 2))
        
        lbl_email = tk.Label(form_inner, text="Email Address *", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#071a35")
        lbl_email.grid(row=3, column=1, sticky="w", pady=(2, 2))
        
        entry_contact = make_cyber_entry(form_inner, self.var_contact)
        entry_contact.grid(row=4, column=0, sticky="ew", padx=(0, 15), ipady=4, pady=(0, 10))
        
        entry_email = make_cyber_entry(form_inner, self.var_email)
        entry_email.grid(row=4, column=1, sticky="ew", ipady=4, pady=(0, 10))
        
        # Row 3: Security Question & Security Answer
        lbl_sec_q = tk.Label(form_inner, text="Select Security Question *", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#071a35")
        lbl_sec_q.grid(row=5, column=0, sticky="w", padx=(0, 15), pady=(2, 2))
        
        lbl_sec_a = tk.Label(form_inner, text="Security Answer *", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#071a35")
        lbl_sec_a.grid(row=5, column=1, sticky="w", pady=(2, 2))
        
        combo_sec_q = ttk.Combobox(
            form_inner, 
            textvariable=self.var_security_q, 
            font=("Segoe UI", 9), 
            state="readonly",
            values=[
                "Select",
                "Your Birth Place",
                "Your Girlfriend name",
                "Your Pet Name",
                "Your Favorite Teacher",
                "Your First School"
            ]
        )
        combo_sec_q.current(0)
        combo_sec_q.grid(row=6, column=0, sticky="ew", padx=(0, 15), ipady=3, pady=(0, 10))
        
        entry_sec_a = make_cyber_entry(form_inner, self.var_security_a)
        entry_sec_a.grid(row=6, column=1, sticky="ew", ipady=4, pady=(0, 10))
        
        # Row 4: Password & Confirm Password
        lbl_pass = tk.Label(form_inner, text="Password *", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#071a35")
        lbl_pass.grid(row=7, column=0, sticky="w", padx=(0, 15), pady=(2, 2))
        
        lbl_cpass = tk.Label(form_inner, text="Confirm Password *", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#071a35")
        lbl_cpass.grid(row=7, column=1, sticky="w", pady=(2, 2))
        
        entry_pass = make_cyber_entry(form_inner, self.var_password, show="*")
        entry_pass.grid(row=8, column=0, sticky="ew", padx=(0, 15), ipady=4, pady=(0, 12))
        
        entry_cpass = make_cyber_entry(form_inner, self.var_confirm_pass, show="*")
        entry_cpass.grid(row=8, column=1, sticky="ew", ipady=4, pady=(0, 12))
        
        # Row 5: Terms & Conditions Checkbox
        chk_terms = tk.Checkbutton(
            form_inner, 
            text="I agree to the Terms & Conditions and administrative privacy guidelines", 
            variable=self.var_terms, 
            font=("Segoe UI", 9), 
            fg="#cbd5e1",
            bg="#071a35", 
            selectcolor="#06152b",
            activebackground="#071a35", 
            activeforeground="#ffffff",
            cursor="hand2"
        )
        chk_terms.grid(row=9, column=0, columnspan=2, sticky="w", pady=(0, 16))
        
        # -------------------------------------------------------------------------
        # Action Buttons Container
        # -------------------------------------------------------------------------
        btn_frame = tk.Frame(form_inner, bg="#071a35")
        btn_frame.grid(row=10, column=0, columnspan=2, sticky="w", pady=(4, 0))
        
        # Blue "Register Now" Action Button
        btn_register = tk.Button(
            btn_frame, 
            text="REGISTER NOW  ➔", 
            font=("Segoe UI", 11, "bold"), 
            bg="#0084ff", 
            fg="white", 
            activebackground="#0095ff", 
            activeforeground="white", 
            cursor="hand2", 
            bd=0, 
            padx=24, 
            pady=8,
            command=self.handle_register
        )
        btn_register.pack(side=tk.LEFT, padx=(0, 18))
        btn_register.bind("<Enter>", lambda e: btn_register.config(bg="#0095ff"))
        btn_register.bind("<Leave>", lambda e: btn_register.config(bg="#0084ff"))
        
        # Dark Slate "Back to Login" Navigation Button
        btn_login = tk.Button(
            btn_frame, 
            text="🔒 Back to Login", 
            font=("Segoe UI", 11, "bold"), 
            bg="#1e293b", 
            fg="#94a3b8", 
            activebackground="#334155", 
            activeforeground="#ffffff", 
            cursor="hand2", 
            bd=0, 
            padx=20, 
            pady=8,
            command=self.handle_login_click
        )
        btn_login.pack(side=tk.LEFT)
        btn_login.bind("<Enter>", lambda e: btn_login.config(bg="#334155", fg="#ffffff"))
        btn_login.bind("<Leave>", lambda e: btn_login.config(bg="#1e293b", fg="#94a3b8"))

    def _render_left_fallback(self, left_frame):
        """Renders stylized fallback UI on the left panel if image is unavailable."""
        lbl_quote = tk.Label(
            left_frame, 
            text="FaceAttend\nSecurity Portal\n\n\"Your Biometric\nNature Is Your\nDigital Future\"", 
            font=("Segoe UI", 15, "bold"), 
            fg="#38bdf8", 
            bg="#071a35",
            justify=tk.CENTER
        )
        lbl_quote.pack(expand=True, padx=20)

    def handle_register(self):
        """
        Validates all user registration inputs and saves the new account in SQLite.
        """
        fname = self.var_fname.get().strip()
        lname = self.var_lname.get().strip()
        contact = self.var_contact.get().strip()
        email = self.var_email.get().strip()
        sec_q = self.var_security_q.get()
        sec_a = self.var_security_a.get().strip()
        password = self.var_password.get()
        confirm_pass = self.var_confirm_pass.get()
        
        # Mandatory fields check
        if not fname or not contact or not email or not sec_a or not password:
            messagebox.showerror("Validation Error", "All required fields marked with * must be filled!", parent=self.root)
            return
        
        # Security question validity check
        if sec_q == "Select":
            messagebox.showerror("Validation Error", "Please select a valid Security Question!", parent=self.root)
            return
        
        # Password match check
        if password != confirm_pass:
            messagebox.showerror("Validation Error", "Password and Confirm Password do not match!", parent=self.root)
            return
        
        # Password length check
        if len(password) < 4:
            messagebox.showwarning("Weak Password", "Password must be at least 4 characters long.", parent=self.root)
            return
        
        # Terms agreement check
        if not self.var_terms.get():
            messagebox.showerror("Terms & Conditions", "You must agree to the Terms & Conditions to register.", parent=self.root)
            return
        
        # Execute database persistence transaction
        success, msg = register_user(fname, lname, contact, email, sec_q, sec_a, password)
        if success:
            messagebox.showinfo("Registration Successful", msg, parent=self.root)
            self.handle_login_click()
        else:
            messagebox.showerror("Registration Failed", msg, parent=self.root)

    def handle_login_click(self):
        """Navigates back to the Login portal via callback or window destruction."""
        if self.on_login_click:
            self.on_login_click()
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = RegisterWindow(root)
    root.mainloop()
