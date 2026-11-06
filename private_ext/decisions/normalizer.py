def normalize_action(action: str) -> str:
    action = action.lower().strip()
    return action if action in {"buy", "watch", "hold", "reduce"} else "hold"

