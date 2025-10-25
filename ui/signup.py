import re
import tkinter as tk
from tkinter import ttk, messagebox
import bcrypt
from app import App

USERNAME_RE = re.compile(r"^[A-Za-z0-9]{1,20}$")
NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ'’.\- ]{1,40}$")

class SignupFrame(ttk.Frame):
    """
    Separate signup page for full user details.

    Fields: first_name, last_name, email, username, password, display_name
    """

    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app

        # form variables
        self.first_name_var = tk.StringVar()
        self.last_name_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.display_name_var = tk.StringVar()

        # layout
        title = ttk.Label(self, text="Create Account", font=("Segoe UI", 16, "bold"))
        title.pack(pady=12)

        form = ttk.Frame(self)
        form.pack(padx=20, pady=10, anchor="n")

        # first / last
        ttk.Label(form, text="First name:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.first_name_var).grid(row=0, column=1, pady=4)

        ttk.Label(form, text="Last name:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.last_name_var).grid(row=1, column=1, pady=4)

        # email
        ttk.Label(form, text="Email:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.email_var).grid(row=2, column=1, pady=4)

        # display / username
        ttk.Label(form, text="Display name:").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.display_name_var).grid(row=3, column=1, pady=4)

        ttk.Label(form, text="Username:").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.username_var).grid(row=4, column=1, pady=4)

        # password
        ttk.Label(form, text="Password:").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.password_var, show="*").grid(row=5, column=1, pady=4)

        # buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Create Account", command=self.create_account).grid(row=0, column=0, padx=6)
        ttk.Button(btn_frame, text="Back to Login", command=self.go_back).grid(row=0, column=1, padx=6)

    def _validate_inputs(self, first, last, email, username, password, display):
        # Required fields 
        if not (username and password and email):
            messagebox.showwarning("Missing Info", "Please fill out username, password and email.")
            return False
        
        # First name / last name: NULL or 1–40 letters, spaces, hyphens, apostrophes, periods
        if not NAME_RE.fullmatch(first): # first name
            messagebox.showwarning("Invalid First Name", "First name must be 1–40 letters, spaces, or allowed special characters (- . ').")
            return False
        
        if not NAME_RE.fullmatch(last): # last name
            messagebox.showwarning("Invalid Last Name", "Last name must be 1–40 letters, spaces, or allowed special characters (- . ').")
            return False

        # Username: ^[A-Za-z0-9]{1,20}$
        if not USERNAME_RE.fullmatch(username):
            messagebox.showwarning("Invalid Username", "Username must be 1–20 letters/numbers only (A–Z, a–z, 0–9).")
            return False

        # Display name: NULL or 1–50 chars. If empty, we set it to username.
        if display and not (1 <= len(display) <= 50):
            messagebox.showwarning("Invalid Display Name", "Display name must be 1–50 characters.")
            return False

        # Password: raw password length 8–30 
        if not (8 <= len(password) <= 30):
            messagebox.showwarning("Invalid Password Length", "Password must be between 8 and 30 characters.")
            return False

        return True

    def create_account(self):
        first = self.first_name_var.get().strip()
        last = self.last_name_var.get().strip()
        email = self.email_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        display = (self.display_name_var.get().strip() or username)

        if not self._validate_inputs(first, last, email, username, password, display):
            return

        try:
            # Hash (bcrypt output is 60 chars and satisfies your DB password length check)
            hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            # Try to insert into USER table
            # sql = 'INSERT INTO "USER" (first_name, last_name, email, username, password, display_name) VALUES (%s, %s, %s, %s, %s, %s)'

            sql = ('INSERT INTO "USER" ' '(first_name, last_name, email, username, password, display_name, creation_date)' 'VALUES (%s, %s, %s, %s, %s, %s, NOW())')

            self.app.exec_and_commit(sql, (first, last, email, username, hashed_pw, display), )

            self.clear_form()  # clear after successful signup

            # log user in and go to dashboard
            self.app.session.username = username
            self.app.session.display_name = display
            messagebox.showinfo("Account Created", f"Welcome, {display}! You are now signed in.")
            self.app.safe_show("Dashboard")

        except Exception as e:
            # inspect e for unique violations to show nicer messages
            messagebox.showerror("Signup Failed", f"Could not create account:\n{e}")

    def go_back(self):
        try:
            self.app.show_frame("Login")
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Could not return to login page:\n{e}")

    def clear_form(self):
        self.first_name_var.set("")
        self.last_name_var.set("")
        self.email_var.set("")
        self.username_var.set("")
        self.password_var.set("")
        self.display_name_var.set("")
