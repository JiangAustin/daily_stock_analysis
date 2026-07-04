from typing import Any


def missing_keys(payload: dict[str, Any], keys: list[str], prefix: str) -> list[str]:
    return [f"{prefix}.{key}" for key in keys if payload.get(key) in (None, "", [])]

