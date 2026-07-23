"""Session history manager for the H4CK3R Wordlist Generator.

Tracks export and generation events in a JSON history file with audit timestamps.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .logger import get_logger
from .utils import ensure_dir

logger = get_logger(name="history", log_file="history.log")


class SessionHistory:
    def __init__(self, history_path: Path, max_entries: int = 20):
        self.history_path = history_path
        self.max_entries = max_entries
        ensure_dir(self.history_path.parent)
        self.entries = self._load_history()

    def _load_history(self) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []
        try:
            items = json.loads(self.history_path.read_text(encoding="utf-8"))
            if isinstance(items, list):
                return items
        except Exception:
            logger.exception("Failed to read session history file")
        return []

    def _save_history(self) -> None:
        try:
            self.history_path.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")
        except Exception:
            logger.exception("Failed to write session history file")

    def append(
        self,
        action: str,
        target: str,
        candidates: int = 0,
        user: str | None = None,
        *,
        generation_time: float | None = None,
        total_passwords: int | None = None,
        export_type: str | None = None,
        output_file: str | None = None,
    ) -> None:
        timestamp = time.time()
        entry = {
            "time": timestamp,
            "date": time.strftime("%Y-%m-%d", time.localtime(timestamp)),
            "time_of_day": time.strftime("%H:%M:%S", time.localtime(timestamp)),
            "action": action,
            "target": target,
            "candidates": candidates,
            "user": user or "admin",
            "generation_time": generation_time,
            "total_passwords": total_passwords if total_passwords is not None else candidates,
            "export_type": export_type,
            "output_file": output_file,
        }
        self.entries.insert(0, entry)
        self.entries = self.entries[: self.max_entries]
        self._save_history()
        logger.info("Recorded session history: %s", entry)

    def list(self) -> list[dict[str, Any]]:
        return list(self.entries)

    def clear(self) -> None:
        self.entries = []
        self._save_history()
        logger.info("Cleared session history")

    @staticmethod
    def format_entry(entry: dict[str, Any]) -> str:
        when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.get("time", 0)))
        action = entry.get("action", "unknown").upper()
        target = entry.get("target", "-")
        count = entry.get("candidates", 0)
        user = entry.get("user", "admin")
        return f"[{when}] {action} | {user} | {count} items | {target}"

    @staticmethod
    def format_fields(entry: dict[str, Any]) -> list[str]:
        return [
            f"Date: {entry.get('date', '-')}",
            f"Time: {entry.get('time_of_day', '-')}",
            f"Total Passwords: {entry.get('total_passwords', entry.get('candidates', 0))}",
            f"Generation Time: {entry.get('generation_time', '-')}",
            f"Export Type: {entry.get('export_type', '-')}",
            f"Output File: {entry.get('output_file', '-')}",
        ]
