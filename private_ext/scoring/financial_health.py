from private_ext.fact_pack.models import StockFactPack


def score_financial_health(fact_pack: StockFactPack) -> tuple[float, str]:
    debt_ratio = float(fact_pack.balance_sheet_facts.get("debt_ratio") or 0)
    cashflow_quality = fact_pack.cashflow_facts.get("operating_cashflow_quality")
    score = 80 - max(0, debt_ratio - 35) * 0.6
    if cashflow_quality == "strong":
        score += 10
    elif cashflow_quality == "improving":
        score += 5
    return _clamp(score), f"debt_ratio={debt_ratio}%, cashflow={cashflow_quality}"


def _clamp(value: float) -> float:
    return max(0, min(100, round(value, 2)))

