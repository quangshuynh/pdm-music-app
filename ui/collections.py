import tkinter as tk
from tkinter import ttk, messagebox
from app import App

class CollectionsFrame(ttk.Frame):
        """View & manage user collection"""
        def __init__(self, parent, app: App):
                super().__init__(parent)
                self.app = app

                # --- Header
                ttk.Label(self, text ="My Collection", font=("Arial", 16, "bold")).pack(pady=(10))

                # --- Controls row
                bar = ttk.Frame(self)
                bar.pack(fill="x", padx = 10, pady = 5)

                self.new_name = tk.StringVar()
                ttk.Entry(bar, textvariable=self.new_name, width=30).pack(side="left")

                # Refresh, back to dash, create collection
                ttk.Button(bar, text="Create Collection", command=self.create_collection).pack(side="left", padx=(8,0))
                ttk.Button(bar, text="Refresh", command = self.refresh).pack(side="left", padx=(8,0))
                ttk.Button(bar, text="Back", command=lambda: app.safe_show("Dashboard")).pack(side="right")

                # --- Tree
                self.tree = ttk.Treeview(self, columns=("name", "songs", "mins"), show="headings", height=15)
                self.tree.pack(fill="both", expand=True, padx=10, pady=10)
                for col, hdr, w in [
                                ("name","Collection Name",240),
                                ("songs","# Songs",80),
                                ("mins","Total (min)",100)
                        ]:
                        self.tree.heading(col, text=hdr)
                        self.tree.column(col, width=w, anchor="center")

                self.tree.bind("<Double-1>", self.on_row_double_click)

                self.refresh() 

        # ---------- UI helpers ----------
        def create_collection(self):
                name = self.new_name.get().strip()
                if not name:
                        messagebox.showerror("Error", "Collection name cannot be empty.")
                        return
                try:
                        with self.app.cursor() as cur:
                                # Check for duplicate name for this user
                                cur.execute(
                                'SELECT COUNT(*) FROM collection WHERE collection_name = %s AND username = %s',
                                (name, self.app.session.username)
                                )
                                existing = cur.fetchone()[0]
                                if existing:
                                        messagebox.showerror("Error", "A collection with this name already exists.")
                                return

                        # Insert new collection
                        cur.execute(
                                'INSERT INTO collection (collection_name, username, creation_date) VALUES (%s, %s, NOW())',
                                (name, self.app.session.username)
                        )
                        self.app.conn.commit()
                        self.new_name.set("")
                        self.refresh()
                        messagebox.showinfo("Created", f"Collection '{name}' successfully added.")
                except Exception as e:
                        messagebox.showerror("Database Error", f"Failed to create collection:\n{e}")


        def on_row_double_click(self, event):
                selected = self.tree.focus()
                if not selected:
                        return
                cid = int(selected)
                print(f"Opening Collection {cid} ...") #todo: uday
        
        # ---------- Data load ----------
        def refresh(self):
                try:
                        self.tree.delete(*self.tree.get_children())

                        sql = """
                                Select c.collection_id, c.collection_name, 
                                        COUNT(cs.song_id) AS num_songs
                                From collection c
                                LEFT JOIN song_within_collection swc
                                        on c.collection_id = swc.collection_id
                                WHERE c.username = %s
                                GROUP BY c.collection_id, c.collection_name
                                ORDER BY c.collection_name ASC;
                        """
                        with self.app.cursor() as cur:
                                curr.execute(sql, (self.app.session.username,))
                                rows = cur.fetchall()

                                for cid, name, count in rows:
                                        self.tree.insert("", "end", iid=cid, values=(name,count))
                except Exception as e:
                        messagebox.showerror("Database Error", f"failed to load collections:\n{e}")




