from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.common import clamp_score, explain_with_missing, to_float


def score_profitability(fact_pack: StockFactPack) -> tuple[float, str]:
    roe = to_float(fact_pack.profitability_facts.get("roe"))
    net_margin = to_float(fact_pack.profitability_facts.get("net_margin"))
    missing = [name for name, value in [("roe", roe), ("net_margin", net_margin)] if value is None]
    if missing:
        return 52.0, explain_with_missing("profitability baseline fallback", missing)
    score = 45 + roe * 1.2 + net_margin * 0.35
    return clamp_score(score), explain_with_missing(f"ROE={roe}%, net_margin={net_margin}%", missing)
