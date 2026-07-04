from private_ext.fact_pack.models import StockFactPack


def score_growth(fact_pack: StockFactPack) -> tuple[float, str]:
    revenue = float(fact_pack.growth_facts.get("revenue_growth") or 0)
    profit = float(fact_pack.growth_facts.get("profit_growth") or 0)
    score = 50 + revenue * 0.8 + profit * 0.8
    return _clamp(score), f"revenue_growth={revenue}%, profit_growth={profit}%"


def _clamp(value: float) -> float:
    return max(0, min(100, round(value, 2)))

