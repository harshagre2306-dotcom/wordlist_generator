"""Logging setup for the H4CK3R Wordlist Generator.

Provides a configured module-level logger that other modules import.
"""
from __future__ import annotations

import logging
from pathlib import Path


LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "app.log"


def get_logger(name: str = "h4cksmith", log_file: str | None = None) -> logging.Logger:
    """Return a configured logger writing to disk and stderr.

    If `log_file` is supplied, the logger writes to that file under the
    repository logs folder. Otherwise it defaults to logs/app.log.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    destination = LOG_FILE if log_file is None else LOGS_DIR / log_file

    fh = logging.FileHandler(destination, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


__all__ = ["get_logger"]
