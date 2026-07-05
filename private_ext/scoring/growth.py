from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.common import clamp_score, explain_with_missing, to_float


def score_growth(fact_pack: StockFactPack) -> tuple[float, str]:
    revenue = to_float(fact_pack.growth_facts.get("revenue_growth"))
    profit = to_float(fact_pack.growth_facts.get("profit_growth"))
    missing = [name for name, value in [("revenue_growth", revenue), ("profit_growth", profit)] if value is None]
    if missing:
        return 50.0, explain_with_missing("growth baseline fallback", missing)
    score = 50 + revenue * 0.8 + profit * 0.8
    return clamp_score(score), explain_with_missing(f"revenue_growth={revenue}%, profit_growth={profit}%", missing)
