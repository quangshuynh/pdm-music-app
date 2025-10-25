# imports up top — keep these exactly
import tkinter as tk
from tkinter import ttk, messagebox
from app import App

class SongsFrame(ttk.Frame):
    """Read-only viewer for the `songs` table."""
    # column id, header text, width
    COLS = [
        ("song_id", "Song ID", 100),
        ("group_id", "Group ID", 110),
        ("title", "Title", 220),
        ("length_ms", "Length", 80),
        ("release_date", "Release", 160),
    ]

    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        self.limit = 100
        self.offset = 0

        ttk.Label(self, text="Songs", font=("Arial", 16, "bold")).pack(pady=(10, 6))

        # Controls
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=4)
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left")
        ttk.Button(bar, text="Prev", command=self.prev_page).pack(side="left", padx=(8,0))
        ttk.Button(bar, text="Next", command=self.next_page).pack(side="left", padx=(8,0))
        self.page_lbl = ttk.Label(bar, text="Page 1")
        self.page_lbl.pack(side="right")

        # Treeview
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
        # dt may be datetime, date, or string depending on your driver/adapter
        try:
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "" if dt is None else str(dt)

    # ---------- Data ----------
    def _query_songs(self):
        sql = """
            SELECT song_id, group_id, title, length_ms, release_date
            FROM song
            ORDER BY release_date DESC, song_id ASC
            LIMIT %s OFFSET %s
        """
        with self.app.cursor() as cur:
            cur.execute(sql, (self.limit, self.offset))
            rows = cur.fetchall()
        return rows

    def refresh(self):
        try:
            rows = self._query_songs()

            # clear and insert
            self.tree.delete(*self.tree.get_children())
            for r in rows:
                # r is a tuple in the order we selected
                song_id, group_id, title, length_ms, release_date = r
                values = [
                    str(song_id) if song_id is not None else "",
                    str(group_id) if group_id is not None else "",
                    "" if title is None else str(title),
                    self._fmt_len(length_ms),
                    self._fmt_dt(release_date),
                ]
                self.tree.insert("", "end", values=values)

            self.page_lbl.config(text=f"Page {self.offset // self.limit + 1}")
        except Exception as e:
            messagebox.showerror("Songs Error", f"Could not load songs:\n{e}")

    def next_page(self):
        self.offset += self.limit
        self.refresh()

    def prev_page(self):
        if self.offset >= self.limit:
            self.offset -= self.limit
            self.refresh()
