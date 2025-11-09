import tkinter as tk
from tkinter import ttk

class DashboardFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        ttk.Label(self, text="Dashboard").pack(pady=20)
        ttk.Button(self, text="Go to Songs", command=lambda: app.safe_show("Songs")).pack()
        ttk.Button(self, text="Go to Follow", command=lambda: app.safe_show("Follow")).pack()
        ttk.Button(self, text="Go to Collections", command=lambda: app.safe_show("Collections")).pack()
        ttk.Button(self, text="Recommendations", command=lambda: app.safe_show("Recommendations")).pack()
        ttk.Button(self, text="Log Out", command=lambda: app.safe_show("Login")).pack()

    def on_show(self):
        pass
