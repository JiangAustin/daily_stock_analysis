from __future__ import annotations

from typing import Any


def clamp_score(value: float) -> float:
    return max(0, min(100, round(value, 2)))


def to_float(value: Any) -> float | None:
    if value in (None, "", [], {}):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def explain_with_missing(base: str, missing: list[str]) -> str:
    if not missing:
        return base
    return f"{base}; conservative_due_to_missing={','.join(missing)}"
