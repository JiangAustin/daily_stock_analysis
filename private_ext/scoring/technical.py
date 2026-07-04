from private_ext.fact_pack.models import StockFactPack


def score_technical(fact_pack: StockFactPack) -> tuple[float, str]:
    trend = fact_pack.technical_facts.get("trend")
    volatility = float(fact_pack.technical_facts.get("volatility") or 0)
    score = 60
    if trend == "up":
        score += 18
    elif trend == "down":
        score -= 18
    if volatility > 30:
        score -= 8
    elif volatility < 15:
        score += 6
    return _clamp(score), f"trend={trend}, volatility={volatility}%"


def _clamp(value: float) -> float:
    return max(0, min(100, round(value, 2)))

