import tkinter as tk
from tkinter import ttk, messagebox
from app import App

class SongsFrame(ttk.Frame):
    """Read-only viewer for the `song` table with search + paging."""
    TABLE = "song"

    # column id, header text, width
    COLS = [
        ("song_id", "Song ID", 100),
        ("group_id", "Group ID", 110),
        ("title", "Title", 220),
        ("length_ms", "Length", 80),
        ("release_date", "Release", 160),
    ]

    # allowed fields to search (whitelist so code can safely splice column name)
    SEARCHABLE = ("title", "song_id", "group_id")

    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        self.limit = 100
        self.offset = 0

        # --- Header
        ttk.Label(self, text="Songs", font=("Arial", 16, "bold")).pack(pady=(10, 6))

        # --- Controls row
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=4)

        # Search widgets
        ttk.Label(bar, text="Search:").pack(side="left", padx=(0,6))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(bar, textvariable=self.search_var, width=32)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<Return>", lambda e: self.apply_search())

        ttk.Label(bar, text=" in ").pack(side="left", padx=6)
        self.field_var = tk.StringVar(value="title")
        self.field_combo = ttk.Combobox(
            bar, textvariable=self.field_var, values=list(self.SEARCHABLE), width=10, state="readonly"
        )
        self.field_combo.pack(side="left")

        ttk.Button(bar, text="Search", command=self.apply_search).pack(side="left", padx=(8,0))
        ttk.Button(bar, text="Clear", command=self.clear_search).pack(side="left", padx=(6,12))

        # Pager + Refresh
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left")
        ttk.Button(bar, text="Prev", command=self.prev_page).pack(side="left", padx=(8,0))
        ttk.Button(bar, text="Next", command=self.next_page).pack(side="left", padx=(8,0))

        self.page_lbl = ttk.Label(bar, text="Page 1")
        self.page_lbl.pack(side="right")

        # Back button
        ttk.Button(self, text="Go to dashboard", command=lambda: app.safe_show("Dashboard")).pack()
        self.page_lbl.pack(side="right", padx=(0,12))

        # --- Tree
        self.tree = ttk.Treeview(self, show="headings", height=16)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self._setup_columns()

        self.refresh()

    # ---------- UI helpers ----------
    def _setup_columns(self):
        self.tree["columns"] = [c[0] for c in self.COLS]
        for col_id, header, width in self.COLS:
            self.tree.heading(col_id, text=header)
            self.tree.column(col_id, width=width, anchor="w")

    @staticmethod
    def _fmt_len(ms):
        try:
            ms = int(ms)
            total_sec = ms // 1000
            m, s = divmod(total_sec, 60)
            return f"{m:02d}:{s:02d}"
        except Exception:
            return "" if ms is None else str(ms)

    @staticmethod
    def _fmt_dt(dt):
        try:
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "" if dt is None else str(dt)

    # ---------- Search state ----------
    def apply_search(self):
        """Apply current search; reset to first page."""
        self.offset = 0
        self.refresh()

    def clear_search(self):
        self.search_var.set("")
        self.offset = 0
        self.refresh()

    # ---------- SQL helpers ----------
    def _build_where(self):
        """
        Returns (where_sql, params_for_where) based on search box.
        Column name is whitelisted from SEARCHABLE to avoid injection.
        """
        term = self.search_var.get().strip()
        field = self.field_var.get().strip()

        if not term:
            return "", []

        # default to title if somehow field not valid
        if field not in self.SEARCHABLE:
            field = "title"

        # Use ILIKE for case-insensitive partial match
        where_sql = f"WHERE {field} ILIKE %s"
        return where_sql, [f"%{term}%"]

    def _count_matches(self):
        where_sql, params = self._build_where()
        sql = f"SELECT COUNT(*) FROM {self.TABLE} {where_sql}"
        with self.app.cursor() as cur:
            cur.execute(sql, params)
            (count,) = cur.fetchone()
        return int(count)

    def _query_songs(self):
        where_sql, params = self._build_where()
        sql = f"""
            SELECT song_id, group_id, title, length_ms, release_date
            FROM {self.TABLE}
            {where_sql}
            ORDER BY release_date DESC, song_id ASC
            LIMIT %s OFFSET %s
        """
        with self.app.cursor() as cur:
            cur.execute(sql, (*params, self.limit, self.offset))
            rows = cur.fetchall()
        return rows

    # ---------- Data load ----------
    def refresh(self):
        try:
            rows = self._query_songs()
            total = self._count_matches()  # keep it simple; fast with an index (see note below)

            # clear and insert
            self.tree.delete(*self.tree.get_children())
            for song_id, group_id, title, length_ms, release_date in rows:
                values = [
                    "" if song_id is None else str(song_id),
                    "" if group_id is None else str(group_id),
                    "" if title is None else str(title),
                    self._fmt_len(length_ms),
                    self._fmt_dt(release_date),
                ]
                self.tree.insert("", "end", values=values)

            page = (self.offset // self.limit) + 1
            pages = max(1, (total + self.limit - 1) // self.limit)
            self.page_lbl.config(text=f"Page {page}/{pages}  •  {total} match(es)")
        except Exception as e:
            messagebox.showerror("Songs Error", f"Could not load songs:\n{e}")

    def next_page(self):
        self.offset += self.limit
        self.refresh()

    def prev_page(self):
        if self.offset >= self.limit:
            self.offset -= self.limit
            self.refresh()
