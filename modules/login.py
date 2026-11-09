import sys
"""
=============================================================================================================
FACIAL RECOGNITION ATTENDANCE MANAGEMENT SYSTEM
Login Portal & Authentication Subsystem (login.py) - FaceAttend Cyber-Blue Edition
=============================================================================================================
Module Responsibility (Lead Engineer: ANSHUDEEP SHAH - Roll No: 23053930):
    - Administrative User Authentication & Role Validation.
    - Responsive FaceAttend Cyber-Blue Glassmorphic UI Theme (Zero Watermark).
    - Dynamic Aspect-Ratio Auto-Fitting (Guarantees Full 100% Uncropped Display on Any Resolution).
    - Session Persistence & Credential Caching ("Remember Me" JSON Storage).
    - Password Recovery & User Registration Navigation.
    - Single-Root Tkinter Window Lifecycle Management.

Supervisor: Mr. Rakesh Kumar Rai (KIIT Deemed to be University)
=============================================================================================================
"""

import os
import json
import tkinter as tk
from tkinter import messagebox
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

# Internal Database & Subsystem Imports
from database.db_manager import verify_login
from modules.register import RegisterWindow
from modules.forget_password import ForgetPasswordWindow

# System Directories & Session File Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SESSION_FILE = os.path.join(BASE_DIR, "database", ".user_session.json")


