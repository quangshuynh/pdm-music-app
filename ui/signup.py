import tkinter as tk
from tkinter import ttk, messagebox
import bcrypt
import datetime
from app import App


class SignupFrame(ttk.Frame):
    """Separate signup page for full user details.

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

        # dsplauy / username
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

    def create_account(self):
        first = self.first_name_var.get().strip()
        last = self.last_name_var.get().strip()
        email = self.email_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        display = self.display_name_var.get().strip() or username

        if not (username and password and email):
            messagebox.showwarning("Missing Info", "Please fill out username, password and email.")
            return

        try:
            hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            now = datetime.datetime.now()

            # Try to insert into USER table. Column names assumed to exist in DB schema.
            self.app.exec_and_commit(
                'INSERT INTO "USER" (first_name, last_name, email, username, password, display_name, creation_date) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (first, last, email, username, hashed_pw, display, now),
            )

            # log user in and go to dashboard
            self.app.session.username = username
            self.app.session.display_name = display
            messagebox.showinfo("Account Created", f"Welcome, {display}! You are now signed in.")
            self.app.safe_show("Dashboard")
        except Exception as e:
            messagebox.showerror("Signup Failed", f"Could not create account:\n{e}")

    def go_back(self):
        try:
            self.app.show_frame("Login")
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Could not return to login page:\n{e}")
