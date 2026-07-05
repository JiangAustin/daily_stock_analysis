from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.common import clamp_score


MAJOR_RISK_KEYWORDS = ("重大减持", "解禁", "问询函", "业绩雷")


def score_risk(fact_pack: StockFactPack) -> tuple[float, str, list[str]]:
    risks = [str(item.get("risk", "")) for item in fact_pack.risk_facts]
    score = 88 - len(risks) * 8
    penalties = [f"missing:{field}" for field in fact_pack.missing_fields]
    if fact_pack.data_quality_warnings:
        penalties.extend(f"warning:{item}" for item in fact_pack.data_quality_warnings)
    for risk in risks:
        if any(keyword in risk for keyword in MAJOR_RISK_KEYWORDS):
            score -= 25
            penalties.append(risk)
        elif risk:
            penalties.append(risk)
    explain = f"risk_events={len(risks)}"
    if fact_pack.missing_fields:
        explain += "; conservative_due_to_missing=risk_context"
        score -= min(18, len(fact_pack.missing_fields) * 1.5)
    return clamp_score(score), explain, penalties
