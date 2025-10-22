import tkinter as tk
from tkinter import ttk

class SongsFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Songs Page").pack(pady=20)
        ttk.Button(self, text="Back to Dashboard", command=lambda: app.safe_show("Dashboard")).pack()

    def on_show(self):
        pass
