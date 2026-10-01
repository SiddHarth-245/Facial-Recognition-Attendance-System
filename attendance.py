"""
========================================================================================
Attendance Records Management & Data Synchronization Module
========================================================================================
Module: attendance.py
Author: Santosh Sah (Lead Developer - Attendance Operations & CSV Data Pipelines)
Mentorship: Mr. Rakesh Kumar Rai (KIIT University)

Role & Architectural Purpose:
-----------------------------
This module provides the user interface and data synchronization controller for managing,
viewing, updating, importing, and exporting student attendance logs. It implements a dual-layer
persistence model bridging relational SQLite transactional records (`attendance` table) with
universal flat-file spreadsheets (`attendance_records/attendance.csv`).

Key System Features:
-------------------
1. Next-Gen FaceAttend Cyber-Blue Enterprise Interface:
   - High-DPI Per-Monitor Scaled UI with Midnight Cyber palette (#030b18 / #071a35).
   - Glassmorphic form panels with cyan (#38bdf8) active highlights and crisp typography.
   - Custom Cyber-Themed Treeview table with high-contrast alternating rows.
2. Dual-Persistence Synchronization:
   - Reads records seamlessly from CSV or SQLite fallback on application startup.
   - Synchronizes manual updates across both SQLite and CSV flat-files atomically.
3. Bidirectional CSV Import & Export:
   - File Import: Parses external CSV attendance logs, validates columns, and stores to database.
   - File Export: Formats records with ISO timestamps (`attendance_export_YYYYMMDD_HHMMSS.csv`).
4. Interactive Form & Treeview Controller:
   - Populates editing fields upon row selection in the Treeview table.
========================================================================================
"""

import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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

# Database CRUD helpers for attendance records
from database.db_manager import (
    fetch_all_attendance,
    log_attendance,
    update_attendance_record,
)

# Filesystem directories and paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance_records")

# Ensure attendance directory exists
os.makedirs(ATTENDANCE_DIR, exist_ok=True)
DEFAULT_CSV = os.path.join(ATTENDANCE_DIR, "attendance.csv")


