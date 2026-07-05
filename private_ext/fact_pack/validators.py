from typing import Any


def missing_keys(payload: dict[str, Any], keys: list[str], prefix: str) -> list[str]:
    return [f"{prefix}.{key}" for key in keys if is_missing(payload.get(key))]


def is_missing(value: Any) -> bool:
    return value in (None, "", []) or value == {}
