import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple, Optional
from app import App


class RecommendationsFrame(ttk.Frame):
    """
    Recommendation & popularity page.

    Provides:
    – Top 50 most popular songs in the last 30 days (rolling)
    – Top 50 most popular songs among users followed by the current user
    – Top 5 most popular genres of the month (calendar month)
    – Song recommendations based on:
        * your play history (e.g. genre, artist)
        * play history of similar users

    All popularity / recommendation logic is driven from the `listen` table.
    """

    # Table aliases (same style as SongsFrame)
    TBL_SONG = "song s"
    TBL_GROUP = '"GROUP" g'
    TBL_SONG_ALBUM = "song_within_album swa"
    TBL_ALBUM = "album al"
    TBL_LISTEN = "listen li"
    TBL_SONG_GENRE = "song_genre sg"
    # user_follow has columns: follower_user_id, followed_user_id
    TBL_FOLLOW = "user_follow f"

    # Song-view columns: (id, header, width)
    COLS_SONG = [
        ("_listen", "Listen", 70),
        ("song", "Song", 260),
        ("artist", "Artist", 200),
        ("album", "Album", 220),
        ("length", "Length", 80),
        ("release_year", "Year", 80),
        ("listen_count", "Listens", 90),
    ]

    # Genre-view columns
    COLS_GENRE = [
        ("genre", "Genre", 260),
        ("listens", "Listens", 120),
    ]

    # visible value index helpers for song-style rows
    IDX_SONG = 1
    IDX_LISTENS = 6

    # modes
    MODE_TOP_30 = "top_50_30_days"
    MODE_FOLLOWED = "top_50_followed"
    MODE_GENRES = "top_5_genres"
    MODE_RECS = "personal_recs"

    MODE_LABELS = [
        ("Top 50 – Last 30 Days", MODE_TOP_30),
        ("Top 50 – Followed Users", MODE_FOLLOWED),
        ("Top 5 Genres – This Month", MODE_GENRES),
        ("Recommended For You", MODE_RECS),
    ]

    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app

        self.current_mode = self.MODE_TOP_30
        self.current_cols = self.COLS_SONG

        # ---------- Header ----------
        ttk.Label(self, text="Recommendations", font=("Arial", 16, "bold")).pack(
            pady=(10, 6)
        )

        # ---------- Controls ----------
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=4)

        ttk.Label(bar, text="View:").pack(side="left", padx=(0, 6))
        self.mode_var = tk.StringVar(value=self.MODE_LABELS[0][0])
        self.mode_to_key = {label: key for (label, key) in self.MODE_LABELS}
        self.key_to_label = {key: label for (label, key) in self.MODE_LABELS}

        self.mode_combo = ttk.Combobox(
            bar,
            textvariable=self.mode_var,
            values=[label for (label, _key) in self.MODE_LABELS],
            width=30,
            state="readonly",
        )
        self.mode_combo.pack(side="left")
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)

        ttk.Button(bar, text="Refresh", command=self.refresh).pack(
            side="left", padx=(8, 0)
        )

        ttk.Button(bar, text="Back", command=lambda: app.safe_show("Dashboard")).pack(
            side="right"
        )

        self.info_lbl = ttk.Label(bar, text="")
        self.info_lbl.pack(side="right", padx=(0, 12))

        # ---------- Actions ----------
        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=2)
        ttk.Button(
            actions,
            text="Add to Collection",
            command=self.add_selected_to_collection,
        ).pack(side="left", padx=(8, 0))

        # ---------- Tree ----------
        self.tree = ttk.Treeview(
            self,
            show="headings",
            height=18,
            selectmode="extended",
        )
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Clicking the first column ("Listen") acts as a button in song-modes
        self.tree.bind("<Button-1>", self._on_tree_click)

        self._setup_columns(self.COLS_SONG)
        self.refresh()

    # ================= UI Helpers =================
    def _setup_columns(self, cols):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = [c[0] for c in cols]
        for col_id, header, width in cols:
            if col_id == "_listen":
                anchor = "center"
            elif col_id in ("length", "listen_count", "listens"):
                anchor = "e"
            else:
                anchor = "w"
            self.tree.heading(col_id, text=header)
            self.tree.column(col_id, width=width, anchor=anchor)
        self.current_cols = cols

    def _on_mode_change(self, _event=None):
        label = self.mode_var.get()
        self.current_mode = self.mode_to_key.get(label, self.MODE_TOP_30)

        # Switch columns depending on mode
        if self.current_mode == self.MODE_GENRES:
            self._setup_columns(self.COLS_GENRE)
        else:
            self._setup_columns(self.COLS_SONG)

        self.refresh()

    def _on_tree_click(self, event):
        """
        If they clicked the "Listen" column for a row in a song-based mode,
        record one listen and update that row.
        """
        if self.current_mode == self.MODE_GENRES:
            return  # no listening for genre summary

        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)  # "#1" is the first displayed column
        if col != "#1":
            return
        iid = self.tree.identify_row(event.y)
        if not iid or not iid.startswith("song_"):
            return
        song_id = iid[5:]
        self._record_listen_and_patch(song_id, iid)

    # ================= Formatting helpers =================
    @staticmethod
    def _fmt_len(ms: Optional[int]) -> str:
        try:
            total = int(ms) // 1000
            m, s = divmod(total, 60)
            return f"{m:02d}:{s:02d}"
        except Exception:
            return ""

    # ================= SQL Queries =================
    def _query_top_50_last_30_days(self):
        """
        Top 50 most popular songs in the last 30 days (rolling),
        fully driven by the listen table.

        Uses DISTINCT (listener_username, date_of_view) like SongsFrame.
        """
        sql = f"""
            SELECT
                s.song_id,
                s.title AS song,
                COALESCE(g.group_name, '') AS artist,
                COALESCE(string_agg(DISTINCT al.album_name, ', '), '') AS album,
                s.length_ms,
                COALESCE(COUNT(DISTINCT (li.listener_username, li.date_of_view)), 0) AS listen_count,
                COALESCE(MIN(s.release_date), MIN(al.release_date)) AS release_date,
                EXTRACT(YEAR FROM COALESCE(MIN(s.release_date), MIN(al.release_date))) AS release_year
            FROM {self.TBL_LISTEN}
            JOIN song s                ON s.song_id = li.song_id
            LEFT JOIN "GROUP" g        ON g.group_id = s.group_id
            LEFT JOIN song_within_album swa ON swa.song_id = s.song_id
            LEFT JOIN album al         ON al.album_id = swa.album_id
            WHERE li.date_of_view >= NOW() - INTERVAL '30 days'
            GROUP BY s.song_id, s.title, s.length_ms, g.group_name
            ORDER BY listen_count DESC,
                     LOWER(s.title) ASC,
                     LOWER(COALESCE(g.group_name, '')) ASC
            LIMIT 50
        """
        with self.app.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()

    def _query_top_50_followed_users(self, username: str):
        """
        Top 50 most popular songs among:
        – users followed by the current user
        – and the current user themselves.

        Driven from listen + user_follow, using DISTINCT counts
        like SongsFrame.
        """
        sql = f"""
            SELECT
                s.song_id,
                s.title AS song,
                COALESCE(g.group_name, '') AS artist,
                COALESCE(string_agg(DISTINCT al.album_name, ', '), '') AS album,
                s.length_ms,
                COALESCE(COUNT(DISTINCT (li.listener_username, li.date_of_view)), 0) AS listen_count,
                COALESCE(MIN(s.release_date), MIN(al.release_date)) AS release_date,
                EXTRACT(YEAR FROM COALESCE(MIN(s.release_date), MIN(al.release_date))) AS release_year
            FROM listen li
            JOIN song s
                 ON s.song_id = li.song_id
            LEFT JOIN "GROUP" g
                 ON g.group_id = s.group_id
            LEFT JOIN song_within_album swa
                 ON swa.song_id = s.song_id
            LEFT JOIN album al
                 ON al.album_id = swa.album_id
            WHERE
                -- listens by the current user
                li.listener_username = %s
                OR
                -- listens by users the current user follows
                li.listener_username IN (
                    SELECT followed_user_id
                    FROM user_follow
                    WHERE follower_user_id = %s
                )
            GROUP BY s.song_id, s.title, s.length_ms, g.group_name
            ORDER BY listen_count DESC,
                     LOWER(s.title) ASC,
                     LOWER(COALESCE(g.group_name, '')) ASC
            LIMIT 50
        """
        with self.app.cursor() as cur:
            cur.execute(sql, (username, username))
            return cur.fetchall()

    def _query_top_5_genres_this_month(self):
        """
        Top 5 most popular genres of the current calendar month.
        Driven from listen + song_genre.
        """
        sql = f"""
            SELECT
                sg.genre,
                COUNT(*) AS listens_this_month
            FROM {self.TBL_LISTEN}
            JOIN {self.TBL_SONG_GENRE}
                 ON sg.song_id = li.song_id
            WHERE li.date_of_view >= date_trunc('month', CURRENT_DATE)
              AND li.date_of_view <  date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
            GROUP BY sg.genre
            ORDER BY listens_this_month DESC, sg.genre ASC
            LIMIT 5
        """
        with self.app.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()

    def _query_recommended_songs(self, username: str):
        """
        Recommend songs based on:
        – user's play history in `listen`
        – play history of similar users in `listen`

        Similar users: share at least 3 songs with the current user.

        Returns rows:
        (song_id, song, artist, album, length_ms, release_date, release_year, listen_count, score)

        where:
        – listen_count = global distinct listens for the song
        – score        = recommendation strength (used for ordering only)
        """
        sql = f"""
            WITH user_listens AS (
                SELECT DISTINCT song_id
                FROM listen
                WHERE listener_username = %s
            ),
            similar_users AS (
                SELECT
                    li.listener_username,
                    COUNT(DISTINCT li.song_id) AS overlap
                FROM listen li
                JOIN user_listens ul ON ul.song_id = li.song_id
                WHERE li.listener_username <> %s
                GROUP BY li.listener_username
                HAVING COUNT(DISTINCT li.song_id) >= 3
            ),
            candidate_plays AS (
                SELECT
                    li.song_id,
                    COUNT(*) AS score
                FROM listen li
                JOIN similar_users su ON su.listener_username = li.listener_username
                WHERE li.song_id NOT IN (SELECT song_id FROM user_listens)
                GROUP BY li.song_id
            ),
            recommended_songs AS (
                SELECT
                    s.song_id,
                    s.title AS song,
                    COALESCE(g.group_name, '') AS artist,
                    COALESCE(string_agg(DISTINCT al.album_name, ', '), '') AS album,
                    s.length_ms,
                    COALESCE(MIN(s.release_date), MIN(al.release_date)) AS release_date,
                    EXTRACT(YEAR FROM COALESCE(MIN(s.release_date), MIN(al.release_date))) AS release_year,
                    c.score,
                    COALESCE(
                        COUNT(DISTINCT (li_all.listener_username, li_all.date_of_view)),
                        0
                    ) AS listen_count
                FROM candidate_plays c
                JOIN song s               ON s.song_id = c.song_id
                LEFT JOIN "GROUP" g       ON g.group_id = s.group_id
                LEFT JOIN song_within_album swa ON swa.song_id = s.song_id
                LEFT JOIN album al        ON al.album_id = swa.album_id
                LEFT JOIN listen li_all   ON li_all.song_id = s.song_id
                GROUP BY s.song_id, s.title, s.length_ms, g.group_name, c.score
            )
            SELECT
                song_id,
                song,
                artist,
                album,
                length_ms,
                release_date,
                release_year,
                listen_count,
                score
            FROM recommended_songs
            ORDER BY score DESC, LOWER(song) ASC
            LIMIT 50
        """
        with self.app.cursor() as cur:
            cur.execute(sql, (username, username))
            return cur.fetchall()

    # ================= Data load =================
    def refresh(self):
        try:
            if self.current_mode == self.MODE_TOP_30:
                rows = self._query_top_50_last_30_days()
                self._populate_song_rows(rows)
                if rows:
                    self.info_lbl.config(text="Top 50 songs (last 30 days)")
                else:
                    self.info_lbl.config(text="No listening activity in the last 30 days.")
            elif self.current_mode == self.MODE_FOLLOWED:
                if not self.app.session.username:
                    messagebox.showwarning(
                        "Not logged in",
                        "Please log in to see what people you follow are listening to.",
                    )
                    self.tree.delete(*self.tree.get_children())
                    self.info_lbl.config(text="Login required")
                    return
                rows = self._query_top_50_followed_users(self.app.session.username)
                if not rows:
                    self.tree.delete(*self.tree.get_children())
                    self.info_lbl.config(
                        text="No listening activity from people you follow."
                    )
                    messagebox.showinfo(
                        "No followed activity",
                        "You either don't follow anyone yet, or the users you follow "
                        "haven't listened to any songs.",
                    )
                    return
                self._populate_song_rows(rows)
                self.info_lbl.config(text="Top 50 songs among followed users")
            elif self.current_mode == self.MODE_GENRES:
                rows = self._query_top_5_genres_this_month()
                self._populate_genre_rows(rows)
                if rows:
                    self.info_lbl.config(text="Top 5 genres this month")
                else:
                    self.info_lbl.config(text="No listening activity this month yet.")
            elif self.current_mode == self.MODE_RECS:
                if not self.app.session.username:
                    messagebox.showwarning(
                        "Not logged in",
                        "Please log in to see your recommendations.",
                    )
                    self.tree.delete(*self.tree.get_children())
                    self.info_lbl.config(text="Login required")
                    return
                rows = self._query_recommended_songs(self.app.session.username)
                if not rows:
                    self.tree.delete(*self.tree.get_children())
                    self.info_lbl.config(
                        text="No recommendations yet – listen to more songs first."
                    )
                    messagebox.showinfo(
                        "No recommendations yet",
                        "We don't have enough listening history to recommend songs.\n"
                        "Try listening to more music or following some users!",
                    )
                    return
                self._populate_recommendation_rows(rows)
                self.info_lbl.config(text="Recommended songs for you")
        except Exception as e:
            messagebox.showerror(
                "Recommendations Error",
                f"Could not load data for this view:\n{e}",
            )

    def _populate_song_rows(self, rows):
        """
        rows: expected structure like
        (song_id, song, artist, album, length_ms, listen_count, release_date, release_year)
        """
        # Ensure correct columns
        if self.current_cols is not self.COLS_SONG:
            self._setup_columns(self.COLS_SONG)

        self.tree.delete(*self.tree.get_children())
        for (
            song_id,
            song,
            artist,
            album,
            length_ms,
            listen_count,
            _release_date,
            release_year,
        ) in rows:
            values = [
                "▶ Play",
                song or "",
                artist or "",
                album or "",
                self._fmt_len(length_ms),
                str(int(release_year)) if release_year else "",
                int(listen_count or 0),
            ]
            self.tree.insert("", "end", iid=f"song_{song_id}", values=values)

    def _populate_recommendation_rows(self, rows):
        """
        rows: (song_id, song, artist, album, length_ms, release_date, release_year,
               listen_count, score)

        We *display* listen_count in the "Listens" column, while keeping score only
        for ordering within the SQL.
        """
        if self.current_cols is not self.COLS_SONG:
            self._setup_columns(self.COLS_SONG)

        self.tree.delete(*self.tree.get_children())
        for (
            song_id,
            song,
            artist,
            album,
            length_ms,
            _release_date,
            release_year,
            listen_count,
            _score,
        ) in rows:
            values = [
                "▶ Play",
                song or "",
                artist or "",
                album or "",
                self._fmt_len(length_ms),
                str(int(release_year)) if release_year else "",
                int(listen_count or 0),
            ]
            self.tree.insert("", "end", iid=f"song_{song_id}", values=values)

    def _populate_genre_rows(self, rows):
        """
        rows: (genre, listens_this_month)
        """
        if self.current_cols is not self.COLS_GENRE:
            self._setup_columns(self.COLS_GENRE)

        self.tree.delete(*self.tree.get_children())
        for genre, listens in rows:
            values = [
                str(genre),
                int(listens or 0),
            ]
            self.tree.insert("", "end", iid=f"genre_{genre}", values=values)

    # ================= Listen handling =================
    def _record_listen_and_patch(self, song_id: str, iid: str):
        """
        Insert a single listen (one row in listen), then query the new total
        for this song and patch only this row.

        Logic is mode-aware so the recount matches the query used
        for each view, similar to SongsFrame.
        """
        if not self.app.session.username:
            messagebox.showwarning("Not logged in", "Please log in first.")
            return

        # grab title for popup before DB work
        try:
            vals_for_title = list(self.tree.item(iid, "values"))
            song_title = vals_for_title[self.IDX_SONG] or "Song"
        except Exception:
            song_title = "Song"

        try:
            with self.app.cursor() as cur:
                # 1) insert one listen row
                cur.execute(
                    """
                    INSERT INTO listen (song_id, listener_username, date_of_view)
                    VALUES (%s, %s, NOW())
                    """,
                    (song_id, self.app.session.username),
                )

                # 2) get the updated count for this song,
                #    matching the logic of the current view
                if self.current_mode == self.MODE_TOP_30:
                    # same filter as _query_top_50_last_30_days
                    cur.execute(
                        """
                        SELECT COALESCE(COUNT(DISTINCT (listener_username, date_of_view)), 0)
                        FROM listen
                        WHERE song_id = %s
                          AND date_of_view >= NOW() - INTERVAL '30 days'
                        """,
                        (song_id,),
                    )
                elif self.current_mode == self.MODE_FOLLOWED:
                    # same filter as _query_top_50_followed_users:
                    # listeners = you OR users you follow
                    cur.execute(
                        """
                        SELECT COALESCE(COUNT(DISTINCT (li.listener_username, li.date_of_view)), 0)
                        FROM listen li
                        WHERE li.song_id = %s
                          AND (
                                li.listener_username = %s
                                OR li.listener_username IN (
                                    SELECT followed_user_id
                                    FROM user_follow
                                    WHERE follower_user_id = %s
                                )
                              )
                        """,
                        (song_id, self.app.session.username, self.app.session.username),
                    )
                else:
                    # For recommendations or any other song-based view that doesn't
                    # have a special filter, fall back to global distinct count.
                    cur.execute(
                        """
                        SELECT COALESCE(COUNT(DISTINCT (listener_username, date_of_view)), 0)
                        FROM listen
                        WHERE song_id = %s
                        """,
                        (song_id,),
                    )

                (new_count,) = cur.fetchone()

            self.app.conn.commit()
        except Exception as e:
            messagebox.showerror("Listen Error", f"Could not record listen:\n{e}")
            return

        # 3) patch the single cell in the UI (no full refresh)
        try:
            vals = list(self.tree.item(iid, "values"))
            vals[self.IDX_LISTENS] = int(new_count)
            self.tree.item(iid, values=vals)
        except Exception:
            pass

        # 4) popup feedback
        messagebox.showinfo("Playing", f"▶ {song_title}")

    # ================= Collections =================
    def _get_selected_song_ids(self) -> List[str]:
        ids: List[str] = []
        for iid in self.tree.selection():
            if iid.startswith("song_"):
                ids.append(iid[5:])
        return ids

    def _get_collection_choices(self) -> List[Tuple[str, str]]:
        sql = """
            SELECT collection_id, collection_name
            FROM collection
            WHERE creator_username = %s
            ORDER BY collection_name
        """
        with self.app.cursor() as cur:
            cur.execute(sql, (self.app.session.username,))
            return cur.fetchall() or []

    def add_selected_to_collection(self):
        if self.current_mode == self.MODE_GENRES:
            messagebox.showinfo(
                "Genres only",
                "You can only add songs (not genres) to collections.\n"
                "Switch to a song-based view first.",
            )
            return

        if not self.app.session.username:
            messagebox.showwarning("Not logged in", "Please log in first.")
            return

        song_ids = self._get_selected_song_ids()
        if not song_ids:
            messagebox.showinfo("Select songs", "Please select one or more songs first.")
            return

        collections = self._get_collection_choices()
        if not collections:
            messagebox.showinfo(
                "No collections", "You don't have any collections. Create one first."
            )
            return

        dialog = tk.Toplevel(self)
        dialog.title("Choose Collection")
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding="16 12")
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Choose a collection:").pack(pady=(0, 8))
        listbox = tk.Listbox(frame, width=42, height=10)
        listbox.pack(pady=(0, 8))

        idx_to_coll = {}
        for i, (cid, name) in enumerate(collections):
            idx_to_coll[i] = (cid, name)
            listbox.insert(tk.END, name)

        def on_ok():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning(
                    "Select collection", "Please select a collection.", parent=dialog
                )
                return
            cid, cname = idx_to_coll[sel[0]]
            dialog.destroy()

            try:
                added = 0
                with self.app.cursor() as cur:
                    for sid in song_ids:
                        cur.execute(
                            """
                            INSERT INTO song_within_collection (collection_id, song_id)
                            VALUES (%s, %s)
                            ON CONFLICT (collection_id, song_id) DO NOTHING
                            """,
                            (cid, sid),
                        )
                        added += cur.rowcount
                self.app.conn.commit()
                skipped = len(song_ids) - added
                msg = f"Added {added} song(s) to '{cname}'."
                if skipped:
                    msg += f"  Skipped {skipped} duplicate(s)."
                messagebox.showinfo("Done", msg)
            except Exception as e:
                messagebox.showerror(
                    "Error", f"Could not add songs to collection:\n{e}"
                )

        ttk.Button(frame, text="OK", command=on_ok).pack(side="left", padx=(0, 8))
        ttk.Button(frame, text="Cancel", command=dialog.destroy).pack(side="left")

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        dialog.wait_window(dialog)