class AttendanceManagementSystem:
    """
    Attendance Management System GUI and Data Handler.
    
    Provides the administrative interface for viewing daily biometric logs,
    modifying attendance statuses, and executing CSV file import/export tasks.
    """

    def __init__(self, root: tk.Tk):
        """
        Initializes the Attendance Management window, responsive geometry, state variables,
        and GUI components.

        Parameters:
        -----------
        root : tk.Tk or tk.Toplevel
            Parent Tkinter window instance.
        """
        self.root = root
        self.root.title("FaceAttend - Attendance Management & CSV Synchronization")
        
        # Calculate dynamic screen dimensions (96% width x 92% height)
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
        # Form State Variables (Bound to Entry widgets and Combobox)
        # -------------------------------------------------------------------------
        self.var_attendance_id = tk.StringVar()
        self.var_employee_id = tk.StringVar()
        self.var_roll = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_dep = tk.StringVar()
        self.var_time = tk.StringVar()
        self.var_date = tk.StringVar()
        self.var_status = tk.StringVar(value="Present")
        
        # Image cache and in-memory table records
        self._images = []
        self.current_csv_data = []
        
        # Apply modern Cyber-Blue ttk styles
        self._apply_theme_styles()
        
        # Construct UI and load existing attendance records
        self.setup_ui()
        self.update_clock()
        self.load_attendance_from_csv()

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
        """Constructs the visual layout of the Attendance Management window."""
        # -------------------------------------------------------------------------
        # 1. Top Photographic Header Banner
        # -------------------------------------------------------------------------
        header_path = os.path.join(ASSETS_DIR, "attendance_header.png")
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
            text="BIOMETRIC ATTENDANCE RECORDS & DATA PIPELINE", 
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
        # LEFT SECTION: Attendance Edit Form Container
        # =========================================================================
        left_box = tk.LabelFrame(
            body_frame, 
            text=" 📊 Attendance Entry Details ", 
            font=("Segoe UI", 10, "bold"), 
            fg="#38bdf8", 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID
        )
        left_box.place(relx=0.0, rely=0.0, relwidth=0.44, relheight=1.0)

        # Form Input Fields Frame
        form_frame = tk.Frame(left_box, bg="#091f40", bd=1, relief=tk.SOLID)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 8))

        lbl_style = {"font": ("Segoe UI", 9, "bold"), "bg": "#091f40", "fg": "#94a3b8"}
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

        # Row 1: Employee/Attendance ID & Roll
        tk.Label(form_frame, text="Attendance ID:", **lbl_style).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        tk.Entry(form_frame, textvariable=self.var_employee_id, width=16, **entry_opts).grid(row=0, column=1, padx=6, pady=10)

        tk.Label(form_frame, text="Roll No:", **lbl_style).grid(row=0, column=2, sticky="w", padx=10, pady=10)
        tk.Entry(form_frame, textvariable=self.var_roll, width=16, **entry_opts).grid(row=0, column=3, padx=6, pady=10)

        # Row 2: Student Name & Department
        tk.Label(form_frame, text="Full Name:", **lbl_style).grid(row=1, column=0, sticky="w", padx=10, pady=10)
        tk.Entry(form_frame, textvariable=self.var_name, width=16, **entry_opts).grid(row=1, column=1, padx=6, pady=10)

        tk.Label(form_frame, text="Department:", **lbl_style).grid(row=1, column=2, sticky="w", padx=10, pady=10)
        tk.Entry(form_frame, textvariable=self.var_dep, width=16, **entry_opts).grid(row=1, column=3, padx=6, pady=10)

        # Row 3: Timestamp & Date
        tk.Label(form_frame, text="Logged Time:", **lbl_style).grid(row=2, column=0, sticky="w", padx=10, pady=10)
        tk.Entry(form_frame, textvariable=self.var_time, width=16, **entry_opts).grid(row=2, column=1, padx=6, pady=10)

        tk.Label(form_frame, text="Logged Date:", **lbl_style).grid(row=2, column=2, sticky="w", padx=10, pady=10)
        tk.Entry(form_frame, textvariable=self.var_date, width=16, **entry_opts).grid(row=2, column=3, padx=6, pady=10)

        # Row 4: Attendance Status Dropdown
        tk.Label(form_frame, text="Status:", **lbl_style).grid(row=3, column=0, sticky="w", padx=10, pady=10)
        combo_status = ttk.Combobox(
            form_frame, textvariable=self.var_status, font=("Segoe UI", 9), state="readonly", width=14,
            values=["Present", "Absent"]
        )
        combo_status.grid(row=3, column=1, padx=6, pady=10)

        # -------------------------------------------------------------------------
        # Action Buttons Bar: Import CSV, Export CSV, Update, Reset
        # -------------------------------------------------------------------------
        btn_bar = tk.Frame(left_box, bg="#071a35")
        btn_bar.pack(fill=tk.X, padx=10, pady=(6, 12))

        btn_base = {
            "font": ("Segoe UI", 9, "bold"), 
            "bd": 0, 
            "relief": tk.FLAT, 
            "cursor": "hand2"
        }

        tk.Button(btn_bar, text="📥 Import CSV", bg="#0084ff", fg="#ffffff", activebackground="#006cd4", activeforeground="#ffffff", command=self.handle_import_csv, **btn_base).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3, ipady=6)
        tk.Button(btn_bar, text="📤 Export CSV", bg="#10b981", fg="#ffffff", activebackground="#059669", activeforeground="#ffffff", command=self.handle_export_csv, **btn_base).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3, ipady=6)
        tk.Button(btn_bar, text="🔄 Update", bg="#0284c7", fg="#ffffff", activebackground="#0369a1", activeforeground="#ffffff", command=self.handle_update, **btn_base).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3, ipady=6)
        tk.Button(btn_bar, text="↺ Reset", bg="#334155", fg="#ffffff", activebackground="#475569", activeforeground="#ffffff", command=self.handle_reset, **btn_base).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3, ipady=6)

        # =========================================================================
        # RIGHT SECTION: Attendance Records Table
        # =========================================================================
        right_box = tk.LabelFrame(
            body_frame, 
            text=" 📋 Daily Attendance Log Records ", 
            font=("Segoe UI", 10, "bold"), 
            fg="#38bdf8", 
            bg="#071a35", 
            bd=1, 
            relief=tk.SOLID
        )
        right_box.place(relx=0.45, rely=0.0, relwidth=0.55, relheight=1.0)

        # Table Container with 2-Dimensional Scrollbars
        table_container = tk.Frame(right_box, bg="#071a35")
        table_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scroll_x = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL)
        scroll_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL, style="Cyber.Vertical.TScrollbar")

        columns = ("id", "roll", "name", "dep", "time", "date", "attendance")
        self.attendance_table = ttk.Treeview(
            table_container, 
            columns=columns, 
            xscrollcommand=scroll_x.set, 
            yscrollcommand=scroll_y.set,
            style="Cyber.Treeview"
        )

        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.attendance_table.xview)
        scroll_y.config(command=self.attendance_table.yview)

        # Column Header Definitions
        headers = {
            "id": "Attendance ID", "roll": "Roll No", "name": "Name",
            "dep": "Department", "time": "Logged Time", "date": "Date", "attendance": "Status"
        }
        for col, label in headers.items():
            self.attendance_table.heading(col, text=label)
            self.attendance_table.column(col, width=100, anchor=tk.CENTER)

        self.attendance_table["show"] = "headings"
        self.attendance_table.pack(fill=tk.BOTH, expand=True)
        self.attendance_table.bind("<ButtonRelease-1>", self.handle_row_selection)

    def update_clock(self):
        """Updates digital clock label every 1000 ms."""
        now = datetime.now()
        time_str = now.strftime("%I:%M:%S %p")
        try:
            self.lbl_clock.config(text=time_str)
        except Exception:
            pass
        self.root.after(1000, self.update_clock)

    def load_attendance_from_csv(self):
        """Loads records from `attendance_records/attendance.csv` into Treeview table."""
        self.attendance_table.delete(*self.attendance_table.get_children())
        self.current_csv_data = []

        if os.path.exists(DEFAULT_CSV):
            try:
                with open(DEFAULT_CSV, "r", newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    for row in reader:
                        if row:
                            self.current_csv_data.append(row)
                            self.attendance_table.insert("", tk.END, values=row)
            except Exception:
                pass
        else:
            rows = fetch_all_attendance()
            for r in rows:
                row_val = [r[0], r[2], r[3], r[4], r[5], r[6], r[7]]
                self.current_csv_data.append(row_val)
                self.attendance_table.insert("", tk.END, values=row_val)

    def handle_row_selection(self, event):
        """Populates the left input form with values from the selected table row."""
        item = self.attendance_table.focus()
        row = self.attendance_table.item(item).get("values")
        if row:
            self.var_attendance_id.set(row[0])
            self.var_employee_id.set(row[0])
            self.var_roll.set(row[1])
            self.var_name.set(row[2])
            self.var_dep.set(row[3])
            self.var_time.set(row[4])
            self.var_date.set(row[5])
            self.var_status.set(row[6])

    def handle_reset(self):
        """Clears all input fields and resets status to 'Present'."""
        self.var_attendance_id.set("")
        self.var_employee_id.set("")
        self.var_roll.set("")
        self.var_name.set("")
        self.var_dep.set("")
        self.var_time.set("")
        self.var_date.set("")
        self.var_status.set("Present")

    def handle_update(self):
        """Updates the attendance status ('Present'/'Absent') in both SQLite and CSV records."""
        att_id = self.var_attendance_id.get().strip()
        status = self.var_status.get().strip()
        if not att_id:
            messagebox.showerror("Error", "Please select a record from the table to update!", parent=self.root)
            return

        try:
            update_attendance_record(int(att_id), status)
            updated_data = []
            if os.path.exists(DEFAULT_CSV):
                with open(DEFAULT_CSV, "r", newline="", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    for row in reader:
                        if row and str(row[0]) == str(att_id):
                            row[6] = status
                        updated_data.append(row)

                with open(DEFAULT_CSV, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if headers:
                        writer.writerow(headers)
                    writer.writerows(updated_data)

            self.load_attendance_from_csv()
            messagebox.showinfo("Success", "Attendance record updated successfully!", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def handle_import_csv(self):
        """Prompts user to select an external CSV file, parses rows, and writes them to SQLite."""
        file_path = filedialog.askopenfilename(
            initialdir=ATTENDANCE_DIR,
            title="Open Attendance CSV File",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*")),
            parent=self.root
        )
        if not file_path:
            return

        try:
            count = 0
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                for row in reader:
                    if len(row) >= 7:
                        log_attendance(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
                        count += 1

            self.load_attendance_from_csv()
            messagebox.showinfo("Success", f"Imported {count} record(s) successfully!", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import CSV: {e}", parent=self.root)

    def handle_export_csv(self):
        """Exports the current attendance table dataset into a user-specified CSV spreadsheet."""
        if not self.current_csv_data:
            messagebox.showwarning("Warning", "No attendance records to export.", parent=self.root)
            return

        file_path = filedialog.asksaveasfilename(
            initialdir=ATTENDANCE_DIR,
            initialfile=f"attendance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            defaultextension=".csv",
            filetypes=(("CSV file (*.csv)", "*.csv"), ("All Files", "*.*")),
            parent=self.root
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Attendance ID", "Roll", "Name", "Department", "Time", "Date", "Attendance"])
                for row in self.current_csv_data:
                    writer.writerow(row)

            messagebox.showinfo("Success", f"Attendance data successfully exported to:\n{file_path}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export CSV: {e}", parent=self.root)


if __name__ == "__main__":
    root = tk.Tk()
    app = AttendanceManagementSystem(root)
    root.mainloop()
