from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.common import clamp_score, explain_with_missing, to_float


def score_technical(fact_pack: StockFactPack) -> tuple[float, str]:
    trend = fact_pack.technical_facts.get("trend")
    volatility = to_float(fact_pack.technical_facts.get("volatility"))
    missing = []
    if not trend:
        missing.append("trend")
    if volatility is None:
        missing.append("volatility")
    if missing:
        return 50.0, explain_with_missing("technical baseline fallback", missing)
    score = 60
    if trend == "up":
        score += 18
    elif trend == "down":
        score -= 18
    if volatility > 30:
        score -= 8
    elif volatility < 15:
        score += 6
    return clamp_score(score), explain_with_missing(f"trend={trend}, volatility={volatility}%", missing)
