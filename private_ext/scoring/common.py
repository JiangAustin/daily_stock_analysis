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


def append_provenance(
    base: str,
    *,
    field_provenance: dict[str, dict[str, Any]] | None,
    fields: list[str],
) -> str:
    if not field_provenance:
        return base

    parts: list[str] = []
    for field in fields:
        payload = field_provenance.get(field, {}) or {}
        source = payload.get("source")
        fallback_level = payload.get("fallback_level")
        is_cached = payload.get("is_cached")
        confidence = payload.get("confidence")
        short_field = field.split(".")[-1]
        if source:
            cache_flag = "cache" if is_cached else "live"
            parts.append(f"{short_field}={source}/{cache_flag}/l{fallback_level}/{confidence}")
        else:
            parts.append(f"{short_field}=missing")
    if not parts:
        return base
    return f"{base}; provenance={'|'.join(parts)}"
