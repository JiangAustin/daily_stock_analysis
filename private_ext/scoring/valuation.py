from private_ext.fact_pack.models import StockFactPack


def score_valuation(fact_pack: StockFactPack) -> tuple[float, str]:
    pe = float(fact_pack.valuation_facts.get("pe") or 0)
    pb = float(fact_pack.valuation_facts.get("pb") or 0)
    dividend = float(fact_pack.valuation_facts.get("dividend_yield") or 0)
    score = 70
    if pe <= 8:
        score += 14
    elif pe >= 35:
        score -= 18
    if pb <= 1:
        score += 8
    elif pb >= 6:
        score -= 10
    if dividend >= 3:
        score += 8
    return _clamp(score), f"PE={pe}, PB={pb}, dividend={dividend}%"


def _clamp(value: float) -> float:
    return max(0, min(100, round(value, 2)))

