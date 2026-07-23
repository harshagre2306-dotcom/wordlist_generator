from __future__ import annotations

from pathlib import Path
from typing import Iterable, List
import itertools
import re


def _normalize(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value


def _build_variants(
    base: str,
    dob: str,
    suffixes: Iterable[str] | None = None,
    separators: Iterable[str] | None = None,
) -> List[str]:
    if not base:
        return []

    dob_digits = re.sub(r"\D+", "", dob)
    year = dob_digits[-2:] if len(dob_digits) >= 2 else dob_digits
    short_year = year[-2:] if len(year) >= 2 else year

    suffix_values = [item for item in (suffixes or ["123", "12"]) if item]
    separator_values = [item for item in (separators or ["@", "!", "-", "_"]) if item]

    ordered: List[str] = []
    seen = set()

    def add(candidate: str) -> None:
        if candidate and candidate not in seen:
            ordered.append(candidate)
            seen.add(candidate)

    add(base)
    add(f"{base}{dob_digits}")
    add(f"{base}{short_year}")
    add(f"{base}@{short_year}")
    add(f"{base}{short_year}!")
    add(f"{base}{dob_digits}!")

    for suffix in suffix_values:
        add(f"{base}{suffix}")

    for separator in separator_values:
        for suffix in suffix_values:
            add(f"{base}{separator}{suffix}")

    for separator in separator_values:
        add(f"{base}{separator}{short_year}")
        add(f"{base}{separator}{dob_digits}")

    if len(base) > 1:
        add(f"{base[0]}{base[-1]}{dob_digits}")

    return ordered


def _extend_to_count(
    ordered: List[str],
    count: int,
    suffix_values: List[str],
    separator_values: List[str],
) -> List[str]:
    """Extend the deterministic pool until the requested count is reached."""
    if len(ordered) >= count:
        return ordered[:count]

    seen = set(ordered)
    produced = ordered[:]
    seed_pool = ordered[:]

    for index in range(1, count + 1):
        for candidate in seed_pool:
            if len(produced) >= count:
                return produced[:count]

            numeric_variant = f"{candidate}{index}"
            if numeric_variant not in seen:
                seen.add(numeric_variant)
                produced.append(numeric_variant)

            for separator in separator_values:
                for suffix in suffix_values:
                    if len(produced) >= count:
                        return produced[:count]

                    variant = f"{candidate}{separator}{suffix}{index}"
                    if variant not in seen:
                        seen.add(variant)
                        produced.append(variant)

    return produced[:count]


def generate_wordlist(
    name: str,
    dob: str,
    interests: Iterable[str] | None = None,
    suffixes: Iterable[str] | None = None,
    separators: Iterable[str] | None = None,
    count: int | None = None,
) -> List[str]:
    """Generate a deterministic, de-duplicated password candidate list.

    When ``count`` is provided, the function returns exactly that many values by
    extending the base, deterministic candidate pool with numeric suffix variants
    if the initial pattern generation is smaller than the request.
    """
    normalized_name = _normalize(name)
    normalized_dob = _normalize(dob)
    interest_items = [_normalize(item) for item in (interests or []) if _normalize(item)]
    suffix_values = [item for item in (suffixes or ["123", "12"]) if item]
    separator_values = [item for item in (separators or ["@", "!", "-", "_"]) if item]

    candidates: List[str] = []

    if normalized_name:
        candidates.extend(_build_variants(normalized_name, normalized_dob, suffixes=suffix_values, separators=separator_values))

    for interest in interest_items:
        candidates.extend(_build_variants(interest, normalized_dob, suffixes=suffix_values, separators=separator_values))

    combined = []
    for first, second in itertools.product([normalized_name] if normalized_name else [""], interest_items + [""]):
        if not first and not second:
            continue
        if first and second:
            combined.append(f"{first}{second}")
            combined.append(f"{first}{second}{normalized_dob}")
            combined.append(f"{first}@{second}")

    candidates.extend(combined)

    # Keep a stable, de-duplicated list.
    ordered: List[str] = []
    seen = set()
    for item in candidates:
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)

    if count is not None:
        count = int(count)
        if count < 1:
            raise ValueError("count must be a positive integer")
        if len(ordered) < count:
            ordered = _extend_to_count(ordered, count, suffix_values, separator_values)
        else:
            ordered = ordered[:count]

    return ordered


def export_wordlist(candidates: Iterable[str], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [candidate for candidate in candidates if candidate]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path
