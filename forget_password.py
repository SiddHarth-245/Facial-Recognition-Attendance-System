"""
========================================================================================
Administrative Password Recovery & Credential Reset Module (Cyber-Blue Enterprise Edition)
========================================================================================
Module: forget_password.py
Author: Anshudeep Shah (Lead Developer - Security & Authentication Portals)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module provides a secure, self-service modal dialog for resetting administrative
passwords using secret security question-and-answer pairs stored during account registration.
It runs as a top-level modal (`tk.Toplevel`) that grabs application focus, validates input
length, queries the SQLite database, and updates user password credentials.

Security & Architecture Details:
--------------------------------
1. Modal Window Architecture:
   - Uses `self.root.grab_set()` and `self.root.focus_force()` to enforce modal interaction,
     preventing parent window interactions until the password reset dialog is completed or dismissed.
2. Case-Insensitive Security Verification:
   - Evaluates security questions and case-folded security answers (`LOWER(security_a) = ?`)
     to account for user casing variations.
3. Password Complexity Enforcement:
   - Enforces minimum 4-character length check before triggering database update queries.
========================================================================================
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

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

# Database CRUD helper for password resetting
from database.db_manager import reset_password


class ForgetPasswordWindow:
    """
    Password Recovery Modal Dialog GUI Controller.
    
    Handles security challenge verification and credential updates in a sleek
    Cyber-Blue themed modal dialog.
    """

    def __init__(self, parent=None):
        """
        Initializes the Forget Password modal window, geometry, and form inputs.

        Parameters:
        -----------
        parent : tk.Tk or tk.Toplevel, optional
            Parent window instance over which this modal dialog is displayed.
        """
        # Instantiate as tk.Toplevel when parent exists to prevent multi-root crashes
        self.root = tk.Toplevel(parent) if parent else tk.Tk()
        self.root.title("FaceAttend - Password Recovery Portal")
        
        # Centered Modal Geometry
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w, win_h = 480, 480
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2 - 20
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.resizable(False, False)
        self.root.config(bg="#030b18")
        
        # Enforce modal focus on top
        self.root.grab_set()
        self.root.focus_force()
        
        self.setup_ui()

    def setup_ui(self):
        """Builds the Cyber-Blue password reset card."""
        # Main Card Frame
        card = tk.Frame(
            self.root, 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1
        )
        card.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header Badge & Title
        header_frame = tk.Frame(card, bg="#071a35")
        header_frame.pack(fill=tk.X, padx=25, pady=(20, 15))

        lbl_badge = tk.Label(
            header_frame,
            text="🔒 PASSWORD RECOVERY",
            font=("Segoe UI", 14, "bold"),
            fg="#ffffff",
            bg="#071a35"
        )
        lbl_badge.pack(anchor="w")

        lbl_sub = tk.Label(
            header_frame,
            text="Verify your security challenge question to update credentials",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#071a35"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Form Inputs Frame
        form_frame = tk.Frame(card, bg="#071a35")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=25)

        # 1. Security Question
        lbl_question = tk.Label(
            form_frame, 
            text="Select Security Question *", 
            font=("Segoe UI", 9, "bold"), 
            fg="#38bdf8", 
            bg="#071a35", 
            anchor="w"
        )
        lbl_question.pack(fill=tk.X, pady=(2, 2))
        
        self.combo_question = ttk.Combobox(
            form_frame, 
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
        self.combo_question.current(0)
        self.combo_question.pack(fill=tk.X, ipady=3, pady=(0, 10))
        
        # 2. Security Answer
        lbl_answer = tk.Label(
            form_frame, 
            text="Security Answer *", 
            font=("Segoe UI", 9, "bold"), 
            fg="#38bdf8", 
            bg="#071a35", 
            anchor="w"
        )
        lbl_answer.pack(fill=tk.X, pady=(2, 2))
        
        self.entry_answer = tk.Entry(
            form_frame, 
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
        self.entry_answer.pack(fill=tk.X, ipady=4, pady=(0, 10))
        
        # 3. New Password
        lbl_new_pass = tk.Label(
            form_frame, 
            text="New Password *", 
            font=("Segoe UI", 9, "bold"), 
            fg="#38bdf8", 
            bg="#071a35", 
            anchor="w"
        )
        lbl_new_pass.pack(fill=tk.X, pady=(2, 2))
        
        self.entry_new_pass = tk.Entry(
            form_frame, 
            font=("Segoe UI", 10), 
            show="*",
            bg="#06152b",
            fg="#ffffff",
            insertbackground="#38bdf8",
            relief=tk.SOLID,
            bd=1,
            highlightthickness=1,
            highlightbackground="#1e3a5f",
            highlightcolor="#38bdf8"
        )
        self.entry_new_pass.pack(fill=tk.X, ipady=4, pady=(0, 18))
        self.entry_new_pass.bind("<Return>", lambda e: self.handle_reset())

        # Action Buttons Container
        btn_container = tk.Frame(form_frame, bg="#071a35")
        btn_container.pack(fill=tk.X, pady=(0, 10))

        # Reset Action Button (Blue Cyber Styling)
        btn_reset = tk.Button(
            btn_container, 
            text="UPDATE PASSWORD  ➔", 
            font=("Segoe UI", 10, "bold"), 
            bg="#0084ff", 
            fg="white", 
            activebackground="#0095ff", 
            activeforeground="white", 
            cursor="hand2", 
            bd=0, 
            pady=8,
            command=self.handle_reset
        )
        btn_reset.pack(fill=tk.X, pady=(0, 8))
        btn_reset.bind("<Enter>", lambda e: btn_reset.config(bg="#0095ff"))
        btn_reset.bind("<Leave>", lambda e: btn_reset.config(bg="#0084ff"))

        # Cancel Button
        btn_cancel = tk.Button(
            btn_container,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#1e293b",
            fg="#94a3b8",
            activebackground="#334155",
            activeforeground="#ffffff",
            cursor="hand2",
            bd=0,
            pady=4,
            command=self.root.destroy
        )
        btn_cancel.pack(fill=tk.X)
        btn_cancel.bind("<Enter>", lambda e: btn_cancel.config(bg="#334155", fg="#ffffff"))
        btn_cancel.bind("<Leave>", lambda e: btn_cancel.config(bg="#1e293b", fg="#94a3b8"))

    def handle_reset(self):
        """
        Validates security challenge fields and triggers database password reset.
        """
        question = self.combo_question.get()
        answer = self.entry_answer.get().strip()
        new_pass = self.entry_new_pass.get()
        
        # Mandatory fields validation
        if question == "Select" or not answer or not new_pass:
            messagebox.showerror("Validation Error", "All fields marked with * are required!", parent=self.root)
            return
        
        # Password length validation
        if len(new_pass) < 4:
            messagebox.showwarning("Weak Password", "Password must be at least 4 characters long.", parent=self.root)
            return
        
        # Query database and update password
        success, msg = reset_password(question, answer, new_pass)
        if success:
            messagebox.showinfo("Password Updated", msg, parent=self.root)
            self.root.destroy()
        else:
            messagebox.showerror("Verification Failed", msg, parent=self.root)


if __name__ == "__main__":
    app = ForgetPasswordWindow()
    app.root.mainloop()
