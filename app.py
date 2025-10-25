import sys
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from typing import Dict, Type, Optional

from db_connection import get_connection, close_tunnel

@dataclass
class Session:
    # holds runtime session state for the app
    username: Optional[str] = None      
    display_name: Optional[str] = None  
    email: Optional[str] = None         


class App(tk.Tk):
    """
    Main application window. Owns:
      - a shared PostgreSQL connection (self.conn)
      - a Session object (self.session)
      - a frame router with show_frame()
    """
    TITLE = "Music Information Database — Team 48"

    def _set_style(self):
        """ttk styles and theme."""
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        # style tweaks
        style.configure("TLabel", padding=(4, 2))
        style.configure("TButton", padding=(6, 4))
        style.configure("TEntry", padding=(2, 2))
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))


    def __init__(self):
        super().__init__()

        # Basic window setup 
        self.title(self.TITLE)
        self.geometry("1280x650")
        self.minsize(1000, 560)
        self._set_style()

        #  connect to DB once; reconnect on failure when needed 
        try:
            self.conn = get_connection()
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not connect to the database.\n\n{e}")
            # fail fast so students catch credential issues immediately
            self.destroy()
            sys.exit(1)

        # track session for currently logged-in user
        self.session = Session()

        # track session for currently logged-in user
        self.session = Session()

        #  container & router 
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self.frames: Dict[str, tk.Frame] = {}

        # import UI frame classes here to avoid circular imports with ui.* modules
        from ui.login import LoginFrame
        from ui.signup import SignupFrame
        from ui.dashboard import DashboardFrame
        from ui.songs import SongsFrame
        from ui.follow import FollowFrame
        from ui.collections import CollectionsFrame

        # map route name -> Frame class
        routes: Dict[str, Type[tk.Frame]] = {
            "Login": LoginFrame,
            "Signup": SignupFrame,
            "Dashboard": DashboardFrame,
            "Songs": SongsFrame,
            "Follow": FollowFrame,
            "Collections": CollectionsFrame,
        }
        for name, FrameCls in routes.items():
            frame = FrameCls(parent=container, app=self)  # pass app for access
            self.frames[name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # start at Login
        self.show_frame("Login")

        # handle window close: clean DB connection
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # routing helpers
    def show_frame(self, name: str):
        """Raise a frame by name; calls `on_show()` on the frame if available."""
        frame = self.frames.get(name)
        if not frame:
            raise KeyError(f"Unknown frame '{name}'")
        # allow pages to refresh themselves when shown
        if hasattr(frame, "on_show") and callable(getattr(frame, "on_show")):
            try:
                frame.on_show()
            except Exception as e:
                # do not crash the router if the page's refresh fails
                messagebox.showerror("View Error", f"{name} failed to load:\n{e}")
        frame.tkraise()
        self._update_title_suffix(name)

    def safe_show(self, name: str):
        """Show frame only if the user is logged in (except Login)."""
        if name != "Login" and not self.session.username:
            messagebox.showwarning("Please log in", "You must log in first.")
            self.show_frame("Login")
            return
        self.show_frame(name)

    def _update_title_suffix(self, name: str):
        """Show page and user in window title for clarity."""
        user = self.session.display_name or self.session.username or "Guest"
        self.title(f"{self.TITLE} — {name} ({user})")

    #db helper
    def cursor(self):
        """
        Get a fresh cursor. Reconnects if needed.
        Usage:
            with app.cursor() as cur:
                cur.execute("SELECT 1")
        """
        try:
            # if connection closed (0=open, nonzero=closed in psycopg2)
            if getattr(self.conn, "closed", 1):
                self.conn = get_connection()
        except Exception:
            self.conn = get_connection()
        return self.conn.cursor()


    def exec_and_commit(self, sql_query: str, params: tuple = ()):
        """Small helper: run a write query and commit."""
        with self.cursor() as cur:
            cur.execute(sql_query, params)
        self.conn.commit()

    # lifecycle
    def on_close(self):
        try:
            if hasattr(self, "conn") and self.conn:
                self.conn.close()
        except Exception:
            pass
        try:
            close_tunnel()
        except Exception:
            pass
        self.destroy()



def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
