import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, List, Tuple
import secrets
import string

from app import App


class CollectionsFrame(ttk.Frame):
    """View and manage the current user's collections."""

    COLS = [
        ("name", "Collection", 260),
        ("count", "Songs", 80),
        ("minutes", "Total Minutes", 120),
    ]

    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app

        # Header
        ttk.Label(self, text="Your Collections", style="Title.TLabel").pack(pady=(10, 6))

        # Toolbar
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=6)
        ttk.Button(bar, text="New", command=self.on_new).pack(side="left")
        ttk.Button(bar, text="Rename", command=self.on_rename).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Delete", command=self.on_delete).pack(side="left", padx=(6, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="Play All", command=self.on_play_all).pack(side="left")
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="Add Song", command=self.on_add_song).pack(side="left")
        ttk.Button(bar, text="Remove Song", command=self.on_remove_song).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Add Album", command=self.on_add_album).pack(side="left", padx=(10, 0))
        ttk.Button(bar, text="Remove Album", command=self.on_remove_album).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Refresh", command=self.refresh).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Back", command=lambda: app.safe_show("Dashboard")).pack(side="right")

        # List
        self.tree = ttk.Treeview(self, show="headings", selectmode="browse", height=16)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._setup_columns()

        # Songs in collection view
        songs_frame = ttk.LabelFrame(self, text="Songs in Collection")
        songs_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        
        # Songs list
        self.songs_tree = ttk.Treeview(songs_frame, show="headings", height=8)
        self.songs_tree.pack(fill="both", expand=True, pady=5)
        
        # Song columns
        self.SONG_COLS = [
            ("song_id", "Song ID", 100),
            ("title", "Title", 300),
            ("length", "Length", 80),
            ("group_id", "Group ID", 100),
        ]
        
        self.songs_tree["columns"] = [c[0] for c in self.SONG_COLS]
        for col_id, header, width in self.SONG_COLS:
            self.songs_tree.heading(col_id, text=header)
            anchor = "w" if col_id in ("title", "song_id") else "center"
            self.songs_tree.column(col_id, width=width, anchor=anchor, stretch=False)

        # Status
        self.status = ttk.Label(self, text="")
        self.status.pack(fill="x", padx=10, pady=(0, 6))

        # Bind collection selection to update songs view
        self.tree.bind('<<TreeviewSelect>>', self._on_collection_select)

    # ----- lifecycle -----
    def on_show(self):
        if not self.app.session.username:
            messagebox.showwarning("Not logged in", "Please log in to manage collections.")
            self.app.show_frame("Login")
            return
        self.refresh()

    # ----- UI helpers -----
    def _setup_columns(self):
        self.tree["columns"] = [c[0] for c in self.COLS]
        for col_id, header, width in self.COLS:
            self.tree.heading(col_id, text=header)
            anchor = "w" if col_id == "name" else "center"
            self.tree.column(col_id, width=width, anchor=anchor, stretch=False)

    def _get_selected_collection(self) -> Optional[Tuple[str, str]]:
        sel = self.tree.selection()
        if not sel:
            return None
        item_id = sel[0]
        values = self.tree.item(item_id, "values")
        # We didn't store id as a column; keep it in tags
        tags = self.tree.item(item_id, "tags") or []
        cid = tags[0] if tags else None
        name = values[0] if values else None
        if cid is None or name is None:
            return None
        return cid, name

    # ----- DB helpers -----
    def _list_collections(self) -> List[Tuple[str, str, int, float]]:
        """
        Return list of (collection_id, name, song_count, total_minutes)
        collection_id is a text id like '#ABC123'. Sorted by name ASC.
        """
        username = self.app.session.username
        sql = """
            SELECT c.collection_id,
                   c.collection_name,
                   COALESCE(COUNT(cs.song_id), 0) AS song_count,
                   COALESCE(SUM(s.length_ms) / 60000.0, 0) AS minutes
            FROM collection c
            LEFT JOIN song_within_collection cs ON cs.collection_id = c.collection_id
            LEFT JOIN song s ON s.song_id = cs.song_id
            WHERE c.creator_username = %s
            GROUP BY c.collection_id, c.collection_name
            ORDER BY c.collection_name ASC
        """
        with self.app.cursor() as cur:
            cur.execute(sql, (username,))
            rows = cur.fetchall() or []
        # ensure proper types
        out = []
        for cid, name, cnt, mins in rows:
            try:
                out.append((str(cid), str(name), int(cnt or 0), float(mins or 0)))
            except Exception:
                continue
        return out

    def _generate_collection_id(self) -> str:
        """Generate a unique collection_id matching '^#[A-Za-z0-9]{1,19}$'.
        This checks the DB for collisions and retries a few times.
        """
        alphabet = string.ascii_letters + string.digits
        # try lengths from 8 up to 12 for reasonable uniqueness
        for _ in range(20):
            length = secrets.choice([8, 9, 10, 11, 12])
            suffix = ''.join(secrets.choice(alphabet) for _ in range(length))
            cid = f"#{suffix}"
            with self.app.cursor() as cur:
                cur.execute("SELECT 1 FROM collection WHERE collection_id = %s", (cid,))
                if not cur.fetchone():
                    return cid
        raise RuntimeError("Failed to generate a unique collection_id")

    def _create_collection(self, name: str):
        cid = self._generate_collection_id()
        sql = """
            INSERT INTO collection (collection_id, creator_username, collection_name, creation_date)
            VALUES (%s, %s, %s, NOW())
        """
        self.app.exec_and_commit(sql, (cid, self.app.session.username, name))

    def _rename_collection(self, collection_id: str, new_name: str):
        sql = "UPDATE collection SET collection_name = %s WHERE collection_id = %s"
        self.app.exec_and_commit(sql, (new_name, collection_id))

    def _delete_collection(self, collection_id: str):
        # delete children then parent for FK safety
        with self.app.cursor() as cur:
            cur.execute("DELETE FROM song_within_collection WHERE collection_id = %s", (collection_id,))
            cur.execute("DELETE FROM collection WHERE collection_id = %s", (collection_id,))
        self.app.conn.commit()

    def _play_collection(self, collection_id: str):
        """Record a play event for each song in the collection for this user."""
        username = self.app.session.username
        # Fetch songs in the collection
        with self.app.cursor() as cur:
            cur.execute(
                "SELECT cs.song_id FROM song_within_collection cs WHERE cs.collection_id = %s",
                (collection_id,),
            )
            rows = cur.fetchall() or []
        song_ids = [r[0] for r in rows]
        if not song_ids:
            return 0
        # Record plays; adjust table/columns to your schema if different
        with self.app.cursor() as cur:
            for sid in song_ids:
                cur.execute(
                    "INSERT INTO listen (listener_username, song_id, date_of_view) VALUES (%s, %s, NOW())",
                    (username, sid),
                )
        self.app.conn.commit()
        return len(song_ids)

    # ----- actions -----
    def refresh(self):
        try:
            rows = self._list_collections()
            self.tree.delete(*self.tree.get_children())
            total_songs = 0
            total_minutes = 0.0
            for cid, name, cnt, mins in rows:
                total_songs += cnt
                total_minutes += mins
                # store id in tags[0]
                self.tree.insert("", "end", values=(name, cnt, f"{mins:.2f}"), tags=(str(cid),))
            self.status.config(
                text=f"{len(rows)} collections - {total_songs} songs - {total_minutes:.2f} minutes"
            )
            
            # Clear songs view when refreshing collections
            self.songs_tree.delete(*self.songs_tree.get_children())
        except Exception as e:
            messagebox.showerror("Collections Error", f"Could not load collections:\n{e}")

    def _list_collection_songs(self, collection_id: str):
        """Get all songs in a collection with details."""
        sql = """
            SELECT s.song_id, s.title, s.length_ms, s.group_id
            FROM song s
            JOIN song_within_collection sc ON sc.song_id = s.song_id
            WHERE sc.collection_id = %s
            ORDER BY s.title ASC
        """
        with self.app.cursor() as cur:
            cur.execute(sql, (collection_id,))
            return cur.fetchall()

    def _on_collection_select(self, event=None):
        """When a collection is selected, show its songs."""
        self.songs_tree.delete(*self.songs_tree.get_children())
        
        sel = self._get_selected_collection()
        if not sel:
            return
            
        cid, name = sel
        try:
            songs = self._list_collection_songs(cid)
            for song_id, title, length_ms, group_id in songs:
                # Format length as MM:SS
                length = ""
                if length_ms is not None:
                    total_sec = int(length_ms) // 1000
                    mins, secs = divmod(total_sec, 60)
                    length = f"{mins:02d}:{secs:02d}"
                
                values = [
                    song_id or "",
                    title or "",
                    length,
                    group_id or "",
                ]
                self.songs_tree.insert("", "end", values=values)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load songs for collection:\n{e}")

        
    def on_new(self):
        name = simpledialog.askstring("New Collection", "Enter collection name:", parent=self)
        if not name:
            return
        try:
            self._create_collection(name.strip())
            self.refresh()
        except Exception as e:
            messagebox.showerror("Create Failed", f"Could not create collection:\n{e}")

    def on_rename(self):
        sel = self._get_selected_collection()
        if not sel:
            messagebox.showinfo("Select a collection", "Please select a collection to rename.")
            return
        cid, old_name = sel
        new_name = simpledialog.askstring("Rename Collection", "New name:", initialvalue=old_name, parent=self)
        if not new_name or new_name.strip() == old_name:
            return
        try:
            self._rename_collection(cid, new_name.strip())
            self.refresh()
        except Exception as e:
            messagebox.showerror("Rename Failed", f"Could not rename collection:\n{e}")

    def on_delete(self):
        sel = self._get_selected_collection()
        if not sel:
            messagebox.showinfo("Select a collection", "Please select a collection to delete.")
            return
        cid, name = sel
        if not messagebox.askyesno("Delete Collection", f"Delete '{name}'? This cannot be undone."):
            return
        try:
            self._delete_collection(cid)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Delete Failed", f"Could not delete collection:\n{e}")

    def on_play_all(self):
        sel = self._get_selected_collection()
        if not sel:
            messagebox.showinfo("Select a collection", "Please select a collection to play.")
            return
        cid, name = sel
        try:
            count = self._play_collection(cid)
            if count:
                messagebox.showinfo("Played", f"Recorded {count} play(s) for '{name}'.")
            else:
                messagebox.showinfo("No Songs", f"Collection '{name}' has no songs.")
        except Exception as e:
            messagebox.showerror("Play Failed", f"Could not record plays:\n{e}")

    # ----- manage items -----
    def on_add_song(self):
        sel = self._get_selected_collection()
        if not sel:
            messagebox.showinfo("Select a collection", "Please select a collection first.")
            return
        cid, _ = sel
        sid_str = simpledialog.askstring("Add Song", "Enter song_id to add:", parent=self)
        if not sid_str:
            return
        try:
            sid = sid_str
        except Exception:
            messagebox.showwarning("Invalid", "Song ID must be 1–20 letters/numbers only (A–Z, a–z, 0–9)")
            return
        try:
            with self.app.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO song_within_collection (collection_id, song_id)
                    VALUES (%s, %s)
                    ON CONFLICT (collection_id, song_id) DO NOTHING
                    """,
                    (cid, sid),
                )
            added = cur.rowcount
            self.app.conn.commit()
            if added:
                self.refresh()
            else:
                messagebox.showinfo("No change", "That song is already in this collection.")
        except Exception as e:
            messagebox.showerror("Add Song Failed", f"Could not add song:\n{e}")

    def on_remove_song(self):
        sel = self._get_selected_collection()
        if not sel:
            messagebox.showinfo("Select a collection", "Please select a collection first.")
            return
        cid, _ = sel
        sid_str = simpledialog.askstring("Remove Song", "Enter song_id to remove:", parent=self)
        if not sid_str:
            return
        try:
            sid = sid_str
        except Exception:
            messagebox.showwarning("Invalid", "Song ID must be 1–20 letters/numbers only (A–Z, a–z, 0–9)")
            return
        try:
            with self.app.cursor() as cur:
                cur.execute(
                    "DELETE FROM song_within_collection WHERE collection_id = %s AND song_id = %s",
                    (cid, sid),
                )
            self.app.conn.commit()
            self.refresh()
        except Exception as e:
            messagebox.showerror("Remove Song Failed", f"Could not remove song:\n{e}")

    def on_add_album(self):
        sel = self._get_selected_collection()
        if not sel:
            messagebox.showinfo("Select a collection", "Please select a collection first.")
            return
        cid, _ = sel

        aid = simpledialog.askstring("Add Album", "Enter album_id to add:", parent=self)
        if not aid:
            return

        try:
            with self.app.cursor() as cur:
                # (Optional) make sure album exists
                cur.execute("SELECT 1 FROM album WHERE album_id = %s", (aid,))
                if not cur.fetchone():
                    messagebox.showwarning("Not found", f"Album '{aid}' does not exist.")
                    return

                # Pull songs from song_within_album, not song
                cur.execute(
                    """
                    SELECT swa.song_id
                    FROM song_within_album AS swa
                    WHERE swa.album_id = %s
                    ORDER BY swa.track_number NULLS LAST, swa.song_id
                    """,
                    (aid,),
                )
                rows = cur.fetchall() or []


                added = 0
                for (sid,) in rows:
                    cur.execute(
                        """
                        INSERT INTO song_within_collection (collection_id, song_id)
                        VALUES (%s, %s)
                        ON CONFLICT (collection_id, song_id) DO NOTHING
                        """,
                        (cid, sid),
                    )
                    # rowcount is 1 when inserted, 0 when skipped due to conflict
                    added += (cur.rowcount or 0)

            self.app.conn.commit()

            if not rows:
                messagebox.showinfo("Add Album", "That album has no tracks.")
            else:
                skipped = len(rows) - added
                msg = f"Added {added} song(s) from the album."
                if skipped:
                    msg += f"  Skipped {skipped} duplicate(s)."
                messagebox.showinfo("Add Album", msg)

            self.refresh()

        except Exception as e:
            messagebox.showerror("Add Album Failed", f"Could not add album songs:\n{e}")


    def on_remove_album(self):
        sel = self._get_selected_collection()
        if not sel:
            messagebox.showinfo("Select a collection", "Please select a collection first.")
            return
        cid, _ = sel

        aid = simpledialog.askstring("Remove Album", "Enter album_id to remove:", parent=self)
        if not aid:
            return

        try:
            with self.app.cursor() as cur:
                # Remove songs in this collection whose IDs are on that album
                cur.execute(
                    """
                    DELETE FROM song_within_collection swc
                    WHERE swc.collection_id = %s
                    AND swc.song_id IN (
                        SELECT swa.song_id
                        FROM song_within_album AS swa
                        WHERE swa.album_id = %s
                    )
                    """,
                    (cid, aid),
                )
                removed = cur.rowcount or 0

            self.app.conn.commit()
            messagebox.showinfo("Remove Album", f"Removed {removed} song(s) from the collection.")
            self.refresh()

        except Exception as e:
            messagebox.showerror("Remove Album Failed", f"Could not remove album songs:\n{e}")
