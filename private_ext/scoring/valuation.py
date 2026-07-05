from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.common import clamp_score, explain_with_missing, to_float


def score_valuation(fact_pack: StockFactPack) -> tuple[float, str]:
    pe = to_float(fact_pack.valuation_facts.get("pe"))
    pb = to_float(fact_pack.valuation_facts.get("pb"))
    dividend = to_float(fact_pack.valuation_facts.get("dividend_yield"))
    missing = [
        name for name, value in [("pe", pe), ("pb", pb), ("dividend_yield", dividend)] if value is None
    ]

    if len(missing) >= 2:
        return 55.0, explain_with_missing("valuation baseline fallback", missing)

    score = 70
    if pe is not None and pe <= 8:
        score += 14
    elif pe is not None and pe >= 35:
        score -= 18
    if pb is not None and pb <= 1:
        score += 8
    elif pb is not None and pb >= 6:
        score -= 10
    if dividend is not None and dividend >= 3:
        score += 8
    return clamp_score(score), explain_with_missing(f"PE={pe}, PB={pb}, dividend={dividend}%", missing)
