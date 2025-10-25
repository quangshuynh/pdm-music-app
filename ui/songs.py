import tkinter as tk
from tkinter import ttk, messagebox
from app import App

class SongsFrame(ttk.Frame):
    """Read-only viewer for the `song` table with search + paging + sortable headers."""
    TABLE = "song"

    # column id, header text, width
    COLS = [
        ("song_id", "Song ID", 100),
        ("group_id", "Group ID", 110),
        ("title", "Title", 220),
        ("length_ms", "Length", 80),
        ("release_date", "Release", 160),
    ]

    # allowed fields to search / sort (whitelists for safety)
    SEARCHABLE = ("title", "song_id", "group_id")
    SORTABLE   = ("song_id", "group_id", "title", "length_ms", "release_date")

    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        self.limit = 100
        self.offset = 0

        # default sort matches your previous ORDER BY
        self.sort_col = "release_date"
        self.sort_dir = "DESC"  # or "ASC"

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
        ttk.Button(self, text="Go to dashboard", command=lambda: app.safe_show("Dashboard")).pack(pady=(2,6))

        # --- Tree
        self.tree = ttk.Treeview(self, show="headings", height=16)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self._setup_columns()

        self.refresh()

    # ---------- UI helpers ----------
    def _setup_columns(self):
        self.tree["columns"] = [c[0] for c in self.COLS]
        for col_id, header, width in self.COLS:
            # make headings clickable
            self.tree.heading(col_id, text=header, command=lambda c=col_id: self._on_heading_click(c))
            self.tree.column(col_id, width=width, anchor="w")
        self._render_heading_arrows()

    def _render_heading_arrows(self):
        """Show ▲/▼ on the active sort column."""
        for col_id, header, _ in self.COLS:
            if col_id == self.sort_col:
                arrow = "▲" if self.sort_dir == "ASC" else "▼"
                self.tree.heading(col_id, text=f"{header} {arrow}")
            else:
                self.tree.heading(col_id, text=header)

    def _on_heading_click(self, col_id: str):
        if col_id not in self.SORTABLE:
            return
        if self.sort_col == col_id:
            # toggle direction
            self.sort_dir = "DESC" if self.sort_dir == "ASC" else "ASC"
        else:
            # switch column, start ASC
            self.sort_col = col_id
            self.sort_dir = "ASC"
        self.offset = 0  # go back to first page on new sort
        self.refresh()

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
        self.offset = 0
        self.refresh()

    def clear_search(self):
        self.search_var.set("")
        self.offset = 0
        self.refresh()

    # ---------- SQL builders ----------
    def _build_where(self):
        term = self.search_var.get().strip()
        field = self.field_var.get().strip()
        if not term:
            return "", []
        if field not in self.SEARCHABLE:
            field = "title"
        where_sql = f"WHERE {field} ILIKE %s"
        return where_sql, [f"%{term}%"]

    def _order_sql(self) -> str:
        """
        Build a safe ORDER BY using whitelisted column and direction.
        Text columns sort case-insensitively via LOWER(...).
        """
        col = self.sort_col if self.sort_col in self.SORTABLE else "release_date"
        direction = "ASC" if self.sort_dir == "ASC" else "DESC"

        if col in ("song_id", "group_id", "title"):
            primary = f"LOWER({col}) {direction}"
        else:
            primary = f"{col} {direction}"

        # deterministic tiebreaker
        tiebreak = "song_id ASC"
        return f"ORDER BY {primary}, {tiebreak}"

    # ---------- Queries ----------
    def _count_matches(self):
        where_sql, params = self._build_where()
        sql = f"SELECT COUNT(*) FROM {self.TABLE} {where_sql}"
        with self.app.cursor() as cur:
            cur.execute(sql, params)
            (count,) = cur.fetchone()
        return int(count)

    def _query_songs(self):
        where_sql, params = self._build_where()
        order_sql = self._order_sql()
        sql = f"""
            SELECT song_id, group_id, title, length_ms, release_date
            FROM {self.TABLE}
            {where_sql}
            {order_sql}
            LIMIT %s OFFSET %s
        """
        with self.app.cursor() as cur:
            cur.execute(sql, (*params, self.limit, self.offset))
            return cur.fetchall()

    # ---------- Data load ----------
    def refresh(self):
        try:
            rows = self._query_songs()
            total = self._count_matches()

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
