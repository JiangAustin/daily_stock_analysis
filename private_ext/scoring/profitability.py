from private_ext.fact_pack.models import StockFactPack


def score_profitability(fact_pack: StockFactPack) -> tuple[float, str]:
    roe = float(fact_pack.profitability_facts.get("roe") or 0)
    net_margin = float(fact_pack.profitability_facts.get("net_margin") or 0)
    score = 45 + roe * 1.2 + net_margin * 0.35
    return _clamp(score), f"ROE={roe}%, net_margin={net_margin}%"


def _clamp(value: float) -> float:
    return max(0, min(100, round(value, 2)))