class LoginWindow:
    """
    Main Authentication Portal Interface.
    
    Features:
        - FaceAttend Cyber-Blue Glassmorphic Design System (Zero Watermarks).
        - Dynamic background scaling guaranteeing full 100% uncropped display.
        - Admin credentials validation against SQLite `users` table.
        - 'Remember Me' caching to `.user_session.json`.
        - Responsive window geometry computation.
        - Single-root lifecycle transitions into `MainDashboard`.
    """
    def __init__(self, root, on_login_success=None):
        """
        Initializes the Login Window.
        
        Parameters:
            root (tk.Tk): Master Tkinter root instance.
            on_login_success (callable, optional): Callback invoked upon successful login.
        """
        self.root = root
        self.on_login_success = on_login_success
        self.root.title("FaceAttend - Facial Recognition Attendance Management System")
        
        # Responsive Window Geometry (Auto-centered on user's display)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.win_w = min(1280, int(screen_w * 0.92))
        self.win_h = min(740, int(screen_h * 0.88))
        x = (screen_w - self.win_w) // 2
        y = max(10, (screen_h - self.win_h) // 2 - 20)
        self.root.geometry(f"{self.win_w}x{self.win_h}+{x}+{y}")
        self.root.resizable(True, True)
        self.root.config(bg="#030b18")
        
        # Reactive Tkinter form variables
        self.var_username = tk.StringVar()
        self.var_password = tk.StringVar()
        self.var_remember = tk.BooleanVar(value=True)
        self.show_password = False
        self._images = []  # Holds references to PhotoImage objects to prevent garbage collection
        
        # Debounce timer for resize events
        self._resize_timer = None
        self._last_dims = (self.win_w, self.win_h)
        
        self.load_saved_credentials()
        self.setup_ui()
        
        # Bind dynamic window resize event
        self._configure_bind_id = self.root.bind("<Configure>", self.handle_resize)
        self.root.after(150, self._check_first_run)

    def _check_first_run(self):
        """Detects if no administrative accounts exist and guides user through first-run setup."""
        try:
            from database.db_manager import is_first_run
            if is_first_run():
                messagebox.showinfo(
                    "First-Run Setup Required",
                    "Welcome to FaceAttend!\n\n"
                    "No administrator accounts currently exist in the database.\n"
                    "Please create your primary administrator account to secure the system.",
                    parent=self.root
                )
                self.open_register()
        except Exception:
            pass

    def load_saved_credentials(self):
        """Loads and auto-populates saved credentials if 'Remember Me' was enabled."""
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("remember", True):
                        self.var_username.set(data.get("username", ""))
                        self.var_remember.set(True)
            except Exception:
                pass

    def save_credentials(self, username, password=None):
        """Saves username in `.user_session.json` based on checkbox state (never caches plaintext passwords)."""
        try:
            os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
            if self.var_remember.get():
                with open(SESSION_FILE, "w", encoding="utf-8") as f:
                    json.dump({"username": username, "remember": True}, f)
            else:
                if os.path.exists(SESSION_FILE):
                    os.remove(SESSION_FILE)
        except Exception:
            pass

    def setup_ui(self):
        """Constructs and arranges the Cyber-Blue UI backdrop and interactive login card."""
        # -------------------------------------------------------------------------
        # 1. Main Background Wallpaper Container
        # -------------------------------------------------------------------------
        self.bg_frame = tk.Frame(self.root, bg="#030b18")
        self.bg_frame.pack(fill=tk.BOTH, expand=True)
        self.bg_frame.bind("<Destroy>", self._on_destroy)

        self.lbl_bg = tk.Label(self.bg_frame, bg="#030b18")
        self.lbl_bg.place(x=0, y=0, relwidth=1, relheight=1)
        
        self.update_background_image(self.win_w, self.win_h)

        # -------------------------------------------------------------------------
        # 2. Right-Hand Glassmorphic "Welcome Back" Login Card Container
        # -------------------------------------------------------------------------
        card_w = min(400, max(320, int(self.win_w * 0.32)))
        card_h = min(500, max(420, int(self.win_h * 0.72)))
        
        self.login_card = tk.Frame(
            self.bg_frame, 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID, 
            highlightbackground="#1e3a5f", 
            highlightthickness=1
        )
        self.login_card.place(relx=0.76, rely=0.55, anchor=tk.CENTER, width=card_w, height=card_h)
        self.login_card.bind("<Destroy>", self._on_destroy)

        # Top Glowing Accent Bar on Card
        top_accent = tk.Frame(self.login_card, bg="#0084ff", height=4)
        top_accent.pack(side=tk.TOP, fill=tk.X)

        # Inner Content Frame
        inner_card = tk.Frame(self.login_card, bg="#071a35")
        inner_card.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        # Cyan Cyber User Avatar Badge
        avatar_path = os.path.join(ASSETS_DIR, "cyber_user_avatar.png")
        if os.path.exists(avatar_path):
            try:
                img_av = Image.open(avatar_path).resize((50, 50), Image.Resampling.LANCZOS)
                photo_av = ImageTk.PhotoImage(img_av, master=self.root)
                self._images.append(photo_av)
                lbl_avatar = tk.Label(inner_card, image=photo_av, bg="#071a35")
                lbl_avatar.pack(pady=(0, 4))
            except Exception:
                lbl_avatar = tk.Label(inner_card, text="👤", font=("Segoe UI", 24), fg="#38bdf8", bg="#071a35")
                lbl_avatar.pack(pady=(0, 4))
        else:
            lbl_avatar = tk.Label(inner_card, text="👤", font=("Segoe UI", 24), fg="#38bdf8", bg="#071a35")
            lbl_avatar.pack(pady=(0, 4))

        # "Welcome Back!" Title
        lbl_welcome = tk.Label(
            inner_card, 
            text="Welcome Back!", 
            font=("Segoe UI", 16, "bold"), 
            fg="#ffffff", 
            bg="#071a35"
        )
        lbl_welcome.pack(pady=(0, 2))

        # Subtitle: Registered Personnel Only Notice
        lbl_sub = tk.Label(
            inner_card, 
            text="Authorized access for registered personnel only", 
            font=("Segoe UI", 8), 
            fg="#94a3b8", 
            bg="#071a35"
        )
        lbl_sub.pack(pady=(0, 4))

        # Restricted Badge
        lbl_badge = tk.Label(
            inner_card,
            text="🔒 REGISTERED USERS ONLY",
            font=("Segoe UI", 7, "bold"),
            fg="#38bdf8",
            bg="#091f40",
            padx=8,
            pady=2,
            bd=1,
            relief=tk.SOLID
        )
        lbl_badge.pack(pady=(0, 10))

        # -------------------------------------------------------------------------
        # 3. Interactive Form Inputs
        # -------------------------------------------------------------------------
        form_frame = tk.Frame(inner_card, bg="#071a35")
        form_frame.pack(fill=tk.X)

        # Username / Email Label
        lbl_user = tk.Label(
            form_frame, 
            text="✉  Registered Username or Email *", 
            font=("Segoe UI", 9, "bold"), 
            fg="#38bdf8", 
            bg="#071a35", 
            anchor="w"
        )
        lbl_user.pack(fill=tk.X, pady=(0, 3))

        # Username Entry Box
        entry_user = tk.Entry(
            form_frame, 
            textvariable=self.var_username, 
            font=("Segoe UI", 10), 
            bg="#06152b", 
            fg="#ffffff", 
            insertbackground="#38bdf8", 
            bd=1, 
            relief=tk.SOLID,
            highlightthickness=1,
            highlightbackground="#1e3a5f",
            highlightcolor="#38bdf8"
        )
        entry_user.pack(fill=tk.X, ipady=4, pady=(0, 10))
        entry_user.bind("<Return>", lambda e: self.handle_login())

        # Password Label
        lbl_pass = tk.Label(
            form_frame, 
            text="🔒  Password *", 
            font=("Segoe UI", 9, "bold"), 
            fg="#38bdf8", 
            bg="#071a35", 
            anchor="w"
        )
        lbl_pass.pack(fill=tk.X, pady=(0, 3))

        # Password Entry Box with Show/Hide Eye Button
        pass_container = tk.Frame(form_frame, bg="#06152b", bd=1, relief=tk.SOLID, highlightthickness=1, highlightbackground="#1e3a5f", highlightcolor="#38bdf8")
        pass_container.pack(fill=tk.X, pady=(0, 8))

        self.entry_pass = tk.Entry(
            pass_container, 
            textvariable=self.var_password, 
            show="*", 
            font=("Segoe UI", 10), 
            bg="#06152b", 
            fg="#ffffff", 
            insertbackground="#38bdf8", 
            bd=0, 
            relief=tk.FLAT
        )
        self.entry_pass.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=4, padx=(6, 0))
        self.entry_pass.bind("<Return>", lambda e: self.handle_login())

        self.btn_eye = tk.Button(
            pass_container, 
            text="👁", 
            font=("Segoe UI", 9), 
            bg="#06152b", 
            fg="#94a3b8", 
            activebackground="#06152b", 
            activeforeground="#38bdf8", 
            bd=0, 
            relief=tk.FLAT, 
            cursor="hand2",
            padx=6,
            command=self.toggle_password_visibility
        )
        self.btn_eye.pack(side=tk.RIGHT, padx=4)

        # Options Row: "Remember Me" (Left) and "Forgot Password?" (Right)
        opt_frame = tk.Frame(form_frame, bg="#071a35")
        opt_frame.pack(fill=tk.X, pady=(0, 12))

        chk_remember = tk.Checkbutton(
            opt_frame, 
            text="Remember Me", 
            variable=self.var_remember, 
            font=("Segoe UI", 8), 
            fg="#cbd5e1", 
            bg="#071a35", 
            selectcolor="#06152b", 
            activebackground="#071a35", 
            activeforeground="#ffffff",
            bd=0,
            cursor="hand2"
        )
        chk_remember.pack(side=tk.LEFT)

        lbl_forgot = tk.Label(
            opt_frame, 
            text="Forgot Password?", 
            font=("Segoe UI", 8, "underline"), 
            fg="#38bdf8", 
            bg="#071a35", 
            cursor="hand2"
        )
        lbl_forgot.pack(side=tk.RIGHT)
        lbl_forgot.bind("<Button-1>", lambda e: self.open_forget_password())

        # -------------------------------------------------------------------------
        # 4. Action Button: "SIGN IN ➔"
        # -------------------------------------------------------------------------
        self.btn_login = tk.Button(
            inner_card, 
            text="SIGN IN  ➔", 
            font=("Segoe UI", 11, "bold"), 
            bg="#0084ff", 
            fg="#ffffff", 
            activebackground="#0095ff", 
            activeforeground="#ffffff", 
            cursor="hand2", 
            bd=0, 
            relief=tk.FLAT,
            padx=16, 
            pady=8,
            command=self.handle_login
        )
        self.btn_login.pack(fill=tk.X, pady=(0, 8))

        # Dynamic Hover Colors
        self.btn_login.bind("<Enter>", lambda e: self.btn_login.config(bg="#0095ff"))
        self.btn_login.bind("<Leave>", lambda e: self.btn_login.config(bg="#0084ff"))

        # Divider: "─── or ───"
        lbl_or = tk.Label(
            inner_card, 
            text="──────  or  ──────", 
            font=("Segoe UI", 8), 
            fg="#334155", 
            bg="#071a35"
        )
        lbl_or.pack(pady=(0, 6))

        # Bottom Link: "New User? Create Account"
        link_container = tk.Frame(inner_card, bg="#071a35")
        link_container.pack(pady=(0, 4))

        lbl_new_text = tk.Label(
            link_container, 
            text="New User? ", 
            font=("Segoe UI", 8), 
            fg="#94a3b8", 
            bg="#071a35"
        )
        lbl_new_text.pack(side=tk.LEFT)

        lbl_register = tk.Label(
            link_container, 
            text="Create Account", 
            font=("Segoe UI", 8, "bold", "underline"), 
            fg="#38bdf8", 
            bg="#071a35", 
            cursor="hand2"
        )
        lbl_register.pack(side=tk.LEFT)
        lbl_register.bind("<Button-1>", lambda e: self.open_register())

    def cancel_pending_resize(self):
        """Safely cancels any active debounced resize callback and clears the timer."""
        if getattr(self, "_resize_timer", None) is not None:
            try:
                if hasattr(self, "root") and self.root.winfo_exists():
                    self.root.after_cancel(self._resize_timer)
            except (tk.TclError, Exception):
                pass
            self._resize_timer = None

    def cleanup_bindings(self):
        """Unbinds resize listeners from root and cancels pending callbacks."""
        self.cancel_pending_resize()
        if hasattr(self, "_configure_bind_id") and self._configure_bind_id:
            try:
                if hasattr(self, "root") and self.root.winfo_exists():
                    self.root.unbind("<Configure>", self._configure_bind_id)
            except (tk.TclError, Exception):
                pass
            self._configure_bind_id = None

    def _on_destroy(self, event=None):
        """Cancels pending callbacks when login widgets or window are destroyed."""
        self.cancel_pending_resize()

    def update_background_image(self, target_w: int, target_h: int):
        """
        Resizes and updates the background image to match target window dimensions exactly,
        ensuring 100% of the graphic from top header to bottom footer is fully displayed.
        """
        if not hasattr(self, "root") or not hasattr(self, "lbl_bg"):
            return
        try:
            if not self.root.winfo_exists() or not self.lbl_bg.winfo_exists():
                return
        except (tk.TclError, Exception):
            return

        bg_path = os.path.join(ASSETS_DIR, "bg_login.png")
        if os.path.exists(bg_path):
            try:
                target_w = max(600, target_w)
                target_h = max(400, target_h)
                img_bg = Image.open(bg_path).resize((target_w, target_h), Image.Resampling.LANCZOS)
                photo_bg = ImageTk.PhotoImage(img_bg, master=self.root)
                self._photo_bg_ref = photo_bg  # Preserve in-memory reference
                if self.lbl_bg.winfo_exists():
                    self.lbl_bg.config(image=photo_bg)
            except (tk.TclError, Exception):
                pass

    def handle_resize(self, event):
        """Debounced handler to dynamically re-scale background when window size changes."""
        if not hasattr(self, "root") or not hasattr(self, "login_card"):
            return
        try:
            if not self.root.winfo_exists() or not self.login_card.winfo_exists():
                self.cancel_pending_resize()
                return
        except (tk.TclError, Exception):
            self.cancel_pending_resize()
            return

        if event.widget == self.root:
            cur_w = event.width
            cur_h = event.height
            # Only trigger if dimensions significantly changed (> 15px)
            if abs(cur_w - self._last_dims[0]) > 15 or abs(cur_h - self._last_dims[1]) > 15:
                self._last_dims = (cur_w, cur_h)
                self.cancel_pending_resize()
                try:
                    self._resize_timer = self.root.after(80, lambda: self._apply_resize(cur_w, cur_h))
                except (tk.TclError, Exception):
                    self._resize_timer = None

    def _apply_resize(self, new_w: int, new_h: int):
        """Applies re-scaling to background and right card."""
        self._resize_timer = None

        if not hasattr(self, "root") or not hasattr(self, "login_card"):
            return
        try:
            if not self.root.winfo_exists() or not self.login_card.winfo_exists():
                return
        except (tk.TclError, Exception):
            return

        try:
            self.update_background_image(new_w, new_h)
            card_w = min(410, max(300, int(new_w * 0.32)))
            card_h = min(510, max(400, int(new_h * 0.72)))
            if self.login_card.winfo_exists():
                self.login_card.place_configure(relx=0.76, rely=0.55, width=card_w, height=card_h)
        except (tk.TclError, Exception):
            pass

    def toggle_password_visibility(self):
        """Toggles the password field masking between plaintext and hidden."""
        if self.show_password:
            self.entry_pass.config(show="*")
            self.btn_eye.config(fg="#94a3b8")
            self.show_password = False
        else:
            self.entry_pass.config(show="")
            self.btn_eye.config(fg="#38bdf8")
            self.show_password = True

    def handle_login(self):
        """Validates credentials against SQLite database and triggers dashboard transition."""
        username = self.var_username.get().strip()
        password = self.var_password.get()
        
        if not username or not password:
            messagebox.showerror("Required Fields", "Please enter both your registered Username/Email and Password!", parent=self.root)
            return
        
        success, user_data, msg = verify_login(username, password)
        if success:
            self.save_credentials(username, password)
            if self.on_login_success:
                self.on_login_success(user_data)
            else:
                self.open_dashboard(user_data)
        else:
            if "not registered" in msg.lower() or "not found" in msg.lower():
                if messagebox.askyesno("Access Denied - Unregistered User", f"{msg}\n\nWould you like to register a new administrator account now?", parent=self.root):
                    self.open_register()
            else:
                messagebox.showerror("Access Denied", msg, parent=self.root)

    def open_register(self):
        """Opens user registration window as modal dialog."""
        reg_win = tk.Toplevel(self.root)
        RegisterWindow(reg_win, on_login_click=lambda: reg_win.destroy())

    def open_forget_password(self):
        """Opens password recovery window."""
        self.cancel_pending_resize()
        ForgetPasswordWindow(self.root)

    def open_dashboard(self, user_data):
        """Transitions into MainDashboard cleanly on the single root window."""
        self.cleanup_bindings()
        from modules.dashboard import MainDashboard
        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except (tk.TclError, Exception):
                pass
        MainDashboard(self.root, user_data)


if __name__ == "__main__":
    root = tk.Tk()
    app = LoginWindow(root)
    root.mainloop()
