import tkinter as tk
from tkinter import ttk, messagebox
import bcrypt
import datetime


class LoginFrame(ttk.Frame):
    # Login / Signup page.

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        # Layout
        ttk.Label(self, text="🎵 Music Information Database", font=("Arial", 18, "bold")).pack(pady=20)
        ttk.Label(self, text="Username:").pack()
        ttk.Entry(self, textvariable=self.username_var).pack(pady=5)

        ttk.Label(self, text="Password:").pack()
        ttk.Entry(self, textvariable=self.password_var, show="*").pack(pady=5)

        ttk.Button(self, text="Login", command=self.login_user).pack(pady=10)
        ttk.Button(self, text="Sign Up", command=self.signup_user).pack()

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
                now = datetime.datetime.now()
                self.app.exec_and_commit('UPDATE "USER" SET last_accessed = %s WHERE username = %s', (now, username))

                self.app.safe_show("Dashboard")
            else:
                messagebox.showerror("Login Failed", "Invalid password.")
        except Exception as e:
            messagebox.showerror("Error", f"Database error:\n{e}")

    #  Signup logic 
    def signup_user(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showwarning("Missing Info", "Please fill out all fields.")
            return

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        now = datetime.datetime.now()

        try:
            self.app.exec_and_commit(
                'INSERT INTO "USER" (username, password, creation_date) VALUES (%s, %s, %s)',
                (username, hashed_pw, now)
            )
            messagebox.showinfo("Account Created", "Your account has been created. You can now log in.")
        except Exception as e:
            messagebox.showerror("Signup Failed", f"Could not create account:\n{e}")