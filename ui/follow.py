import tkinter as tk
from tkinter import ttk, messagebox

class FollowFrame(ttk.Frame):
    """ View, follow, and unfollow other users. """
    COLS = [
        ("followed_user_id", "User", 200),
        ("followers", "Followers", 100),
        ("following", "Following", 100),
    ]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        ttk.Label(self, text="Following", font=("Arial", 16, "bold")).pack(pady=10)

        
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=6)

        ttk.Label(bar, text="Username:").pack(side="left")
        self.target_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.target_var, width=24).pack(side="left", padx=(6, 10))

        # Buttons
        ttk.Button(bar, text="Follow", command=self.on_follow).pack(side="left", padx=5)
        ttk.Button(bar, text="Unfollow", command=self.on_unfollow).pack(side="left", padx=5)
        ttk.Button(bar, text="View Stats", command=self.on_view_stats).pack(side="left", padx=5)
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left", padx=5)
        
        # Search widgets
        ttk.Label(bar, text="Search:").pack(side="left", padx=(0,6))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(bar, textvariable=self.search_var, width=32)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<Return>", lambda e: self.apply_search())

        ttk.Button(bar, text="Search", command=self.apply_search).pack(side="left", padx=(8,0))
        ttk.Button(bar, text="Clear", command=self.clear_search).pack(side="left", padx=(6,12))

        ttk.Button(bar, text="Back", command=lambda: app.safe_show("Dashboard")).pack(side="right")

        # ---- Tree View
        
        self.tree_label = ttk.Label(self, text="You are following:")
        self.tree_label.pack(anchor="w", padx=10)
        
        self.tree = ttk.Treeview(self, show="headings", height=10)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self._setup_columns()

        self.tree.bind("<Double-1>", self._on_double_click)

        self.status = ttk.Label(self, text="")
        self.status.pack(fill="x", padx=10, pady=5)

    # ---- Stats (modal) ----
    def _get_selected_username(self):
        selected = self.tree.selection()
        if not selected:
            return None
        item_id = selected[0]
        values = self.tree.item(item_id, "values")
        if not values:
            return None
        return values[0]

    def on_view_stats(self):
        username = (self.target_var.get() or "").strip() or self._get_selected_username()
        if not username:
            messagebox.showinfo("Select User", "Enter or select a user to view stats.")
            return
        if not self._user_exists(username):
            messagebox.showinfo("Not Found", f"User '{username}' does not exist.")
            return
        try:
            data = self._fetch_user_stats(username)
            self._open_stats_modal(username, data)
        except Exception as e:
            messagebox.showerror("Stats Error", f"Could not load stats for '{username}':\n{e}")

    def _fetch_user_stats(self, username: str):
        sql_counts = {
            "collections": (
                "SELECT COUNT(*) FROM collection WHERE creator_username = %s",
                (username,),
            ),
            "followers": (
                "SELECT COUNT(*) FROM user_follow WHERE followed_user_id = %s",
                (username,),
            ),
            "following": (
                "SELECT COUNT(*) FROM user_follow WHERE follower_user_id = %s",
                (username,),
            ),
        }

        out = {"collections": 0, "followers": 0, "following": 0, "top_artists": []}
        with self.app.cursor() as cur:
            for key, (q, params) in sql_counts.items():
                cur.execute(q, params)
                (cnt,) = cur.fetchone()
                out[key] = int(cnt or 0)

            cur.execute(
                """
                SELECT artist_label, listens
                FROM (
                    SELECT
                        CASE
                            WHEN g.group_id IS NOT NULL THEN g.group_id::text
                            ELSE 'song:' || s.song_id::text
                        END AS artist_key,
                        CASE
                            WHEN g.group_id IS NOT NULL AND g.group_name IS NOT NULL THEN g.group_name
                            WHEN g.group_id IS NOT NULL AND g.group_name IS NULL THEN 'Unknown (group ' || g.group_id::text || ')'
                            ELSE 'Unknown Artist: ' || COALESCE(s.title, s.song_id::text)
                        END AS artist_label,
                        COUNT(*) AS listens
                    FROM listen li
                    JOIN song s ON s.song_id = li.song_id
                    LEFT JOIN "GROUP" g ON g.group_id = s.group_id
                    WHERE li.listener_username = %s
                    GROUP BY artist_key, artist_label
                ) t
                ORDER BY listens DESC, LOWER(artist_label) ASC
                LIMIT 10
                """,
                (username,),
            )
            out["top_artists"] = cur.fetchall() or []

        return out

    def _open_stats_modal(self, username: str, data):
        win = tk.Toplevel(self)
        win.title(f"Stats: {username}")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        header = ttk.Label(win, text=f"User Stats for {username}", font=("Segoe UI", 14, "bold"))
        header.pack(padx=12, pady=(10, 6))

        counts = ttk.Frame(win)
        counts.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Label(counts, text=f"Collections: {data.get('collections', 0)}").pack(anchor="w")
        ttk.Label(counts, text=f"Followers: {data.get('followers', 0)}").pack(anchor="w")
        ttk.Label(counts, text=f"Following: {data.get('following', 0)}").pack(anchor="w")

        box = ttk.LabelFrame(win, text="Top 10 Artists (by listens)")
        box.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        tv = ttk.Treeview(box, show="headings", height=10)
        tv.pack(fill="both", expand=True, padx=4, pady=6)
        tv["columns"] = ["artist", "listens"]
        tv.heading("artist", text="Artist")
        tv.heading("listens", text="Listens")
        tv.column("artist", width=320, anchor="w", stretch=True)
        tv.column("listens", width=100, anchor="center", stretch=False)

        for artist, listens in data.get("top_artists", []):
            tv.insert("", "end", values=(artist or "Unknown", int(listens or 0)))

        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right")

    # ---- Data Loading ----
    def _list_following(self, email_filter=None):
        me = self.app.session.username

        if not email_filter:
            sql = """
                SELECT
                    uf.followed_user_id AS username,
                    COUNT(DISTINCT f2.follower_user_id) AS followers,
                    COUNT(DISTINCT f3.followed_user_id) AS following,
                    TRUE AS is_followed
                FROM user_follow uf
                LEFT JOIN user_follow f2 ON f2.followed_user_id = uf.followed_user_id
                LEFT JOIN user_follow f3 ON f3.follower_user_id = uf.followed_user_id
                WHERE uf.follower_user_id = %s
                GROUP BY uf.followed_user_id
                ORDER BY uf.followed_user_id ASC;
            """
            params = [me]

        # if searching by email
        else:
            sql = """
                SELECT
                    u.username,
                    COUNT(DISTINCT f2.follower_user_id) AS followers,
                    COUNT(DISTINCT f3.followed_user_id) AS following,
                    CASE WHEN uf.follower_user_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_followed
                FROM "USER" u
                LEFT JOIN user_follow uf
                    ON uf.followed_user_id = u.username
                    AND uf.follower_user_id = %s
                LEFT JOIN user_follow f2 ON f2.followed_user_id = u.username
                LEFT JOIN user_follow f3 ON f3.follower_user_id = u.username
                WHERE u.email ILIKE %s
                GROUP BY u.username, uf.follower_user_id
                ORDER BY u.username ASC;
            """
            params = [me, f"%{email_filter}%"]

        with self.app.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


    def refresh(self):
        try:
            term = self.search_var.get().strip()
            rows = self._list_following(term if term else None)

            self.tree.delete(*self.tree.get_children())
            for username, followers, following, _ in rows:
                self.tree.insert("", "end", values=(username, followers, following))

            if not term:
                self.status.config(text=f"Following {len(rows)} user(s).")
                self.tree_label.config(text="You are following:")
            else:
                self.status.config(text=f"Search result: {len(rows)} user(s) found.")
                self.tree_label.config(text="Search results:")

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
        
    def _on_double_click(self, event):
        """ if user is double clicked, put that name in USER entry"""
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        values = self.tree.item(item_id, "values")
        if not values:
            return
        usernmae = values[0]
        self.target_var.set(usernmae)

    # ---- Search

    def apply_search(self):
        self.refresh()

    def clear_search(self):
        self.search_var.set("")
        self.refresh()

    # ---- Follow/ Unfollow
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
