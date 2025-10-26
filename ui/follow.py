import tkinter as tk
from tkinter import ttk, messagebox

class FollowFrame(ttk.Frame):
    """ View, follow, and unfollow other users. """
    COLS = [
        ("followed_user_id", "Following", 200),
    ]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        ttk.Label(self, text="Followers", font=("Arial", 16, "bold")).pack(pady=10)

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=6)

        ttk.Label(bar, text="Username:").pack(side="left")
        self.target_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.target_var, width=24).pack(side="left", padx=(6, 10))

        ttk.Button(bar, text="Follow", command=self.on_follow).pack(side="left", padx=5)
        ttk.Button(bar, text="Unfollow", command=self.on_unfollow).pack(side="left", padx=5)
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left", padx=5)
        ttk.Button(bar, text="Back", command=lambda: app.safe_show("Dashboard")).pack(side="right")

        # ---- Tree View
        ttk.Label(self, text="You are following:").pack(anchor="w", padx=10)
        self.tree = ttk.Treeview(self, show="headings", height=10)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self._setup_columns()


        self.status = ttk.Label(self, text="")
        self.status.pack(fill="x", padx=10, pady=5)

    # ---- Data Loading ----
    def list_following(self):
        sql = """
            SELECT followed_user_id
            FROM user_follow
            WHERE follower_user_id = %s
            ORDER BY followed_user_id ASC
        """
        with self.app.cursor() as cur:
            cur.execute(sql, (self.app.session.username,))
            rows = cur.fetchall() or []
        return [r[0] for r in rows]
    
    def refresh(self):
        try:
            following = self.list_following()
            self.tree.delete(*self.tree.get_children())
            for user in following:
                self.tree.insert("", "end", values=(user,))
            self.status.config(text = f"Following {len(following)} user(s).")
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load following list:\n{e}")
    # ---- UI Helpers ----
    def on_show(self):
        if not self.app.session.username:
            messagebox.showwarning("Not Logged in", "Please log in to view this page.")
            self.app.safe_show("Login")
        else:
            self.refresh()
        
    def _setup_columns(self):
        self.tree["columns"] = [c[0] for c in self.COLS]
        for col_id, header, width in self.COLS:
            self.tree.heading(col_id, text=header)
            anchor = "w" if col_id == "name" else "center"
            self.tree.column(col_id, width=width, anchor=anchor, stretch=False)


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
            self.refresh()
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
            self.refresh()
        except Exception as e:
            messagebox.showerror("Unfollow Failed", f"Could not unfollow user:\n{e}")
