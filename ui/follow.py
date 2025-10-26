import tkinter as tk
from tkinter import ttk, messagebox

class FollowFrame(ttk.Frame):
    """ View, follow, and unfollow other users. """

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        ttk.Label(self, text="Follow / Unfollow Users", font=("Arial", 16, "bold")).pack(pady=10)

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=6)

        ttk.Label(bar, text="Username:").pack(side="left")
        self.target_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.target_var, width=24).pack(side="left", padx=(6, 10))

        ttk.Button(bar, text="Follow", command=self.on_follow).pack(side="left", padx=5)
        ttk.Button(bar, text="Unfollow", command=self.on_unfollow).pack(side="left", padx=5)
        ttk.Button(bar, text="Back", command=lambda: app.safe_show("Dashboard")).pack(side="right")

        self.status = ttk.Label(self, text="")
        self.status.pack(fill="x", padx=10, pady=5)

    # ---- UI Helpers ----
    def on_show(self):
        if not self.app.session.username:
            messagebox.showwarning("Not Logged in", "Please log in to view this page.")
            self.app.safe_show("Login")

    def _user_exists(self, username: str) -> bool:
        """Check if a user exists in the USER table."""
        sql = 'SELECT 1 FROM "USER" WHERE username = %s LIMIT 1'
        with self.app.cursor() as cur:
            cur.execute(sql, (username,))
            return cur.fetchone() is not None

    def on_follow(self):
        me = self.app.session.username
        target = self.target_var.get().strip()

        if not target:
            messagebox.showinfo("Missing", "Enter a username to follow.")
            return
        if target == me:
            messagebox.showinfo("Invalid", "You cannot follow yourself.")
            return
        if not self._user_exists(target):
            messagebox.showinfo("Not Found", f"User '{target}' does not exist.")
            return

        sql = """
            INSERT INTO user_follow (follower_user_id, followed_user_id)
            VALUES (%s, %s)
            ON CONFLICT (follower_user_id, followed_user_id) DO NOTHING
        """
        try:
            with self.app.cursor() as cur:
                cur.execute(sql, (me, target))
                added = cur.rowcount
            self.app.conn.commit()

            if added:
                self.status.config(text=f"Now following {target}.")
                messagebox.showinfo("Followed", f"You are now following {target}.")
            else:
                self.status.config(text=f"Already following {target}.")
                messagebox.showinfo("Already Following", f"You already follow {target}.")
        except Exception as e:
            messagebox.showerror("Follow Failed", f"Could not follow user:\n{e}")

    def on_unfollow(self):
        me = self.app.session.username
        target = self.target_var.get().strip()
        if not target:
            messagebox.showinfo("Missing", "Enter a username to unfollow.")
            return

        sql = "DELETE FROM user_follow WHERE follower_user_id = %s AND followed_user_id = %s"
        try:
            with self.app.cursor() as cur:
                cur.execute(sql, (me, target))
                removed = cur.rowcount
            self.app.conn.commit()

            if removed:
                self.status.config(text=f"Unfollowed {target}.")
                messagebox.showinfo("Unfollowed", f"You unfollowed {target}.")
            else:
                self.status.config(text=f"Not following {target}.")
                messagebox.showinfo("Not Following", f"You were not following {target}.")
        except Exception as e:
            messagebox.showerror("Unfollow Failed", f"Could not unfollow user:\n{e}")
