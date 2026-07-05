from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.common import clamp_score, explain_with_missing, to_float


def score_capital_flow(fact_pack: StockFactPack) -> tuple[float, str]:
    main = to_float(fact_pack.capital_flow_facts.get("main_net_inflow"))
    northbound = to_float(fact_pack.capital_flow_facts.get("northbound_net_inflow"))
    missing = [name for name, value in [("main_net_inflow", main), ("northbound_net_inflow", northbound)] if value is None]
    if missing:
        return 50.0, explain_with_missing("capital_flow baseline fallback", missing)
    score = 55 + main * 8 + northbound * 6
    return clamp_score(score), explain_with_missing(
        f"main_net_inflow={main}, northbound_net_inflow={northbound}", missing
    )
