"""Compatibility wrapper for the modern CustomTkinter launcher.

This module is retained for backwards compatibility with older imports.
The active desktop UI now lives in ``ui.py`` and is started through
``wordlist_generator.app.launch()``.
"""

from __future__ import annotations

from .app import launch as _launch


def launch_gui():
    """Launch the modern H4CK3R Wordlist Generator UI."""
    return _launch()


__all__ = ["launch_gui"]
