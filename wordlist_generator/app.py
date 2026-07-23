"""Application launcher for the H4CK3R Wordlist Generator.

Creates logger and launches the CustomTkinter UI.
"""
from __future__ import annotations

from .logger import get_logger
from .ui import HackerUI


def launch():
    logger = get_logger()
    logger.info("Launching Hacker Wordlist Generator UI")

    try:
        app = HackerUI()
        app.mainloop()
    except Exception as e:
        logger.exception("Exception in HackerUI")
        import traceback
        traceback.print_exc()
        print("ERROR:", e)