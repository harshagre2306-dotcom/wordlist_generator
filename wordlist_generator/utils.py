"""Utility helpers for the wordlist GUI and generator.

Small, well-tested helpers kept separate to keep UI code focused.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, List


def parse_csv(value: str) -> List[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def safe_int(value: str, default: int) -> int:
    try:
        return int(value.strip()) if str(value).strip() else default
    except Exception:
        return default


def estimate_entropy(candidates: Iterable[str]) -> float:
    """Rough entropy estimate: avg_length * log2(unique_alphabet_size)."""
    items = list(candidates)
    if not items:
        return 0.0
    avg_len = sum(len(c) for c in items) / len(items)
    alphabet = set("".join(items))
    if not alphabet:
        return 0.0
    try:
        return avg_len * math.log2(len(alphabet))
    except Exception:
        return 0.0


def strength_label(entropy_bits: float) -> str:
    if entropy_bits < 28:
        return "Very Weak"
    if entropy_bits < 36:
        return "Weak"
    if entropy_bits < 60:
        return "Moderate"
    if entropy_bits < 80:
        return "Strong"
    return "Very Strong"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = [
    "parse_csv",
    "safe_int",
    "estimate_entropy",
    "strength_label",
    "ensure_dir",
]
