"""PolarWatch Sites — modern PolarLabs website-only desktop monitor.

This entrypoint intentionally has no imports from the owner mining console,
SQLite database, Stripe, wallet, or license management.
"""
import customtkinter as ctk
from polarwatch_modern_ui import PolarWatchModern

def main():
    root=ctk.CTk()
    PolarWatchModern(root)
    root.mainloop()

if __name__=="__main__":
    main()
