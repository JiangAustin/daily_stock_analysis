from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.common import clamp_score, explain_with_missing, to_float


def score_financial_health(fact_pack: StockFactPack) -> tuple[float, str]:
    debt_ratio = to_float(fact_pack.balance_sheet_facts.get("debt_ratio"))
    cashflow_quality = fact_pack.cashflow_facts.get("operating_cashflow_quality")
    missing = []
    if debt_ratio is None:
        missing.append("debt_ratio")
    if not cashflow_quality:
        missing.append("operating_cashflow_quality")
    if missing:
        return 55.0, explain_with_missing("financial_health baseline fallback", missing)
    score = 80 - max(0, debt_ratio - 35) * 0.6
    if cashflow_quality == "strong":
        score += 10
    elif cashflow_quality == "improving":
        score += 5
    return clamp_score(score), explain_with_missing(f"debt_ratio={debt_ratio}%, cashflow={cashflow_quality}", missing)
