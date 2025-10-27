import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple, Optional
from app import App


class SongsFrame(ttk.Frame):
    """
    Song search + results viewer with 'Listen' action per row.
    """

    # SQL expressions used in SELECT/ORDER/GROUP BY.
    SQL_COLS = {
        "song": "s.title",
        "artist": "COALESCE(g.group_name, '')",
        "album": "COALESCE(al.album_name, '')",
        "length_ms": "s.length_ms",
        "release_date": "al.release_date",
        "release_year": "EXTRACT(YEAR FROM al.release_date)",
        "genre": "COALESCE(string_agg(DISTINCT sg.genre::text, ', '), '')",
        "listen_count": "COALESCE(COUNT(li.song_id), 0)",
    }

    # Table names
    TBL_SONG = "song s"
    TBL_GROUP = '"GROUP" g'
    TBL_SONG_ALBUM = "song_within_album swa"
    TBL_ALBUM = "album al"
    TBL_SONG_GENRE = "song_genre sg"
    TBL_LISTEN = "listen li"

    # UI columns: (tree_id, header, width)
    # NOTE: _listen is a pseudo-column that renders a button-like cell.
    COLS = [
        ("_listen", "Listen", 70),
        ("song", "Song", 260),
        ("artist", "Artist", 200),
        ("album", "Album", 220),
        ("length", "Length", 80),
        ("release_year", "Year", 80),
        ("listen_count", "Listens", 90),
    ]

    SEARCH_FIELDS = {
        "song": "s.title",
        "artist": "g.group_name",
        "album": "al.album_name",
        "genre": "sg.genre::text",
    }

    SORTABLE = {
        "song": SQL_COLS["song"],
        "artist": SQL_COLS["artist"],
        "genre": SQL_COLS["genre"],
        "release_year": SQL_COLS["release_year"],
    }

    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app

        # Paging
        self.limit = 100
        self.offset = 0

        # Default sort
        self.sort_key = "song"
        self.sort_dir = "ASC"

        # ---------- Header ----------
        ttk.Label(self, text="Songs", font=("Arial", 16, "bold")).pack(pady=(10, 6))

        # ---------- Controls ----------
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=4)

        ttk.Label(bar, text="Search:").pack(side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(bar, textvariable=self.search_var, width=36)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<Return>", lambda e: self.apply_search())

        ttk.Label(bar, text=" in ").pack(side="left", padx=6)
        self.field_var = tk.StringVar(value="song")
        self.field_combo = ttk.Combobox(
            bar,
            textvariable=self.field_var,
            values=list(self.SEARCH_FIELDS.keys()),
            width=12,
            state="readonly",
        )
        self.field_combo.pack(side="left")

        ttk.Button(bar, text="Search", command=self.apply_search).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="Clear", command=self.clear_search).pack(side="left", padx=(6, 12))

        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left")
        ttk.Button(bar, text="Prev", command=self.prev_page).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="Next", command=self.next_page).pack(side="left", padx=(8, 0))

        self.page_lbl = ttk.Label(bar, text="Page 1")
        self.page_lbl.pack(side="right")

        # Action row
        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=2)
        ttk.Button(actions, text="Listen Selected", command=self.listen_selected).pack(side="left")
        ttk.Button(actions, text="Add to Collection", command=self.add_selected_to_collection).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Back", command=lambda: app.safe_show("Dashboard")).pack(side="right")

        # ---------- Tree ----------
        self.tree = ttk.Treeview(self, show="headings", height=18, selectmode="extended")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._setup_columns()

        # Clicking the first column ("Listen") acts as a button
        self.tree.bind("<Button-1>", self._on_tree_click)

        self.refresh()

    # ================= UI Helpers =================
    def _setup_columns(self):
        self.tree["columns"] = [c[0] for c in self.COLS]
        for col_id, header, width in self.COLS:
            self.tree.heading(col_id, text=header, command=lambda c=col_id: self._on_heading_click(c))
            anchor = "center" if col_id == "_listen" else ("e" if col_id in ("length", "listen_count") else "w")
            self.tree.column(col_id, width=width, anchor=anchor)
        self._render_heading_arrows()

    def _render_heading_arrows(self):
        for col_id, header, _ in self.COLS:
            key = "release_year" if col_id == "release_year" else col_id
            if key == self.sort_key:
                arrow = "▲" if self.sort_dir == "ASC" else "▼"
                self.tree.heading(col_id, text=f"{header} {arrow}")
            else:
                self.tree.heading(col_id, text=header)

    def _on_heading_click(self, col_id: str):
        if col_id == "_listen":
            return  # not sortable
        key = col_id
        if key not in self.SORTABLE:
            return

        if self.sort_key == key:
            self.sort_dir = "DESC" if self.sort_dir == "ASC" else "ASC"
        else:
            self.sort_key = key
            self.sort_dir = "ASC"

        self.offset = 0
        self.refresh()

    def _on_tree_click(self, event):
        # If they clicked the "Listen" column for a row, record a listen
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)  # e.g., "#1"
        if col != "#1":
            return  # first displayed column is our _listen pseudo-button
        iid = self.tree.identify_row(event.y)
        if not iid or not iid.startswith("song_"):
            return
        song_id = iid[5:]
        self._record_listen(song_id)

    # ================= Formatting helpers =================
    @staticmethod
    def _fmt_len(ms: Optional[int]) -> str:
        try:
            total = int(ms) // 1000
            m, s = divmod(total, 60)
            return f"{m:02d}:{s:02d}"
        except Exception:
            return ""

    # ================= Search state =================
    def apply_search(self):
        self.offset = 0
        self.refresh()

    def clear_search(self):
        self.search_var.set("")
        self.offset = 0
        self.refresh()

    # ================= SQL build =================
    def _build_base_from(self) -> str:
        return f"""
        FROM {self.TBL_SONG}
        LEFT JOIN {self.TBL_GROUP}      ON g.group_id = s.group_id
        LEFT JOIN {self.TBL_SONG_ALBUM} ON swa.song_id = s.song_id
        LEFT JOIN {self.TBL_ALBUM}      ON al.album_id = swa.album_id
        LEFT JOIN {self.TBL_SONG_GENRE} ON sg.song_id = s.song_id
        LEFT JOIN {self.TBL_LISTEN}     ON li.song_id = s.song_id
        """

    def _build_where(self) -> Tuple[str, list]:
        term = self.search_var.get().strip()
        if not term:
            return "", []

        field_key = self.field_var.get()
        field_expr = self.SEARCH_FIELDS.get(field_key, "s.title")
        return f"WHERE {field_expr} ILIKE %s", [f"%{term}%"]

    def _order_sql(self) -> str:
        key = self.sort_key if self.sort_key in ("song", "artist", "genre", "release_year") else "song"
        direction = "ASC" if self.sort_dir == "ASC" else "DESC"

        if key in ("song", "artist", "genre"):
            primary = f"LOWER({key}) {direction}"
        else:
            primary = f"{key} {direction}"

        secondary = "LOWER(song) ASC, LOWER(artist) ASC"
        return f"ORDER BY {primary}, {secondary}"

    # ================= Queries =================
    def _count_matches(self) -> int:
        where_sql, params = self._build_where()
        sql = f"SELECT COUNT(DISTINCT s.song_id) {self._build_base_from()} {where_sql}"
        with self.app.cursor() as cur:
            cur.execute(sql, params)
            (count,) = cur.fetchone()
        return int(count)

    def _query_rows(self):
        where_sql, params = self._build_where()
        order_sql = self._order_sql()

        sql = f"""
            SELECT *
            FROM (
                SELECT
                    s.song_id,
                    s.title AS song,
                    COALESCE(g.group_name, '') AS artist,

                    COALESCE(string_agg(DISTINCT al.album_name, ', '), '') AS album,
                    s.length_ms,

                    -- Count listens without being multiplied by album/genre joins
                    COALESCE(COUNT(DISTINCT (li.listener_username, li.date_of_view)), 0) AS listen_count,

                    COALESCE(string_agg(DISTINCT sg.genre, ', '), '') AS genre,

                    COALESCE(MIN(s.release_date), MIN(al.release_date)) AS release_date,
                    EXTRACT(YEAR FROM COALESCE(MIN(s.release_date), MIN(al.release_date))) AS release_year
                {self._build_base_from()}
                {where_sql}
                GROUP BY
                    s.song_id, s.title, s.length_ms, g.group_name
            ) AS sub
            {order_sql}
            LIMIT %s OFFSET %s
        """
        with self.app.cursor() as cur:
            cur.execute(sql, (*params, self.limit, self.offset))
            return cur.fetchall()

    # ================= Data load =================
    def refresh(self):
        try:
            rows = self._query_rows()
            total = self._count_matches()

            self.tree.delete(*self.tree.get_children())

            for (
                song_id,
                song,
                artist,
                album,
                length_ms,
                listen_count,
                _genre,
                _release_date,
                release_year,
            ) in rows:
                values = [
                    "▶ Play",                             # _listen pseudo-button
                    song or "",
                    artist or "",
                    album or "",
                    self._fmt_len(length_ms),
                    str(int(release_year)) if release_year else "",
                    int(listen_count or 0),
                ]
                self.tree.insert("", "end", iid=f"song_{song_id}", values=values)

            page = (self.offset // self.limit) + 1
            pages = max(1, (total + self.limit - 1) // self.limit)
            self.page_lbl.config(text=f"Page {page}/{pages}  •  {total} match(es)")
            self._render_heading_arrows()
        except Exception as e:
            messagebox.showerror("Songs Error", f"Could not load songs:\n{e}")

    def next_page(self):
        self.offset += self.limit
        self.refresh()

    def prev_page(self):
        if self.offset >= self.limit:
            self.offset -= self.limit
            self.refresh()

    # ================= Listen actions =================
    def _record_listen(self, song_id: str):
        if not self.app.session.username:
            messagebox.showwarning("Not logged in", "Please log in first.")
            return
        try:
            with self.app.cursor() as cur:
                # If date_of_view has a DEFAULT now() you can omit it; included here for clarity.
                cur.execute(
                    """
                    INSERT INTO listen (song_id, listener_username, date_of_view)
                    VALUES (%s, %s, NOW())
                    """,
                    (song_id, self.app.session.username),
                )
            self.app.conn.commit()
            # Refresh to update listen_count (and preserve filters/sort)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Listen Error", f"Could not record listen:\n{e}")

    def listen_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a song", "Please select a song first.")
            return
        iid = sel[0]
        if not iid.startswith("song_"):
            return
        song_id = iid[5:]
        self._record_listen(song_id)

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
        if not self.app.session.username:
            messagebox.showwarning("Not logged in", "Please log in first.")
            return

        song_ids = self._get_selected_song_ids()
        if not song_ids:
            messagebox.showinfo("Select songs", "Please select one or more songs first.")
            return

        collections = self._get_collection_choices()
        if not collections:
            messagebox.showinfo("No collections", "You don't have any collections. Create one first.")
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
                messagebox.showwarning("Select collection", "Please select a collection.", parent=dialog)
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
                messagebox.showerror("Error", f"Could not add songs to collection:\n{e}")

        ttk.Button(frame, text="OK", command=on_ok).pack(side="left", padx=(0, 8))
        ttk.Button(frame, text="Cancel", command=dialog.destroy).pack(side="left")

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        dialog.wait_window(dialog)
