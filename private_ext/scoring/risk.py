from private_ext.fact_pack.models import StockFactPack


MAJOR_RISK_KEYWORDS = ("重大减持", "解禁", "问询函", "业绩雷")


def score_risk(fact_pack: StockFactPack) -> tuple[float, str, list[str]]:
    risks = [str(item.get("risk", "")) for item in fact_pack.risk_facts]
    score = 88 - len(risks) * 8
    penalties = []
    for risk in risks:
        if any(keyword in risk for keyword in MAJOR_RISK_KEYWORDS):
            score -= 25
            penalties.append(risk)
        elif risk:
            penalties.append(risk)
    return _clamp(score), f"risk_events={len(risks)}", penalties


def _clamp(value: float) -> float:
    return max(0, min(100, round(value, 2)))

