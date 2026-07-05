from collections.abc import Iterable


def bullet_list(items: Iterable[str]) -> str:
    values = [str(item) for item in items if str(item)]
    return "\n".join(f"- {item}" for item in values) if values else "- 无"

