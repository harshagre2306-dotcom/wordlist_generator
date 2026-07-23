"""CustomTkinter-based Hacker-themed UI.

This module implements a professional-looking, responsive UI using
CustomTkinter (ctk). It keeps logic separated from the generator.
"""
from __future__ import annotations

import json
import os
import time
import datetime
import threading
from pathlib import Path
from typing import List

from tkinter import messagebox

import customtkinter as ctk

from .generator import export_wordlist, generate_wordlist
from .history import SessionHistory
from .logger import get_logger
from .utils import (
    ensure_dir,
    estimate_entropy,
    parse_csv,
    safe_int,
    strength_label,
)

logger = get_logger()

# Theme colours per requirements
BG = "#000000"
CARD = "#111111"
BORDER = "#00FF66"
ACCENT = "#00FF66"
ACCENT2 = "#00FFFF"
CONSOLE_FONT = "Consolas"

DEFAULT_SETTINGS = {
    "theme": "dark",
    "font_size": 11,
    "autosave": False,
    "autocopy": False,
    "default_password_count": 1000,
    "default_export_format": "txt",
    "output_folder": "output",
}


class HackerUI(ctk.CTk):
    """Main CTk application window.

    Uses a responsive grid layout. Left panel contains inputs; right panel
    contains output, search and statistics.
    """

    def __init__(self, settings: dict | None = None):
        super().__init__()
        self.title("H4CK3R WORDLIST GENERATOR")
        self.geometry("1200x800")
        self.minsize(900, 700)
        self.configure(fg_color=BG)

        # CTk appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # State
        self.candidates: List[str] = []
        self.filtered_candidates: List[str] | None = None
        self.current_page = 1
        self.page_size = 30
        self._generating = False
        self._progress_after_id: str | None = None

        base = Path(__file__).resolve().parents[1]
        self.presets_path = base / "presets.json"
        self.history_path = base / "history.json"
        self.history = SessionHistory(self.history_path)
        self.settings = settings or {
            **DEFAULT_SETTINGS,
            "output_folder": str(base / "output"),
        }
        self.settings_path = base / "settings.json"
        if self.settings_path.exists():
            try:
                loaded = json.loads(self.settings_path.read_text(encoding="utf-8"))
                self.settings.update(loaded)
            except Exception:
                logger.exception("Failed to load settings")
        ensure_dir(Path(self.settings["output_folder"]))
        self._apply_settings()

        # Layout: 2 columns, left inputs (col 0), right output/stats (col 1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._build_left()
        self._build_right()
        self._bind_shortcuts()
        self._build_statusbar()

    def _build_left(self):
        """Build the left-side profile form and action controls."""
        frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=6, border_width=2, border_color=BORDER)
        frame.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        frame.grid_rowconfigure(12, weight=1)

        lbl = ctk.CTkLabel(
            frame,
            text="H4CKSMITH - Profile",
            fg_color=None,
            text_color=ACCENT,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        lbl.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6))

        font_size = int(self.settings.get("font_size", DEFAULT_SETTINGS["font_size"]))
        entry_font = ctk.CTkFont(size=font_size)
        default_password_count = int(self.settings.get("default_password_count", DEFAULT_SETTINGS["default_password_count"]))

        self._build_profile_inputs(frame, entry_font, default_password_count)
        self._build_profile_actions(frame)
        self._build_contextual_help(frame)
        self._build_strength_meter(frame)

    def _build_profile_inputs(self, frame, entry_font, default_password_count: int):
        """Create the profile form entries and progress widgets."""
        self.basic_profile_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.basic_profile_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 6))
        self.basic_profile_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.basic_profile_frame,
            text="Basic Profile",
            text_color=ACCENT,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=0, pady=(0, 6))

        self.entry_name = ctk.CTkEntry(self.basic_profile_frame, placeholder_text="Enter your Name", font=entry_font)
        self.entry_name.grid(row=1, column=0, sticky="ew", pady=6)

        self.entry_dob = ctk.CTkEntry(self.basic_profile_frame, placeholder_text="DD/MM/YYYY", font=entry_font)
        self.entry_dob.grid(row=2, column=0, sticky="ew", pady=6)

        self.entry_nick = ctk.CTkEntry(self.basic_profile_frame, placeholder_text="Enter Nickname", font=entry_font)
        self.entry_nick.grid(row=3, column=0, sticky="ew", pady=6)

        self.entry_interests = ctk.CTkEntry(self.basic_profile_frame, placeholder_text="Enter Interests (comma separated)", font=entry_font)
        self.entry_interests.grid(row=4, column=0, sticky="ew", pady=6)

        self.entry_password = ctk.CTkEntry(self.basic_profile_frame, placeholder_text="Enter Password", show="*", font=entry_font)
        self.entry_password.grid(row=5, column=0, sticky="ew", pady=6)

        self.entry_preview = ctk.CTkEntry(self.basic_profile_frame, placeholder_text="30", font=entry_font)
        self.entry_preview.grid(row=6, column=0, sticky="ew", pady=6)

        self.advanced_toggle = ctk.CTkButton(
            self.basic_profile_frame,
            text="▾ Advanced Options",
            fg_color=ACCENT2,
            command=self._toggle_advanced_section,
        )
        self.advanced_toggle.grid(row=7, column=0, sticky="ew", pady=(6, 0))

        self.advanced_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.advanced_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 6))
        self.advanced_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.advanced_frame,
            text="Advanced Options",
            text_color=ACCENT,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.entry_suffixes = ctk.CTkEntry(self.advanced_frame, placeholder_text="123,@123,2026", font=entry_font)
        self.entry_suffixes.grid(row=1, column=0, sticky="ew", pady=6)

        self.entry_separators = ctk.CTkEntry(self.advanced_frame, placeholder_text="@,-,_", font=entry_font)
        self.entry_separators.grid(row=2, column=0, sticky="ew", pady=6)

        ctk.CTkLabel(
            self.advanced_frame,
            text="Number of Passwords",
            text_color=ACCENT,
            font=ctk.CTkFont(size=int(self.settings.get("font_size", DEFAULT_SETTINGS["font_size"]))),
        ).grid(row=3, column=0, sticky="w", pady=(6, 0))

        quick_count_frame = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        quick_count_frame.grid(row=4, column=0, sticky="ew", pady=(4, 6))
        quick_count_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        quick_counts = (100, 500, 1000, 5000)
        for index, count_value in enumerate(quick_counts):
            ctk.CTkButton(
                quick_count_frame,
                text=str(count_value),
                width=70,
                command=lambda value=count_value: self._apply_password_count(value),
            ).grid(row=0, column=index, sticky="ew", padx=(0, 4), pady=4)

        self.entry_password_count = ctk.CTkEntry(self.advanced_frame, placeholder_text=str(default_password_count), font=entry_font)
        self.entry_password_count.insert(0, str(default_password_count))
        self.entry_password_count.grid(row=5, column=0, sticky="ew", pady=(6, 0))

        self.progress_status_var = ctk.StringVar(value="Generating Wordlist...\nPlease Wait...")
        self.progress_status_label = ctk.CTkLabel(
            frame,
            textvariable=self.progress_status_var,
            text_color=ACCENT2,
            justify="left",
            anchor="w",
        )
        self.progress_status_label.grid(row=8, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 0))

        self.progress_pct_var = ctk.StringVar(value="0%")
        self.progress_pct_label = ctk.CTkLabel(frame, textvariable=self.progress_pct_var, text_color=ACCENT, anchor="e")
        self.progress_pct_label.grid(row=9, column=1, sticky="e", padx=(0, 12), pady=(0, 2))

        self.progress = ctk.CTkProgressBar(
            frame,
            width=260,
            progress_color=ACCENT,
            corner_radius=6,
            fg_color=BG,
        )
        self.progress.set(0.0)
        self.progress.grid(row=9, column=0, sticky="ew", padx=12, pady=(0, 6))

    def _build_profile_actions(self, frame):
        """Create the primary action buttons for the left pane."""
        self.btn_generate = ctk.CTkButton(frame, text="Generate", fg_color=ACCENT, command=self._on_generate)
        self.btn_generate.grid(row=13, column=0, sticky="ew", padx=(12, 6), pady=12)

        self.btn_copy = ctk.CTkButton(frame, text="Copy", fg_color=ACCENT2, command=self._on_copy)
        self.btn_copy.grid(row=13, column=1, sticky="ew", padx=(6, 12), pady=12)

        self.btn_save = ctk.CTkButton(frame, text="Save", command=self._on_save)
        self.btn_save.grid(row=14, column=0, sticky="ew", padx=(12, 6), pady=6)

        self.btn_saveas = ctk.CTkButton(frame, text="Save As", command=self._on_save_as)
        self.btn_saveas.grid(row=14, column=1, sticky="ew", padx=(6, 12), pady=6)

        self.btn_clear = ctk.CTkButton(frame, text="Clear", fg_color="#FF5555", command=self._on_clear)
        self.btn_clear.grid(row=15, column=0, columnspan=2, sticky="ew", padx=12, pady=(6, 12))

        self.btn_reset_profile = ctk.CTkButton(frame, text="Reset Profile", fg_color=ACCENT2, command=self._on_reset_profile)
        self.btn_reset_profile.grid(row=16, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))

        btn_frame = ctk.CTkFrame(frame, fg_color=None, corner_radius=0)
        btn_frame.grid(row=0, column=2, sticky="e", padx=6)
        btn_settings = ctk.CTkButton(btn_frame, text="⚙", width=36, command=self._open_settings)
        btn_settings.grid(row=0, column=0, padx=(0, 6))
        btn_help = ctk.CTkButton(btn_frame, text="?", width=36, command=self._open_help)
        btn_help.grid(row=0, column=1)

    def _build_contextual_help(self, frame):
        """Create the contextual help label and attach help text to form inputs."""
        self.help_var = ctk.StringVar(value="")
        self.help_label = ctk.CTkLabel(frame, textvariable=self.help_var, text_color=ACCENT2, anchor="w")
        self.help_label.grid(row=14, column=0, columnspan=3, sticky="ew", padx=12, pady=(2, 8))

        self._attach_help(self.entry_name, "Enter the person's full name", shortcut="Ctrl+G to generate")
        self._attach_help(self.entry_dob, "Date of birth (DD/MM/YYYY) - digits used by generator")
        self._attach_help(self.entry_nick, "Optional nickname used in profile generation")
        self._attach_help(self.entry_interests, "Comma-separated interests (e.g. hacker,code)")
        self._attach_help(self.entry_password_count, "How many passwords to generate (positive integer)")
        self._attach_help(self.entry_suffixes, "Comma-separated suffixes to append")
        self._attach_help(self.entry_separators, "Comma-separated separators to use")
        self._attach_help(self.entry_preview, "How many results to display per page")

    def _build_strength_meter(self, frame):
        """Create the strength meter widget at the bottom of the profile pane."""
        self.strength_var = ctk.StringVar(value="Strength: N/A")
        self.lbl_strength = ctk.CTkLabel(frame, textvariable=self.strength_var, text_color=ACCENT)
        self.lbl_strength.grid(row=16, column=0, columnspan=2, sticky="w", padx=12, pady=(6, 2))

    def _build_right(self):
        frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=6, border_width=2, border_color=BORDER)
        frame.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Search row
        top = ctk.CTkFrame(frame, fg_color=BG)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="Search:", text_color=ACCENT2).grid(row=0, column=0, padx=(0, 6))
        self.entry_search = ctk.CTkEntry(top, placeholder_text="Filter output...")
        self.entry_search.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.entry_search.bind("<KeyRelease>", lambda e: self._apply_filter())

        self.search_case_var = ctk.BooleanVar(value=False)
        self.search_case_checkbox = ctk.CTkCheckBox(
            top,
            text="Case Sensitive",
            variable=self.search_case_var,
            onvalue=True,
            offvalue=False,
            command=self._apply_filter,
        )
        self.search_case_checkbox.grid(row=0, column=2, padx=(0, 6))

        self.btn_clear_search = ctk.CTkButton(top, text="Clear Search", command=self._clear_search)
        self.btn_clear_search.grid(row=0, column=3, padx=(0, 6))

        self.lbl_search_matches = ctk.CTkLabel(top, text="Total Matches: 0", text_color=ACCENT2)
        self.lbl_search_matches.grid(row=1, column=0, columnspan=4, sticky="w", padx=(0, 6), pady=(6, 0))

        # Statistics card above the output pane
        stats = ctk.CTkFrame(frame, fg_color=BG, corner_radius=8, border_width=2, border_color=ACCENT)
        stats.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        stats.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(stats, text="Statistics", text_color=ACCENT, font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 8), sticky="w")

        self.lbl_total = ctk.CTkLabel(stats, text="Total Passwords: 0", text_color=ACCENT)
        self.lbl_total.grid(row=1, column=0, padx=12, pady=4, sticky="w")
        self.lbl_time = ctk.CTkLabel(stats, text="Generation Time: 0.00s", text_color=ACCENT)
        self.lbl_time.grid(row=1, column=1, padx=12, pady=4, sticky="e")

        self.lbl_unique = ctk.CTkLabel(stats, text="Unique Passwords: 0", text_color=ACCENT)
        self.lbl_unique.grid(row=2, column=0, padx=12, pady=4, sticky="w")
        self.lbl_filesize = ctk.CTkLabel(stats, text="File Size: 0 bytes", text_color=ACCENT)
        self.lbl_filesize.grid(row=2, column=1, padx=12, pady=4, sticky="e")

        self.lbl_duplicates = ctk.CTkLabel(stats, text="Duplicate Count: 0", text_color=ACCENT2)
        self.lbl_duplicates.grid(row=3, column=0, padx=12, pady=(4, 10), sticky="w")
        self.lbl_avg_length = ctk.CTkLabel(stats, text="Average Length: 0.00", text_color=ACCENT2)
        self.lbl_avg_length.grid(row=3, column=1, padx=12, pady=(4, 10), sticky="e")

        # Output textbox (scrollable)
        self.txt_output = ctk.CTkTextbox(frame, width=800, corner_radius=6)
        self.txt_output.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._output_text = self.txt_output._textbox
        self._output_text.tag_configure("match", background=ACCENT, foreground="#111111")

        # Export buttons row
        bottom = ctk.CTkFrame(frame, fg_color=BG)
        bottom.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))

        btn_txt = ctk.CTkButton(bottom, text="Export TXT", command=lambda: self._export("txt"))
        btn_txt.grid(row=0, column=0, padx=6)
        btn_csv = ctk.CTkButton(bottom, text="Export CSV", command=lambda: self._export("csv"))
        btn_csv.grid(row=0, column=1, padx=6)
        btn_json = ctk.CTkButton(bottom, text="Export JSON", command=lambda: self._export("json"))
        btn_json.grid(row=0, column=2, padx=6)

        btn_history = ctk.CTkButton(bottom, text="History", fg_color="#333333", command=self._open_history)
        btn_history.grid(row=0, column=4, padx=6)

        # Live clock
        self.clock_var = ctk.StringVar()
        self.lbl_clock = ctk.CTkLabel(bottom, textvariable=self.clock_var, anchor="e")
        self.lbl_clock.grid(row=0, column=3, sticky="e", padx=(12, 0))
        self._update_clock()

        # set default stat labels
        self.lbl_total.configure(text="Total Passwords: 0")
        self.lbl_time.configure(text="Generation Time: 0.00s")
        self.lbl_unique.configure(text="Unique Passwords: 0")
        self.lbl_duplicates.configure(text="Duplicate Count: 0")
        self.lbl_avg_length.configure(text="Average Length: 0.00")
        self.lbl_filesize.configure(text="File Size: 0 bytes")

    def _build_statusbar(self):
        separator = ctk.CTkFrame(self, fg_color=ACCENT, height=1)
        separator.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(12, 12), pady=(0, 0))

        footer = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, border_width=1, border_color=BORDER)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=0)

        self.footer_text_var = ctk.StringVar(value=self._build_footer_text())
        footer_label = ctk.CTkLabel(
            footer,
            textvariable=self.footer_text_var,
            text_color=ACCENT,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            anchor="w",
        )
        footer_label.grid(row=0, column=0, sticky="ew", padx=16, pady=8)

        self.footer_status_var = ctk.StringVar(value="● READY")
        self.footer_status_label = ctk.CTkLabel(
            footer,
            textvariable=self.footer_status_var,
            text_color=ACCENT,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            anchor="e",
        )
        self.footer_status_label.grid(row=0, column=1, sticky="e", padx=16, pady=8)

        self._update_footer_status("READY")

    def _build_footer_text(self) -> str:
        year = datetime.datetime.now().year
        return f"● Developed by Harsh Agre | Cyber Security Major Project | Version 2.0 | © {year}"

    def _update_footer_status(self, state: str):
        color = ACCENT
        text = state.upper()
        if state == "READY":
            color = ACCENT
        elif state == "GENERATING...":
            color = "#FFFF00"
        elif state == "SAVED":
            color = "#3399FF"
        elif state == "ERROR":
            color = "#FF3333"

        self.footer_status_var.set(f"● {text}")
        self.footer_status_label.configure(text_color=color)

    def _bind_shortcuts(self):
        self.bind("<Control-g>", lambda e: self._on_generate())
        self.bind("<Control-s>", lambda e: self._on_save())
        self.bind("<Control-Shift-S>", lambda e: self._on_save_as())
        self.bind("<Control-c>", lambda e: self._on_copy())
        self.bind("<Control-f>", lambda e: self._focus_search())
        self.bind("<Control-r>", lambda e: self._on_reset_profile())
        self.bind("<Control-Delete>", lambda e: self._on_clear())
        self.bind("<F1>", lambda e: self._open_help())
        self.bind("<Control-e>", lambda e: self._export("txt"))

    def _focus_search(self):
        if hasattr(self, "entry_search"):
            self.entry_search.focus_set()
        return "break"

    def _attach_help(self, widget, text: str, shortcut: str | None = None):
        """Attach contextual help that updates the help label when the widget gains focus."""

        def on_focus_in(e):
            msg = text
            if shortcut:
                msg = f"{text}  ({shortcut})"
            self.help_var.set(msg)

        def on_focus_out(e):
            # Clear help when focus is lost
            self.help_var.set("")

        widget.bind("<FocusIn>", on_focus_in)
        widget.bind("<FocusOut>", on_focus_out)

    def _toggle_advanced_section(self):
        """Show or hide the advanced options panel."""
        if self.advanced_frame.winfo_viewable():
            self.advanced_frame.grid_remove()
            self.advanced_toggle.configure(text="▸ Advanced Options")
        else:
            self.advanced_frame.grid()
            self.advanced_toggle.configure(text="▾ Advanced Options")

    def _apply_password_count(self, value: int) -> None:
        """Populate the custom count box with a quick-select value."""
        if value < 1:
            messagebox.showerror("INPUT ERROR", "Number of Passwords must be a positive integer.")
            return
        self.entry_password_count.delete(0, "end")
        self.entry_password_count.insert(0, str(value))

    def _apply_settings(self):
        """Apply persisted appearance settings at startup or after editing."""
        theme = self.settings.get("theme", "dark")
        if theme in {"dark", "light"}:
            ctk.set_appearance_mode(theme)

    def _set_stats_defaults(self):
        """Reset the statistics pane to its default empty state."""
        self.lbl_total.configure(text="Total Passwords: 0")
        self.lbl_filesize.configure(text="File Size: 0 bytes")
        self.lbl_time.configure(text="Generation Time: 0.00s")
        self.lbl_unique.configure(text="Unique Passwords: 0")
        self.lbl_duplicates.configure(text="Duplicate Count: 0")
        self.lbl_avg_length.configure(text="Average Length: 0.00")

    def _record_history(self, action: str, target: str, candidates: int, **meta) -> None:
        """Persist a structured history record with error isolation."""
        try:
            self.history.append(
                action,
                target,
                candidates,
                self.entry_name.get().strip() or "admin",
                **meta,
            )
        except Exception:
            logger.exception("Failed to record history entry")

    def _open_settings(self):
        """Open a professional settings dialog with persisted defaults."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("Settings")
        dlg.geometry("620x420")
        dlg.transient(self)
        dlg.configure(fg_color=CARD)

        header = ctk.CTkLabel(
            dlg,
            text="Application Settings",
            text_color=ACCENT,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.grid(row=0, column=0, columnspan=3, padx=16, pady=(16, 8), sticky="w")

        autosave_var = ctk.BooleanVar(value=self.settings.get("autosave", False))
        autocopy_var = ctk.BooleanVar(value=self.settings.get("autocopy", False))
        theme_var = ctk.StringVar(value=self.settings.get("theme", "dark"))
        font_size_var = ctk.StringVar(value=str(self.settings.get("font_size", 11)))
        default_password_count_var = ctk.StringVar(value=str(self.settings.get("default_password_count", 1000)))
        export_format_var = ctk.StringVar(value=self.settings.get("default_export_format", "txt"))
        out_var = ctk.StringVar(value=self.settings.get("output_folder", ""))

        row = 1
        ctk.CTkLabel(dlg, text="Theme:", text_color=ACCENT2).grid(row=row, column=0, padx=16, pady=8, sticky="w")
        ctk.CTkOptionMenu(dlg, values=["dark", "light"], variable=theme_var).grid(row=row, column=1, padx=16, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(dlg, text="Font Size:", text_color=ACCENT2).grid(row=row, column=0, padx=16, pady=8, sticky="w")
        ctk.CTkOptionMenu(dlg, values=["10", "11", "12", "13", "14"], variable=font_size_var).grid(row=row, column=1, padx=16, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(dlg, text="Auto Save:", text_color=ACCENT2).grid(row=row, column=0, padx=16, pady=8, sticky="w")
        ctk.CTkSwitch(dlg, text="", variable=autosave_var).grid(row=row, column=1, padx=16, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(dlg, text="Auto Copy:", text_color=ACCENT2).grid(row=row, column=0, padx=16, pady=8, sticky="w")
        ctk.CTkSwitch(dlg, text="", variable=autocopy_var).grid(row=row, column=1, padx=16, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(dlg, text="Default Password Count:", text_color=ACCENT2).grid(row=row, column=0, padx=16, pady=8, sticky="w")
        ctk.CTkEntry(dlg, textvariable=default_password_count_var, width=180).grid(row=row, column=1, padx=16, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(dlg, text="Default Export Format:", text_color=ACCENT2).grid(row=row, column=0, padx=16, pady=8, sticky="w")
        ctk.CTkOptionMenu(dlg, values=["txt", "csv", "json"], variable=export_format_var).grid(row=row, column=1, padx=16, pady=8, sticky="w")
        row += 1

        ctk.CTkLabel(dlg, text="Output Folder:", text_color=ACCENT2).grid(row=row, column=0, padx=16, pady=8, sticky="w")
        out_entry = ctk.CTkEntry(dlg, width=300, textvariable=out_var)
        out_entry.grid(row=row, column=1, padx=16, pady=8, sticky="w")

        def _browse():
            from tkinter import filedialog

            selected = filedialog.askdirectory()
            if selected:
                out_var.set(selected)

        ctk.CTkButton(dlg, text="Browse", command=_browse).grid(row=row, column=2, padx=(0, 16), pady=8, sticky="w")

        def save_and_close():
            try:
                normalized_count = safe_int(default_password_count_var.get(), int(self.settings.get("default_password_count", 1000)))
                if normalized_count < 1:
                    raise ValueError("Default Password Count must be a positive integer")
                self.settings["theme"] = theme_var.get()
                self.settings["font_size"] = int(font_size_var.get())
                self.settings["autosave"] = bool(autosave_var.get())
                self.settings["autocopy"] = bool(autocopy_var.get())
                self.settings["default_password_count"] = normalized_count
                self.settings["default_export_format"] = export_format_var.get()
                self.settings["output_folder"] = out_var.get()
                self.settings_path.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
                self._apply_settings()
                self.entry_password_count.delete(0, "end")
                self.entry_password_count.insert(0, str(normalized_count))
            except Exception:
                logger.exception("Failed to save settings")
                messagebox.showerror("Settings", "Unable to save settings. Please verify the values are valid.")
                return
            dlg.destroy()

        actions = ctk.CTkFrame(dlg, fg_color=None)
        actions.grid(row=row + 1, column=0, columnspan=3, padx=16, pady=(12, 16), sticky="e")
        ctk.CTkButton(actions, text="Save", command=save_and_close).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(actions, text="Cancel", command=dlg.destroy).grid(row=0, column=1)
        dlg.grab_set()

    def _open_help(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Help Window")
        dlg.geometry("760x560")
        dlg.transient(self)
        dlg.configure(fg_color=BG)

        scroll = ctk.CTkScrollableFrame(dlg, fg_color=BG, corner_radius=8)
        scroll.pack(fill="both", expand=True, padx=12, pady=12)
        scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            scroll,
            text="Wordlist Generator Help",
            text_color=ACCENT,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=(8, 8), sticky="w")

        ctk.CTkLabel(
            scroll,
            text="Main Buttons",
            text_color=ACCENT2,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=1, column=0, padx=12, pady=(0, 6), sticky="w")

        button_help = (
            "Generate: creates the password list using the profile fields and the Number of Passwords setting.\n"
            "Clear: removes the current output and resets the generated candidates in the working panel.\n"
            "Reset Profile: clears the profile form fields such as Name, DOB, Nickname, Interests, Suffixes, and Separators.\n"
            "Settings: opens the application settings dialog to adjust theme, font size, output folder, and default count.\n"
            "History: opens the session history window showing generated/export activity.\n"
            "Export TXT / CSV / JSON: saves the current wordlist in the selected format.\n"
            "Copy: copies the current visible output into your clipboard.\n"
            "Save / Save As: saves the current output to the configured folder or a custom file path.\n"
            "Clear Search: removes the current search filter and restores the full output.\n"
            "Search: filters the results by text. Enable Case Sensitive for exact matching."
        )
        ctk.CTkLabel(scroll, text=button_help, justify="left", text_color="white", wraplength=680).grid(row=2, column=0, padx=12, pady=(0, 12), sticky="w")

        ctk.CTkLabel(
            scroll,
            text="Keyboard Shortcuts",
            text_color=ACCENT2,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=3, column=0, padx=12, pady=(0, 6), sticky="w")

        shortcuts = (
            "Ctrl+G: Generate a new wordlist\n"
            "Ctrl+E: Export the current results as TXT\n"
            "Ctrl+C: Copy the current visible output\n"
            "Ctrl+Delete: Clear the current session output"
        )
        ctk.CTkLabel(scroll, text=shortcuts, justify="left", text_color="white", wraplength=680).grid(row=4, column=0, padx=12, pady=(0, 12), sticky="w")

        ctk.CTkLabel(
            scroll,
            text="Example Usage",
            text_color=ACCENT2,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=5, column=0, padx=12, pady=(0, 6), sticky="w")

        examples = (
            "Example 1:\n"
            "  Name: John Carter\n"
            "  DOB: 19880412\n"
            "  Interests: hacker,code,linux\n"
            "  Number of Passwords: 500\n"
            "  Suffixes: 2026,admin\n"
            "  Separators: -,_\n"
            "  Result: the generator creates 500 candidates based on those profile tokens.\n\n"
            "Example 2:\n"
            "  Name: Alex Morgan\n"
            "  DOB: 02071992\n"
            "  Nickname: Storm\n"
            "  Interests: purple,code,network\n"
            "  Number of Passwords: 1000\n"
            "  Result: the app builds a larger wordlist and allows you to export it to TXT, CSV, or JSON."
        )
        ctk.CTkLabel(scroll, text=examples, justify="left", text_color="white", wraplength=680).grid(row=6, column=0, padx=12, pady=(0, 12), sticky="w")

        ctk.CTkLabel(
            scroll,
            text="Field Tips",
            text_color=ACCENT2,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=7, column=0, padx=12, pady=(0, 6), sticky="w")

        tips = (
            "Name: primary seed for matching profile combinations\n"
            "DOB: digits are extracted and appended as suffixes where relevant\n"
            "Interests: commas separate multiple keywords that expand candidate strings\n"
            "Suffixes: optional list of appended endings such as 2026 or admin\n"
            "Separators: characters used to join the profile tokens, such as -, _, or spaces"
        )
        ctk.CTkLabel(scroll, text=tips, justify="left", text_color="white", wraplength=680).grid(row=8, column=0, padx=12, pady=(0, 12), sticky="w")

        ctk.CTkButton(scroll, text="Close", command=dlg.destroy, fg_color=ACCENT).grid(row=9, column=0, padx=12, pady=(0, 12), sticky="e")
        dlg.grab_set()

    # ----- Actions -----
    def _disable_action_buttons(self):
        for button in (
            self.btn_generate,
            self.btn_copy,
            self.btn_save,
            self.btn_saveas,
            self.btn_clear,
            self.btn_reset_profile,
        ):
            button.configure(state="disabled")

    def _enable_action_buttons(self):
        for button in (
            self.btn_generate,
            self.btn_copy,
            self.btn_save,
            self.btn_saveas,
            self.btn_clear,
            self.btn_reset_profile,
        ):
            button.configure(state="normal")

    def _start_progress_animation(self):
        if self._progress_after_id is not None:
            self.after_cancel(self._progress_after_id)
        self._progress_after_id = self.after(50, self._tick_progress)

    def _tick_progress(self):
        if not self._generating:
            return
        value = self.progress.get() + 0.03
        if value >= 0.95:
            value = 0.95
        self.progress.set(value)
        self.progress_pct_var.set(f"{int(value * 100)}%")
        self._progress_after_id = self.after(50, self._tick_progress)

    def _stop_progress_animation(self):
        if self._progress_after_id is not None:
            try:
                self.after_cancel(self._progress_after_id)
            except Exception:
                pass
            self._progress_after_id = None

    def _set_progress_state(self, value: float, pct: str, status: str) -> None:
        """Keep the progress bar, percent label, and status label in sync."""
        self.progress.set(value)
        self.progress_pct_var.set(pct)
        self.progress_status_var.set(status)

    def _on_generate(self):
        if self._generating:
            return

        # validate inputs
        name = self.entry_name.get().strip()
        dob = self.entry_dob.get().strip()
        interests = parse_csv(self.entry_interests.get())
        suffixes = parse_csv(self.entry_suffixes.get()) or ["123", "12"]
        separators = parse_csv(self.entry_separators.get()) or ["@", "!", "-", "_"]
        preview = safe_int(self.entry_preview.get(), 30)

        password_count_raw = self.entry_password_count.get().strip()
        if not password_count_raw:
            messagebox.showerror("INPUT ERROR", "Number of Passwords is required.")
            return
        try:
            password_count = int(password_count_raw)
        except ValueError:
            messagebox.showerror("INPUT ERROR", "Number of Passwords must be a positive integer.")
            return
        if password_count < 1:
            messagebox.showerror("INPUT ERROR", "Number of Passwords must be a positive integer.")
            return

        if not name and not interests:
            messagebox.showwarning("INPUT ERROR", "NAME or INTERESTS required")
            return

        self._generating = True
        self._disable_action_buttons()
        self._set_progress_state(0.0, "0%", "Generating Wordlist...\nPlease Wait...")
        self._update_footer_status("GENERATING...")
        self._start_progress_animation()

        def _worker():
            start = time.time()
            try:
                candidates = generate_wordlist(
                    name=name,
                    dob=dob,
                    interests=interests,
                    suffixes=suffixes,
                    separators=separators,
                    count=password_count,
                )
                elapsed = time.time() - start
                self.after(0, self._generation_complete, candidates, elapsed, preview)
            except Exception as exc:
                logger.exception("Generation failed")
                self.after(0, self._generation_failed, exc)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_success_popup(self, generated_count: int, elapsed: float, saved_path: Path):
        dlg = ctk.CTkToplevel(self)
        dlg.title("SUCCESS")
        dlg.geometry("460x280")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(fg_color=CARD)

        ctk.CTkLabel(
            dlg,
            text="✔ Successfully Generated",
            text_color=ACCENT,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(padx=16, pady=(18, 12))

        details = ctk.CTkFrame(dlg, fg_color=CARD)
        details.pack(padx=18, pady=(0, 12), fill="x")

        ctk.CTkLabel(details, text="Total Passwords", text_color=ACCENT2).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=4)
        ctk.CTkLabel(details, text=str(generated_count), text_color="white").grid(row=0, column=1, sticky="w", pady=4)

        ctk.CTkLabel(details, text="Generation Time", text_color=ACCENT2).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=4)
        ctk.CTkLabel(details, text=f"{elapsed:.2f}s", text_color="white").grid(row=1, column=1, sticky="w", pady=4)

        ctk.CTkLabel(details, text="File Name", text_color=ACCENT2).grid(row=2, column=0, sticky="w", padx=(0, 12), pady=4)
        ctk.CTkLabel(details, text=saved_path.name, text_color="white", wraplength=300, justify="left").grid(row=2, column=1, sticky="w", pady=4)

        button_row = ctk.CTkFrame(dlg, fg_color=CARD)
        button_row.pack(padx=18, pady=(0, 18), fill="x")

        def _open_folder():
            try:
                folder = saved_path.parent
                if hasattr(os, "startfile"):
                    os.startfile(str(folder))
                else:
                    messagebox.showinfo("Open Folder", f"Folder: {folder}")
            except Exception:
                logger.exception("Failed to open output folder")
                messagebox.showerror("Open Folder", "Could not open the output folder.")

        ctk.CTkButton(button_row, text="Open Folder", command=_open_folder).pack(side="left", padx=(0, 8))
        ctk.CTkButton(button_row, text="OK", command=dlg.destroy).pack(side="left")

    def _generation_complete(self, candidates: List[str], elapsed: float, preview: int):
        self._stop_progress_animation()
        self._generating = False
        self._set_progress_state(1.0, "100%", "Generation Complete")
        self._enable_action_buttons()

        self.candidates = candidates
        self.filtered_candidates = None
        self.current_page = 1
        self.page_size = max(1, preview)
        self._render_output()

        out_dir = Path(self.settings.get("output_folder", "output"))
        ensure_dir(out_dir)
        output_path = out_dir / "wordlist.txt"
        export_wordlist(self.candidates, str(output_path))
        self._refresh_statistics(candidates, elapsed, output_path)
        self._record_history(
            "generate",
            "in-memory",
            len(candidates),
            generation_time=elapsed,
            total_passwords=len(candidates),
            export_type="generated",
            output_file=str(output_path),
        )

        ent = estimate_entropy(candidates)
        self.lbl_strength.configure(text=f"Strength: {strength_label(ent)}")
        self._update_footer_status(f"Generated {len(candidates)} candidates • Saved to {output_path.as_posix()}")
        self._show_success_popup(len(candidates), elapsed, output_path)

        if self.settings.get("autosave"):
            def _auto_save():
                try:
                    folder = Path(self.settings.get("output_folder"))
                    ensure_dir(folder)
                    name = datetime.datetime.utcnow().strftime("wordlist_%Y%m%d_%H%M%S.txt")
                    target = folder / name
                    export_wordlist(self.candidates, str(target))
                    self.lbl_filesize.configure(text=f"File Size: {target.stat().st_size} bytes")
                    self._record_history(
                        "autosave",
                        str(target),
                        len(self.candidates),
                        total_passwords=len(self.candidates),
                        export_type="txt",
                        output_file=str(target),
                    )
                    self._update_footer_status(f"Auto-saved to {target}")
                except Exception:
                    logger.exception("Auto-save failed")

            threading.Thread(target=_auto_save, daemon=True).start()

    def _generation_failed(self, exc: Exception):
        self._stop_progress_animation()
        self._generating = False
        self._set_progress_state(0.0, "0%", "Generation Failed")
        self._enable_action_buttons()
        self._update_footer_status("ERROR")
        logger.exception("Generation failed")
        messagebox.showerror("ERROR", f"Generation failed: {exc}")

    def _render_output(self):
        src = self.filtered_candidates if self.filtered_candidates is not None else self.candidates
        text = "".join(f"[{i+1}] {w}\n" for i, w in enumerate(src))

        self.txt_output.configure(state="normal")
        self.txt_output.delete("0.0", "end")
        self._output_text.tag_remove("match", "1.0", "end")
        self.txt_output.insert("0.0", text)

        query = self.entry_search.get().strip()
        if query:
            searchable_query = query if self.search_case_var.get() else query.lower()
            for index, candidate in enumerate(src, start=1):
                prefix = f"[{index}] "
                prefix_len = len(prefix)
                target = candidate if self.search_case_var.get() else candidate.lower()
                start_pos = 0
                while True:
                    match_index = target.find(searchable_query, start_pos)
                    if match_index == -1:
                        break
                    start_col = prefix_len + match_index
                    end_col = start_col + len(query)
                    self._output_text.tag_add("match", f"{index}.{start_col}", f"{index}.{end_col}")
                    start_pos = match_index + len(query)

        self.txt_output.configure(state="disabled")
        self.lbl_search_matches.configure(text=f"Total Matches: {len(src)}")

    def _apply_filter(self):
        q = self.entry_search.get().strip()
        if not q:
            self.filtered_candidates = None
        else:
            q_search = q if self.search_case_var.get() else q.lower()
            self.filtered_candidates = [
                c for c in self.candidates if (c if self.search_case_var.get() else c.lower()).find(q_search) != -1
            ]
        self._render_output()

    def _clear_search(self):
        self.entry_search.delete(0, "end")
        self.filtered_candidates = None
        self._render_output()

    def _on_copy(self):
        try:
            self.clipboard_clear()
            self.clipboard_append("\n".join(self.candidates))
        except Exception:
            pass

    def _refresh_statistics(self, candidates: List[str], elapsed: float, output_path: Path | None = None):
        total = len(candidates)
        unique = len(set(candidates))
        duplicates = max(0, total - unique)
        avg_length = round(sum(len(item) for item in candidates) / total, 2) if total else 0.0
        file_size = output_path.stat().st_size if output_path and output_path.exists() else 0

        self.lbl_total.configure(text=f"Total Passwords: {total}")
        self.lbl_time.configure(text=f"Generation Time: {elapsed:.2f}s")
        self.lbl_unique.configure(text=f"Unique Passwords: {unique}")
        self.lbl_duplicates.configure(text=f"Duplicate Count: {duplicates}")
        self.lbl_avg_length.configure(text=f"Average Length: {avg_length:.2f}")
        self.lbl_filesize.configure(text=f"File Size: {file_size} bytes")

    def _write_export_file(self, path: str, fmt: str) -> None:
        """Write the current candidate set to disk in the requested format."""
        if fmt == "txt":
            export_wordlist(self.candidates, path)
            return

        if fmt == "csv":
            import csv

            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                for candidate in self.candidates:
                    writer.writerow([candidate])
            return

        if fmt == "json":
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.candidates, fh, indent=2)
            return

        raise ValueError(f"Unsupported export format: {fmt}")

    def _on_save(self):
        """Save the current candidates to the configured default output folder."""
        folder = Path(self.settings.get("output_folder"))
        ensure_dir(folder)
        path = folder / "wordlist.txt"
        self._write_export_file(str(path), "txt")
        self.lbl_filesize.configure(text=f"File Size: {path.stat().st_size} bytes")
        self._record_history(
            "save",
            str(path),
            len(self.candidates),
            total_passwords=len(self.candidates),
            export_type="txt",
            output_file=str(path),
        )
        self._update_footer_status("SAVED")

    def _on_save_as(self):
        """Save the current candidates to a user-chosen file path."""
        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return

        self._write_export_file(path, "txt")
        self.lbl_filesize.configure(text=f"File Size: {Path(path).stat().st_size} bytes")
        self._record_history(
            "save",
            str(path),
            len(self.candidates),
            total_passwords=len(self.candidates),
            export_type="txt",
            output_file=str(path),
        )
        self._update_footer_status("SAVED")

    def _on_clear(self):
        confirmed = messagebox.askyesno(
            "Clear",
            "Do you really want to clear all generated passwords and profile data?",
        )
        if not confirmed:
            return

        self.txt_output.delete("0.0", "end")
        self.entry_search.delete(0, "end")
        self.candidates = []
        self.filtered_candidates = None
        self._set_stats_defaults()
        self.strength_var.set("Strength: N/A")
        self.progress_pct_var.set("0%")
        self.progress.set(0.0)

    def _clear_profile_fields(self):
        """Clear only the profile-related form fields while preserving outputs."""
        self.entry_name.delete(0, "end")
        self.entry_dob.delete(0, "end")
        self.entry_interests.delete(0, "end")
        self.entry_nick.delete(0, "end")
        self.entry_password.delete(0, "end")
        self.entry_suffixes.delete(0, "end")
        self.entry_separators.delete(0, "end")
        self.entry_password_count.delete(0, "end")
        self.entry_password_count.insert(0, str(self.settings.get("default_password_count", DEFAULT_SETTINGS["default_password_count"])))

    def _on_reset_profile(self):
        self._clear_profile_fields()

    def _show_export_success_popup(self, path: str):
        dlg = ctk.CTkToplevel(self)
        dlg.title("EXPORT SUCCESS")
        dlg.geometry("460x220")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(fg_color=CARD)

        ctk.CTkLabel(
            dlg,
            text="✔ Export Complete",
            text_color=ACCENT,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(padx=16, pady=(18, 10))

        ctk.CTkLabel(
            dlg,
            text=f"Exported file:\n{path}",
            justify="left",
            text_color="white",
        ).pack(padx=18, pady=(0, 14), anchor="w")

        ctk.CTkButton(dlg, text="OK", command=dlg.destroy).pack(pady=(0, 18))

    def _export(self, fmt: str = "txt"):
        from tkinter import filedialog

        if not self.candidates:
            messagebox.showinfo("EXPORT", "No candidates to export")
            return

        filetypes = {
            "txt": [("Text Files", "*.txt"), ("All Files", "*.*")],
            "csv": [("CSV Files", "*.csv"), ("All Files", "*.*")],
            "json": [("JSON Files", "*.json"), ("All Files", "*.*")],
        }

        path = filedialog.asksaveasfilename(
            defaultextension=f".{fmt}",
            filetypes=filetypes.get(fmt, [("All Files", "*.*")]),
        )
        if not path:
            return

        self._write_export_file(path, fmt)
        self.lbl_filesize.configure(text=f"File Size: {Path(path).stat().st_size} bytes")
        self._record_history(
            "export",
            path,
            len(self.candidates),
            total_passwords=len(self.candidates),
            export_type=fmt,
            output_file=path,
        )
        self._show_export_success_popup(path)

    def _open_history(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Session History")
        dlg.geometry("760x480")
        dlg.transient(self)
        dlg.grid_columnconfigure(0, weight=1)
        dlg.grid_rowconfigure(0, weight=1)

        history_scroll = ctk.CTkScrollableFrame(dlg, corner_radius=6)
        history_scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        history_scroll.grid_columnconfigure(0, weight=1)

        self._refresh_history(history_scroll)

        controls = ctk.CTkFrame(dlg, fg_color=BG)
        controls.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        ctk.CTkButton(controls, text="Refresh", command=lambda: self._refresh_history(history_scroll)).grid(row=0, column=0, padx=6)
        ctk.CTkButton(controls, text="Clear History", fg_color="#FF5555", hover_color="#FF7777", command=lambda: self._clear_history(history_scroll)).grid(row=0, column=1, padx=6)
        ctk.CTkButton(controls, text="Close", command=dlg.destroy).grid(row=0, column=2, padx=6)

        dlg.grab_set()

    def _refresh_history(self, history_container):
        for widget in history_container.winfo_children():
            widget.destroy()

        if not self.history.list():
            ctk.CTkLabel(history_container, text="No history entries yet.", text_color=ACCENT2).grid(row=0, column=0, padx=12, pady=12, sticky="w")
            return

        for row, entry in enumerate(self.history.list()):
            card = ctk.CTkFrame(history_container, fg_color=CARD, corner_radius=6, border_width=1)
            card.grid(row=row, column=0, sticky="ew", padx=12, pady=(0, 8))
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(card, text=SessionHistory.format_entry(entry), text_color=ACCENT, anchor="w").grid(row=0, column=0, padx=10, pady=(10, 4), sticky="w")
            for col, field in enumerate(SessionHistory.format_fields(entry)):
                ctk.CTkLabel(card, text=field, text_color=ACCENT2, anchor="w").grid(row=col + 1, column=0, padx=10, pady=(0, 4), sticky="w")

    def _clear_history(self, history_container):
        self.history.clear()
        self._refresh_history(history_container)

    def _update_clock(self):
        self.clock_var.set(time.strftime("%Y-%m-%d %H:%M:%S"))
        self.after(1000, self._update_clock)


__all__ = ["HackerUI"]
