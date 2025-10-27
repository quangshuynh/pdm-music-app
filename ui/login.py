import tkinter as tk
from tkinter import ttk, messagebox
import bcrypt
import datetime
from app import App


class LoginFrame(ttk.Frame):
    # Login 

    def __init__(self, parent, app:App):
        super().__init__(parent)
        self.app = app

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        # Layout
        ttk.Label(self, text="Toe Jam", font=("Arial", 18, "bold")).pack(pady=20)
        ttk.Label(self, text="Username:").pack()
        user_entry = ttk.Entry(self, textvariable=self.username_var)
        user_entry.bind('<Return>', self.login_user_entry)
        user_entry.pack(pady=5)

        ttk.Label(self, text="Password:").pack()
        password_entry = ttk.Entry(self, textvariable=self.password_var, show="*")
        password_entry.bind('<Return>', self.login_user_entry)
        password_entry.pack(pady=5)

        ttk.Button(self, text="Login", command=self.login_user).pack(pady=10)
        ttk.Button(self, text="Sign Up", command=self.go_to_signup).pack()

    def login_user_entry(self, event):
        self.login_user()

    #  Login logic 
    def login_user(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showwarning("Missing Info", "Please enter username and password.")
            return

        try:
            with self.app.cursor() as cur:
                cur.execute('SELECT password FROM "USER" WHERE username = %s', (username,))
                row = cur.fetchone()

            if not row:
                messagebox.showerror("Login Failed", "User not found.")
                return

            stored_pw = row[0].encode("utf-8")
            if bcrypt.checkpw(password.encode("utf-8"), stored_pw):
                self.app.session.username = username
                self.app.session.display_name = username
                messagebox.showinfo("Success", f"Welcome back, {username}!")

                # Update last accessed
                self.app.exec_and_commit('UPDATE "USER" SET last_accessed = NOW() WHERE username = %s', (username,))

                self.app.safe_show("Dashboard")
            else:
                messagebox.showerror("Login Failed", "Invalid password.")
        except Exception as e:
            messagebox.showerror("Error", f"Database error:\n{e}")

    def go_to_signup(self):
        """Navigate to the separate Signup page."""
        try:
            self.app.show_frame("Signup")
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Could not open signup page:\n{e}")