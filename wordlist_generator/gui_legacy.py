"""
Legacy Tkinter GUI (archived)

This file contains the previous Tkinter-based GUI implementation. It is
archived for reference and debugging; the active UI has been migrated to
`ui.py` using CustomTkinter.
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
from typing import Iterable, List, Optional

from .generator import export_wordlist, generate_wordlist

# Setup application logging
LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "app.log"
logger = logging.getLogger("h4cksmith")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    # also console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

# ── Colour palette ──────────────────────────────────────────────────
BG_BLACK = "#000000"
GREEN_NEON = "#00FF00"
GREEN_DIM = "#003300"
GREEN_MED = "#008800"
CYAN_NEON = "#00FFFF"
MAGENTA_NEON = "#FF00FF"
YELLOW_NEON = "#FFFF00"
WHITE = "#FFFFFF"
GRAY_DIM = "#1A1A1A"
GRAY_MED = "#333333"
GRAY_TEXT = "#888888"

FONT_FAMILY = "Courier New"
FONT_SIZE_SM = 9
FONT_SIZE_MD = 11
FONT_SIZE_LG = 14
FONT_SIZE_XL = 18

# ── Matrix characters ───────────────────────────────────────────────
MATRIX_CHARS = (
    "アイウエオカキクケコサシスセソタチツテトナニヌネノ"
    "ハヒフヘホマミムメモヤユヨラリルレロワヲン"
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
)

# ── Skull ASCII Art ─────────────────────────────────────────────────
SKULL_ART = r"""
    ╔════════════════════════════════════════════════════════╗
    ║  _   _            _    _ _____ _     _ _ _            ║
    ║ | | | | __ _  ___| | _| |_   _| |__ (_) | | ___ _ __  ║
    ║ | |_| |/ _` |/ __| |/ / | | | | '_ \| | | |/ _ \ '__| ║
    ║ |  _  | (_| | (__|   <| | | | | | | | | | |  __/ |    ║
    ║ |_| |_|\__,_|\___|_|\_\_| |_| |_| |_|_|_|_|\___|_|    ║
    ║                                                        ║
    ║           H A C K S M I T H   W O R D L I S T          ║
    ║               Generator • GUI Mode v2.1               ║
    ╠════════════════════════════════════════════════════════╣
    ║  >> custom patterns • presets • filter • copy/export   ║
    ╚════════════════════════════════════════════════════════╝
"""


class MatrixRain:
    """Matrix digital rain effect rendered on a tkinter Canvas."""

    def __init__(self, canvas: tk.Canvas, width: int, height: int, speed: int = 60):
        self.canvas = canvas
        self.width = width
        self.height = height
        self.speed = speed  # ms between frames
        self._running = False
        self._columns: List[dict] = []
        self._drops: List[int] = []
        self._after_id: Optional[str] = None

        # Character cell size
        self.font_size = 12
        self.cell_w = 10
        self.cell_h = 16

        # Initialise columns
        self.num_cols = width // self.cell_w
        self._drops = [random.randint(-30, 0) for _ in range(self.num_cols)]

    def start(self):
        self._running = True
        self._animate()

    def stop(self):
        self._running = False
        if self._after_id:
            self.canvas.after_cancel(self._after_id)
            self._after_id = None

    def _animate(self):
        if not self._running:
            return

        self.canvas.delete("matrix")

        for col in range(self.num_cols):
            # Draw a trailing column of characters
            y = self._drops[col] * self.cell_h
            for i in range(random.randint(1, 5)):
                char_y = y - i * self.cell_h
                if 0 <= char_y <= self.height:
                    char = random.choice(MATRIX_CHARS)
                    # Brightness fades with distance from head
                    if i == 0:
                        color = WHITE
                    elif i == 1:
                        color = CYAN_NEON
                    elif i == 2:
                        color = GREEN_NEON
                    else:
                        color = GREEN_DIM
                    self.canvas.create_text(
                        col * self.cell_w + self.cell_w // 2,
                        char_y,
                        text=char,
                        fill=color,
                        font=(FONT_FAMILY, self.font_size, "bold"),
                        tags="matrix",
                    )

            # Random chance to reset a column
            if self._drops[col] * self.cell_h > self.height and random.random() < 0.05:
                self._drops[col] = 0
            else:
                self._drops[col] += 1

        self._after_id = self.canvas.after(self.speed, self._animate)


class HackerButton(tk.Canvas):
    """Custom-styled button with hover glow effect."""

    def __init__(
        self,
        parent,
        text: str,
        command,
        width: int = 180,
        height: int = 40,
        bg_color: str = GREEN_DIM,
        fg_color: str = GREEN_NEON,
        hover_color: str = GREEN_MED,
        font_size: int = FONT_SIZE_MD,
        **kwargs,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=BG_BLACK,
            highlightthickness=0,
            **kwargs,
        )
        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color
        self.font_size = font_size
        self.text = text
        self.button_width = width
        self.button_height = height

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self._draw()

    def _draw(self, bg=None):
        self.delete("all")
        bg = bg or self.bg_color
        r = 5  # corner radius

        # Border rect
        self.create_rounded_rect(r, r, self.button_width - r, self.button_height - r, r, outline=GREEN_NEON, width=1)
        # Fill rect
        self.create_rounded_rect(r + 2, r + 2, self.button_width - r - 2, self.button_height - r - 2, r - 1, fill=bg, outline="")

        # Text
        self.create_text(
            self.button_width // 2,
            self.button_height // 2,
            text=self.text,
            fill=self.fg_color,
            font=(FONT_FAMILY, self.font_size, "bold"),
        )

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_enter(self, event):
        self._draw(bg=self.hover_color)
        self.config(cursor="hand2")

    def _on_leave(self, event):
        self._draw(bg=self.bg_color)
        self.config(cursor="")

    def _on_click(self, event):
        if self.command:
            self.command()


class HackerEntry(tk.Frame):
    """Styled input field with neon label and dark entry widget."""

    def __init__(
        self,
        parent,
        label: str,
        default: str = "",
        width: int = 40,
        **kwargs,
    ):
        super().__init__(parent, bg=BG_BLACK, **kwargs)

        self.label_text = label
        self.default = default

        # Label
        self.lbl = tk.Label(
            self,
            text=f">> {label}:",
            fg=CYAN_NEON,
            bg=BG_BLACK,
            font=(FONT_FAMILY, FONT_SIZE_SM, "bold"),
            anchor="w",
        )
        self.lbl.pack(fill="x", pady=(4, 0))

        # Entry
        self.entry = tk.Entry(
            self,
            width=width,
            bg=GRAY_DIM,
            fg=GREEN_NEON,
            insertbackground=GREEN_NEON,
            font=(FONT_FAMILY, FONT_SIZE_MD),
            relief="flat",
            bd=2,
            highlightthickness=1,
            highlightcolor=GREEN_MED,
            highlightbackground=GRAY_DIM,
        )
        self.entry.pack(fill="x", pady=(2, 6), ipady=3)
        if default:
            self.entry.insert(0, default)

    def get(self) -> str:
        return self.entry.get().strip()

    def clear(self):
        self.entry.delete(0, tk.END)

    def set(self, value: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)


class ProgressBar(tk.Canvas):
    """Hacker-style animated progress bar."""

    def __init__(self, parent, width: int = 400, height: int = 24, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=BG_BLACK,
            highlightthickness=0,
            **kwargs,
        )
        self.bar_width = width
        self.bar_height = height
        self._progress = 0.0
        self._target = 0.0
        self._running = False
        self._after_id = None
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.bar_width
        h = self.bar_height

        # Outer border
        self.create_rectangle(2, 2, w - 2, h - 2, outline=GREEN_NEON, width=1)

        # Fill
        fill_w = int((w - 6) * self._progress)
        if fill_w > 0:
            self.create_rectangle(4, 4, 4 + fill_w, h - 4, fill=GREEN_NEON, outline="")

        # Percentage text
        pct = int(self._progress * 100)
        self.create_text(
            w // 2,
            h // 2,
            text=f"[ {'█' * (pct // 10)}{'░' * (10 - pct // 10)} ] {pct:3d}%",
            fill=BG_BLACK,
            font=(FONT_FAMILY, FONT_SIZE_SM, "bold"),
        )

    def set_progress(self, value: float):
        self._target = max(0.0, min(1.0, value))
        if not self._running:
            self._running = True
            self._animate()

    def _animate(self):
        if abs(self._progress - self._target) < 0.01:
            self._progress = self._target
            self._draw()
            self._running = False
            return

        self._progress += (self._target - self._progress) * 0.3
        self._draw()
        self._after_id = self.after(30, self._animate)

    def reset(self):
        self._running = False
        self._progress = 0.0
        self._target = 0.0
        self._draw()


class HackerGUI:
    """Main application window for the H4CK3R Wordlist Generator."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("H4CK3R WORDLIST GENERATOR v2.0")
        self.root.configure(bg=BG_BLACK)

        # Window geometry
        win_width = 900
        win_height = 760
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - win_width) // 2
        y = (screen_h - win_height) // 2
        self.root.geometry(f"{win_width}x{win_height}+{x}+{y}")
        self.root.minsize(700, 650)

        # State
        self.candidates: List[str] = []
        self._generating = False
        self.filtered_candidates: Optional[List[str]] = None
        self.current_page = 1
        self.page_size = 30

        # Presets storage path
        self.presets_path = Path(__file__).resolve().parents[1] / "presets.json"
        # Recent history
        self.history_path = Path(__file__).resolve().parents[1] / "history.json"
        # Settings defaults
        self.settings = {
            "theme": "green",
            "autosave": False,
            "autocopy": False,
            "output_folder": str(Path(__file__).resolve().parents[1] / "output"),
        }
        # Ensure output folder
        Path(self.settings["output_folder"]).mkdir(parents=True, exist_ok=True)

        # ── Build UI ────────────────────────────────────────────────
        self._build_matrix_layer(win_width, win_height)
        self._build_main_frame()
        self._build_menu()
        self._build_header()
        self._build_side_panels()
        self._build_inputs()
        self._build_actions()
        self._build_progress()
        self._build_output()
        self._build_status()

        # Start matrix rain after a short delay
        self.root.after(300, self._start_matrix)

        # Bind keys
        self.root.bind("<Return>", lambda e: self._generate())
        # Keyboard shortcuts
        self.root.bind("<Control-g>", lambda e: self._generate())
        self.root.bind("<Control-e>", lambda e: self._export())
        self.root.bind("<Control-c>", lambda e: self._copy_output())
        self.root.bind("<Control-f>", lambda e: self.entry_filter.focus_set())

        # Protocol for clean shutdown
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Matrix background layer ─────────────────────────────────────
    def _build_matrix_layer(self, width: int, height: int):
        self.matrix_canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg=BG_BLACK,
            highlightthickness=0,
        )
        self.matrix_canvas.place(x=0, y=0, width=width, height=height)
        self.matrix_rain = MatrixRain(self.matrix_canvas, width, height, speed=80)

    def _start_matrix(self):
        self.matrix_rain.start()

    # ── Main content frame ──────────────────────────────────────────
    def _build_main_frame(self):
        self.main_frame = tk.Frame(self.root, bg=BG_BLACK)
        self.main_frame.place(x=0, y=0, relwidth=1, relheight=1)

    # ── Header / Banner ─────────────────────────────────────────────
    def _build_header(self):
        header_frame = tk.Frame(self.main_frame, bg=BG_BLACK)
        header_frame.pack(fill="x", padx=10, pady=(5, 0))

        self.header_text = tk.Text(
            header_frame,
            height=12,
            bg=BG_BLACK,
            fg=GREEN_NEON,
            font=(FONT_FAMILY, FONT_SIZE_SM),
            relief="flat",
            highlightthickness=0,
            padx=5,
            pady=2,
            cursor="arrow",
        )
        self.header_text.insert("1.0", SKULL_ART)
        self.header_text.config(state="disabled")
        self.header_text.pack(fill="x")

        # Glitch effect on header (toggle colours)
        self._glitch_header()

    def _build_side_panels(self):
        # Right-hand column for stats and console logs
        side_frame = tk.Frame(self.main_frame, bg=BG_BLACK)
        side_frame.place(relx=0.66, rely=0.14, relwidth=0.33, relheight=0.72)

        # Statistics panel
        stats_frame = tk.Frame(side_frame, bg=GRAY_DIM)
        stats_frame.pack(fill="x", padx=6, pady=(6, 4))
        tk.Label(stats_frame, text=">> STATISTICS", fg=CYAN_NEON, bg=GRAY_DIM, font=(FONT_FAMILY, FONT_SIZE_SM, "bold")).pack(anchor="w", padx=6, pady=4)
        self.lbl_word_count = tk.Label(stats_frame, text="Words: 0", fg=GREEN_NEON, bg=GRAY_DIM, font=(FONT_FAMILY, FONT_SIZE_SM))
        self.lbl_word_count.pack(anchor="w", padx=8)
        self.lbl_entropy = tk.Label(stats_frame, text="Entropy: 0.0 bits", fg=GREEN_NEON, bg=GRAY_DIM, font=(FONT_FAMILY, FONT_SIZE_SM))
        self.lbl_entropy.pack(anchor="w", padx=8)
        self.lbl_strength = tk.Label(stats_frame, text="Strength: N/A", fg=GREEN_NEON, bg=GRAY_DIM, font=(FONT_FAMILY, FONT_SIZE_SM))
        self.lbl_strength.pack(anchor="w", padx=8)
        self.lbl_gen_time = tk.Label(stats_frame, text="Generation time: 0.00s", fg=GREEN_NEON, bg=GRAY_DIM, font=(FONT_FAMILY, FONT_SIZE_SM))
        self.lbl_gen_time.pack(anchor="w", padx=8)

        # Live console logs
        logs_frame = tk.Frame(side_frame, bg=BG_BLACK)
        logs_frame.pack(fill="both", expand=True, padx=6, pady=(4, 6))
        tk.Label(logs_frame, text=">> CONSOLE", fg=CYAN_NEON, bg=BG_BLACK, font=(FONT_FAMILY, FONT_SIZE_SM, "bold")).pack(anchor="w", padx=6, pady=(2, 4))
        self.txt_console = scrolledtext.ScrolledText(logs_frame, height=12, bg=BG_BLACK, fg=CYAN_NEON, font=(FONT_FAMILY, FONT_SIZE_SM), state="disabled")
        self.txt_console.pack(fill="both", expand=True, padx=6, pady=(0, 4))

        # Hook logger to console
        class TkHandler(logging.Handler):
            def __init__(self, widget):
                super().__init__()
                self.widget = widget

            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.widget.configure(state="normal")
                    self.widget.insert(tk.END, msg + "\n")
                    self.widget.configure(state="disabled")
                    self.widget.yview_moveto(1.0)
                except Exception:
                    pass

        th = TkHandler(self.txt_console)
        th.setLevel(logging.INFO)
        th.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        logger.addHandler(th)

    def _glitch_header(self):
        colours = [GREEN_NEON, CYAN_NEON, GREEN_DIM, GREEN_NEON, MAGENTA_NEON]
        new_fg = random.choice(colours)
        self.header_text.config(fg=new_fg)
        # Random glitch: swap a few characters briefly
        if random.random() < 0.2:
            self.header_text.config(font=(FONT_FAMILY, FONT_SIZE_SM, "bold" if random.random() > 0.5 else "normal"))
        else:
            self.header_text.config(font=(FONT_FAMILY, FONT_SIZE_SM, "normal"))
        self.root.after(random.randint(400, 1200), self._glitch_header)

    # ── Menu bar (Presets) ─────────────────────────────────────────
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        presets_menu = tk.Menu(menubar, tearoff=0)
        presets_menu.add_command(label="Save Preset...", command=self._save_preset)
        # dynamic presets submenu
        self.presets_submenu = tk.Menu(presets_menu, tearoff=0)
        presets_menu.add_cascade(label="Load Preset", menu=self.presets_submenu)
        presets_menu.add_command(label="Refresh Presets", command=self._refresh_presets_menu)
        menubar.add_cascade(label="Presets", menu=presets_menu)
        menubar.add_command(label="Exit", command=self._on_close)
        self.root.config(menu=menubar)
        self._refresh_presets_menu()

    def _read_presets(self) -> dict:
        try:
            if self.presets_path.exists():
                return json.loads(self.presets_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {}

    def _append_history(self, file_path: str):
        try:
            h = []
            if self.history_path.exists():
                h = json.loads(self.history_path.read_text(encoding="utf-8"))
            entry = {"file": str(file_path), "time": time.time()}
            h.insert(0, entry)
            # keep last 20
            h = h[:20]
            self.history_path.write_text(json.dumps(h, indent=2), encoding="utf-8")
            logger.info("Appended history: %s", file_path)
        except Exception:
            logger.exception("Failed to append history")

    def _write_presets(self, data: dict):
        try:
            self.presets_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("PRESET ERROR", f">> Failed to save presets: {exc}")

    def _save_preset(self):
        preset_name = simpledialog.askstring("Save Preset", "Preset name:")
        if not preset_name:
            return
        data = self._read_presets()
        data[preset_name] = {
            "name": self.entry_name.get(),
            "dob": self.entry_dob.get(),
            "interests": self.entry_interests.get(),
            "suffixes": self.entry_suffixes.get(),
            "separators": self.entry_separators.get(),
            "preview": self.entry_preview.get(),
        }
        self._write_presets(data)
        self._refresh_presets_menu()
        messagebox.showinfo("SAVED", f">> Preset '{preset_name}' saved")
        logger.info("Saved preset: %s", preset_name)

    def _load_preset(self, name: str):
        data = self._read_presets()
        if name not in data:
            messagebox.showerror("LOAD ERROR", ">> Preset not found")
            return
        p = data[name]
        # Clear current inputs first so the loaded preset fully replaces them
        self.entry_name.clear()
        self.entry_dob.clear()
        self.entry_interests.clear()
        self.entry_suffixes.clear()
        self.entry_separators.clear()
        self.entry_preview.clear()

        # Populate with preset values
        self.entry_name.set(p.get("name", ""))
        self.entry_dob.set(p.get("dob", ""))
        self.entry_interests.set(p.get("interests", ""))
        self.entry_suffixes.set(p.get("suffixes", ""))
        self.entry_separators.set(p.get("separators", ""))
        self.entry_preview.set(p.get("preview", "30"))

    def _refresh_presets_menu(self):
        self.presets_submenu.delete(0, tk.END)
        data = self._read_presets()
        if not data:
            self.presets_submenu.add_command(label="(no presets)", state="disabled")
            return
        for name in sorted(data.keys()):
            self.presets_submenu.add_command(label=name, command=lambda n=name: self._load_preset(n))

    # ── Input fields ────────────────────────────────────────────────
    def _build_inputs(self):
        input_container = tk.Frame(self.main_frame, bg=BG_BLACK)
        input_container.pack(fill="x", padx=20, pady=(5, 0))

        # Two-column layout for inputs
        left_col = tk.Frame(input_container, bg=BG_BLACK)
        left_col.pack(side="left", fill="x", expand=True, padx=(0, 10))
        right_col = tk.Frame(input_container, bg=BG_BLACK)
        right_col.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.entry_name = HackerEntry(left_col, "NAME", "Enter your name")
        self.entry_name.pack(fill="x")

        self.entry_dob = HackerEntry(left_col, "DOB", "Enter your date of birth")
        self.entry_dob.pack(fill="x")

        self.entry_interests = HackerEntry(left_col, "INTERESTS (comma sep)", "Enter your interests ")
        self.entry_interests.pack(fill="x")

        self.entry_suffixes = HackerEntry(right_col, "SUFFIXES (comma sep)", "Enter suffixes (comma-separated)","123,@123,2026")
        self.entry_suffixes.pack(fill="x")

        self.entry_separators = HackerEntry(right_col, "SEPARATORS (comma sep)", "@, !, -, _")
        self.entry_separators.pack(fill="x")

        self.entry_preview = HackerEntry(right_col, "PREVIEW COUNT", "30")
        self.entry_preview.pack(fill="x")

    # ── Action buttons ──────────────────────────────────────────────
    def _build_actions(self):
        action_frame = tk.Frame(self.main_frame, bg=BG_BLACK)
        action_frame.pack(fill="x", padx=20, pady=(5, 0))

        self.btn_generate = HackerButton(
            action_frame,
            text="[ GENERATE ]",
            command=self._generate,
            width=160,
            height=36,
            bg_color=GREEN_DIM,
            fg_color=GREEN_NEON,
            hover_color=GREEN_MED,
        )
        self.btn_generate.pack(side="left", padx=(0, 10))

        self.btn_export = HackerButton(
            action_frame,
            text="[ EXPORT ]",
            command=self._export,
            width=160,
            height=36,
            bg_color=GRAY_DIM,
            fg_color=CYAN_NEON,
            hover_color=GRAY_MED,
        )
        self.btn_export.pack(side="left", padx=(10, 0))

        self.btn_copy = HackerButton(
            action_frame,
            text="[ COPY ]",
            command=self._copy_output,
            width=120,
            height=36,
            bg_color=GRAY_DIM,
            fg_color=GREEN_NEON,
            hover_color=GRAY_MED,
        )
        self.btn_copy.pack(side="left", padx=(10, 0))

        self.btn_clear = HackerButton(
            action_frame,
            text="[ CLEAR ]",
            command=self._clear_output,
            width=120,
            height=36,
            bg_color=GRAY_DIM,
            fg_color=MAGENTA_NEON,
            hover_color=GRAY_MED,
        )
        self.btn_clear.pack(side="right")

    # ── Progress bar ────────────────────────────────────────────────
    def _build_progress(self):
        progress_frame = tk.Frame(self.main_frame, bg=BG_BLACK)
        progress_frame.pack(fill="x", padx=20, pady=(5, 0))

        self.progress_bar = ProgressBar(progress_frame, width=500, height=24)
        self.progress_bar.pack(side="left")

        self.lbl_status_info = tk.Label(
            progress_frame,
            text="WAITING...",
            fg=GRAY_TEXT,
            bg=BG_BLACK,
            font=(FONT_FAMILY, FONT_SIZE_SM, "bold"),
        )
        self.lbl_status_info.pack(side="right", padx=(10, 0))

    # ── Output panel ───────────────────────────────────────────────
    def _build_output(self):
        output_frame = tk.Frame(self.main_frame, bg=BG_BLACK)
        output_frame.pack(fill="both", expand=True, padx=20, pady=(5, 2))

        # Border label
        lbl_out = tk.Label(
            output_frame,
            text=">> OUTPUT WINDOW",
            fg=CYAN_NEON,
            bg=BG_BLACK,
            font=(FONT_FAMILY, FONT_SIZE_SM, "bold"),
            anchor="w",
        )
        lbl_out.pack(fill="x")

        # Filter entry (small) placed above output for quick filtering
        filter_frame = tk.Frame(output_frame, bg=BG_BLACK)
        filter_frame.pack(fill="x", pady=(4, 4))
        tk.Label(
            filter_frame,
            text=">> FILTER:",
            fg=CYAN_NEON,
            bg=BG_BLACK,
            font=(FONT_FAMILY, FONT_SIZE_SM, "bold"),
        ).pack(side="left", padx=(0, 6))
        self.entry_filter_var = tk.StringVar()
        self.entry_filter = tk.Entry(
            filter_frame,
            textvariable=self.entry_filter_var,
            bg=GRAY_DIM,
            fg=GREEN_NEON,
            insertbackground=GREEN_NEON,
            font=(FONT_FAMILY, FONT_SIZE_MD),
            relief="flat",
            width=40,
        )
        self.entry_filter.pack(side="left", padx=(0, 6))
        self.entry_filter.bind("<KeyRelease>", lambda e: self._apply_filter())

        # Pagination controls
        pag_frame = tk.Frame(output_frame, bg=BG_BLACK)
        pag_frame.pack(fill="x", pady=(2, 6))

        self.btn_prev = tk.Button(
            pag_frame,
            text="◀ Prev",
            command=self._prev_page,
            bg=GRAY_DIM,
            fg=CYAN_NEON,
            relief="flat",
            width=8,
        )
        self.btn_prev.pack(side="left", padx=(0, 6))

        self.lbl_page = tk.Label(
            pag_frame,
            text="Page 1/1",
            fg=GREEN_NEON,
            bg=BG_BLACK,
            font=(FONT_FAMILY, FONT_SIZE_SM, "bold"),
        )
        self.lbl_page.pack(side="left", padx=(0, 8))

        self.btn_next = tk.Button(
            pag_frame,
            text="Next ▶",
            command=self._next_page,
            bg=GRAY_DIM,
            fg=CYAN_NEON,
            relief="flat",
            width=8,
        )
        self.btn_next.pack(side="left", padx=(0, 6))

        tk.Label(
            pag_frame,
            text="Page size:",
            fg=CYAN_NEON,
            bg=BG_BLACK,
            font=(FONT_FAMILY, FONT_SIZE_SM, "bold"),
        ).pack(side="left", padx=(12, 4))

        self.page_size_var = tk.StringVar(value=str(self.page_size))
        self.entry_page_size = tk.Entry(
            pag_frame,
            textvariable=self.page_size_var,
            width=6,
            bg=GRAY_DIM,
            fg=GREEN_NEON,
            relief="flat",
        )
        self.entry_page_size.pack(side="left")
        self.entry_page_size.bind("<Return>", lambda e: self._change_page_size())

        # Text widget
        self.txt_output = scrolledtext.ScrolledText(
            output_frame,
            bg=BG_BLACK,
            fg=GREEN_NEON,
            insertbackground=GREEN_NEON,
            font=(FONT_FAMILY, FONT_SIZE_MD),
            relief="flat",
            bd=2,
            highlightthickness=1,
            highlightcolor=GREEN_MED,
            highlightbackground=GRAY_DIM,
            wrap="none",
            state="disabled",
            cursor="arrow",
        )
        self.txt_output.pack(fill="both", expand=True, pady=(2, 0))

    # ── Status bar ──────────────────────────────────────────────────
    def _build_status(self):
        status_frame = tk.Frame(self.main_frame, bg=GRAY_DIM, height=24)
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)

        self.lbl_status = tk.Label(
            status_frame,
            text=">> SYSTEM READY :: H4CK3R WORDLIST GENERATOR v2.0",
            fg=GREEN_NEON,
            bg=GRAY_DIM,
            font=(FONT_FAMILY, FONT_SIZE_SM, "bold"),
            anchor="w",
        )
        self.lbl_status.pack(fill="x", padx=10, pady=2)

    # ── Core logic ──────────────────────────────────────────────────
    def _parse_csv(self, value: str) -> List[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    def _safe_int(self, value: str, default: int) -> int:
        try:
            return int(value.strip()) if value.strip() else default
        except ValueError:
            return default

    def _generate(self):
        if self._generating:
            return

        self._generating = True
        self.btn_generate.config(state="disabled")
        self.lbl_status.config(text=">> GENERATING WORDLIST...", fg=YELLOW_NEON)
        self.lbl_status_info.config(text="WORKING...", fg=YELLOW_NEON)
        self.progress_bar.set_progress(0.1)

        # Grab input values
        name = self.entry_name.get()
        dob = self.entry_dob.get()
        interests = self._parse_csv(self.entry_interests.get())
        suffixes = self._parse_csv(self.entry_suffixes.get()) or ["123", "12"]
        separators = self._parse_csv(self.entry_separators.get()) or ["@", "!", "-", "_"]
        preview_count = self._safe_int(self.entry_preview.get(), 30)

        if not name and not interests:
            messagebox.showwarning(
                "INPUT ERROR",
                ">> NAME or INTERESTS required for generation!",
            )
            self._generating = False
            self.btn_generate.config(state="normal")
            self.lbl_status.config(text=">> SYSTEM READY", fg=GREEN_NEON)
            self.lbl_status_info.config(text="WAITING...", fg=GRAY_TEXT)
            self.progress_bar.reset()
            return

        # Run generation in a thread
        self._gen_thread = threading.Thread(
            target=self._generate_thread,
            args=(name, dob, interests, suffixes, separators, preview_count),
            daemon=True,
        )
        self._gen_thread.start()

    def _generate_thread(
        self,
        name: str,
        dob: str,
        interests: List[str],
        suffixes: List[str],
        separators: List[str],
        preview_count: int,
    ):
        # Simulate progress steps
        for pct in [0.2, 0.4, 0.6, 0.8]:
            time.sleep(0.15)
            self.root.after(0, self.progress_bar.set_progress, pct)

        start_time = time.time()
        try:
            candidates = generate_wordlist(
                name=name,
                dob=dob,
                interests=interests,
                suffixes=suffixes,
                separators=separators,
            )
            logger.info("Generation completed: %d candidates", len(candidates))
        except Exception as exc:
            logger.exception("Generation failed")
            self.root.after(0, self._generation_error, str(exc))
            return

        elapsed = time.time() - start_time
        self.candidates = candidates
        # Update stats
        self.root.after(0, self._update_stats_after_generation, candidates, elapsed)
        self.root.after(0, self._generation_complete, candidates, preview_count)

    def _generation_complete(self, candidates: List[str], preview_count: int):
        self.progress_bar.set_progress(1.0)
        self.lbl_status_info.config(text="DONE", fg=GREEN_NEON)

        # Store and render
        self.candidates = candidates
        self._render_candidates(candidates, preview_count)

        # Update status
        total = len(candidates)
        self.lbl_status.config(
            text=f">> {total} CANDIDATES GENERATED :: showing {min(preview_count, total)}",
            fg=GREEN_NEON,
        )

        # Re-enable
        self._generating = False
        self.btn_generate.config(state="normal")
        self.lbl_status_info.config(text="READY", fg=CYAN_NEON)

        # Flash the status bar
        self._flash_status()

    def _update_stats_after_generation(self, candidates: List[str], elapsed: float):
        # Word count
        wc = len(candidates)
        self.lbl_word_count.config(text=f"Words: {wc}")
        # Entropy: estimate as log2 of unique chars * avg length
        ent = self._estimate_entropy(candidates)
        self.lbl_entropy.config(text=f"Entropy: {ent:.2f} bits")
        strength = self._strength_label(ent)
        self.lbl_strength.config(text=f"Strength: {strength}")
        self.lbl_gen_time.config(text=f"Generation time: {elapsed:.2f}s")
        logger.info("Updated stats: words=%d entropy=%.2f time=%.2fs", wc, ent, elapsed)

    def _render_candidates(self, candidates: List[str], preview_count: int):
        """Render a list of candidates into the output window with tags."""
        # use pagination: preview_count is page size
        self.page_size = max(1, int(preview_count))
        total = len(candidates)
        total_pages = max(1, math.ceil(total / self.page_size))
        if self.current_page > total_pages:
            self.current_page = total_pages

        start = (self.current_page - 1) * self.page_size
        end = start + self.page_size
        shown = candidates[start:end]

        self.txt_output.config(state="normal")
        self.txt_output.delete("1.0", tk.END)

        header = (
            f"╔{'═' * 60}╗\n"
            f"║ {'GENERATED CANDIDATES':^56} ║\n"
            f"╠{'═' * 60}╣\n"
        )
        self.txt_output.insert(tk.END, header, "header")

        # Tag configuration for coloured output
        self.txt_output.tag_configure("header", foreground=CYAN_NEON)
        self.txt_output.tag_configure("index", foreground=MAGENTA_NEON)
        self.txt_output.tag_configure("candidate", foreground=GREEN_NEON)
        self.txt_output.tag_configure("dim", foreground=GRAY_TEXT)

        for i, cand in enumerate(shown, start=start + 1):
            idx_str = f"[{i:>3}]"
            self.txt_output.insert(tk.END, f"{idx_str}  ", "index")
            self.txt_output.insert(tk.END, f"{cand}\n", "candidate")
        if total > self.page_size:
            remaining = total - end if end < total else 0
            self.txt_output.insert(
                tk.END,
                f"\n╟{'─' * 60}╢\n",
                "dim",
            )
            if remaining > 0:
                self.txt_output.insert(
                    tk.END,
                    f"║ {'... and ' + str(remaining) + ' more candidates':^56} ║\n",
                    "dim",
                )
            self.txt_output.insert(tk.END, f"╚{'═' * 60}╝\n", "dim")

        self.txt_output.config(state="disabled")

        # Update page label
        self.lbl_page.config(text=f"Page {self.current_page}/{total_pages}")

    def _estimate_entropy(self, candidates: List[str]) -> float:
        # Very rough estimate: entropy = avg_length * log2(unique_alphabet_size)
        if not candidates:
            return 0.0
        avg_len = sum(len(c) for c in candidates) / len(candidates)
        alphabet = set("".join(candidates))
        if not alphabet:
            return 0.0
        try:
            ent = avg_len * math.log2(len(alphabet))
        except Exception:
            ent = 0.0
        return ent

    def _strength_label(self, entropy_bits: float) -> str:
        if entropy_bits < 28:
            return "Very Weak"
        if entropy_bits < 36:
            return "Weak"
        if entropy_bits < 60:
            return "Moderate"
        if entropy_bits < 80:
            return "Strong"
        return "Very Strong"

    def _apply_filter(self):
        """Apply the text filter from the filter entry to the current candidates and re-render."""
        if not hasattr(self, "candidates") or not self.candidates:
            return
        q = self.entry_filter_var.get().strip().lower()
        if not q:
            filtered = self.candidates
        else:
            filtered = [c for c in self.candidates if q in c.lower()]
        # reset to first page
        self.filtered_candidates = filtered
        self.current_page = 1
        page_size = self._safe_int(self.page_size_var.get(), self.page_size)
        self._render_candidates(filtered, page_size)

    def _copy_output(self):
        """Copy the currently displayed output (or all candidates) to clipboard."""
        try:
            # If there's a selection in the text widget, copy that; otherwise copy all candidates
            sel = None
            try:
                sel = self.txt_output.get(tk.SEL_FIRST, tk.SEL_LAST)
            except tk.TclError:
                sel = None

            if sel:
                text_to_copy = sel
            elif getattr(self, "candidates", None):
                text_to_copy = "\n".join(self.candidates)
            else:
                text_to_copy = self.txt_output.get("1.0", tk.END)

            # Use tkinter clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            self.lbl_status_info.config(text="COPIED", fg=GREEN_NEON)
            self._flash_status(1)
            self.root.after(1200, lambda: self.lbl_status_info.config(text="READY", fg=CYAN_NEON))
        except Exception as exc:
            messagebox.showerror("COPY ERROR", f">> Failed to copy: {exc}")

    # ── Pagination controls
    def _prev_page(self):
        if getattr(self, "filtered_candidates", None) is not None:
            total_list = self.filtered_candidates
        else:
            total_list = self.candidates
        if not total_list:
            return
        total_pages = max(1, math.ceil(len(total_list) / self.page_size))
        if self.current_page > 1:
            self.current_page -= 1
            self._render_candidates(total_list, self.page_size)

    def _next_page(self):
        if getattr(self, "filtered_candidates", None) is not None:
            total_list = self.filtered_candidates
        else:
            total_list = self.candidates
        if not total_list:
            return
        total_pages = max(1, math.ceil(len(total_list) / self.page_size))
        if self.current_page < total_pages:
            self.current_page += 1
            self._render_candidates(total_list, self.page_size)

    def _change_page_size(self):
        try:
            new_size = max(1, int(self.page_size_var.get()))
        except Exception:
            new_size = self.page_size
            self.page_size_var.set(str(self.page_size))
        self.page_size = new_size
        self.current_page = 1
        total_list = self.filtered_candidates if self.filtered_candidates is not None else self.candidates
        self._render_candidates(total_list, self.page_size)

    def _generation_error(self, error: str):
        self.progress_bar.reset()
        self.lbl_status.config(text=f">> ERROR: {error}", fg=MAGENTA_NEON)
        self.lbl_status_info.config(text="ERROR", fg=MAGENTA_NEON)
        self._generating = False
        self.btn_generate.config(state="normal")

    def _flash_status(self, times: int = 3):
        def _flash(count):
            if count <= 0:
                return
            if count % 2 == 0:
                self.lbl_status.config(fg=GREEN_NEON)
            else:
                self.lbl_status.config(fg=YELLOW_NEON)
            self.root.after(150, _flash, count - 1)

        _flash(times * 2)

    # ── Export ──────────────────────────────────────────────────────
    def _export(self):
        try:
            if not self.candidates:
                messagebox.showinfo("EXPORT", ">> No candidates to export. Generate a wordlist first!")
                return

            # Ask format
            fmt = simpledialog.askstring("Export Format", "Choose format: txt, csv, json", initialvalue="txt")
            if not fmt:
                return
            fmt = fmt.strip().lower()

            # Default filename
            default_name = f"wordlist.{fmt if fmt in ('txt','csv','json') else 'txt'}"
            file_path = filedialog.asksaveasfilename(defaultextension=f".{fmt}", initialfile=default_name, filetypes=[("All Files", "*.*")])
            if not file_path:
                return

            # Ensure output folder exists
            out_dir = Path(file_path).parent
            out_dir.mkdir(parents=True, exist_ok=True)

            if fmt == "txt":
                export_wordlist(self.candidates, file_path)
            elif fmt == "csv":
                import csv

                with open(file_path, "w", newline="", encoding="utf-8") as fh:
                    writer = csv.writer(fh)
                    for w in self.candidates:
                        writer.writerow([w])
            elif fmt == "json":
                with open(file_path, "w", encoding="utf-8") as fh:
                    json.dump(self.candidates, fh, indent=2)
            else:
                # fallback to txt
                export_wordlist(self.candidates, file_path)

            # Update history
            self._append_history(file_path)

            # Status updates
            size = Path(file_path).stat().st_size
            self.lbl_status.config(text=f">> EXPORTED {len(self.candidates)} candidates to {file_path} ({size} bytes)", fg=CYAN_NEON)
            self._flash_status(2)
            self.lbl_status_info.config(text="SAVED", fg=GREEN_NEON)
            logger.info("Exported %d candidates to %s", len(self.candidates), file_path)

            # Auto copy
            if self.settings.get("autocopy"):
                self.root.clipboard_clear()
                self.root.clipboard_append("\n".join(self.candidates))
                self.lbl_status_info.config(text="COPIED", fg=GREEN_NEON)

            # Auto save to output folder if enabled
            if self.settings.get("autosave"):
                out_folder = Path(self.settings.get("output_folder"))
                out_folder.mkdir(parents=True, exist_ok=True)
                target = out_folder / Path(file_path).name
                Path(file_path).replace(target)
                logger.info("Auto-saved to %s", target)

            # Reset status ready after delay
            self.root.after(2000, lambda: self.lbl_status_info.config(text="READY", fg=CYAN_NEON))
        except Exception as exc:
            logger.exception("Export failed")
            messagebox.showerror("EXPORT ERROR", f">> Failed to export: {exc}")

    # ── Clear output ────────────────────────────────────────────────
    def _clear_output(self):
        self.txt_output.config(state="normal")
        self.txt_output.delete("1.0", tk.END)
        self.txt_output.config(state="disabled")
        self.candidates = []
        self.progress_bar.reset()
        self.lbl_status.config(text=">> OUTPUT CLEARED :: SYSTEM READY", fg=GREEN_NEON)
        self.lbl_status_info.config(text="WAITING...", fg=GRAY_TEXT)
        # clear stats and filtered view
        self.filtered_candidates = None
        self.current_page = 1
        self.lbl_word_count.config(text="Words: 0")
        self.lbl_entropy.config(text="Entropy: 0.0 bits")
        self.lbl_strength.config(text="Strength: N/A")
        self.lbl_gen_time.config(text="Generation time: 0.00s")

    # ── Clean shutdown ──────────────────────────────────────────────
    def _on_close(self):
        self.matrix_rain.stop()
        self.root.destroy()

    # ── Run ─────────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()


def launch_gui():
    """Launch the H4CK3R Wordlist Generator GUI."""
    app = HackerGUI()
    app.run()


if __name__ == "__main__":
    launch_gui()
