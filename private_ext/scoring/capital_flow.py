from private_ext.fact_pack.models import StockFactPack


def score_capital_flow(fact_pack: StockFactPack) -> tuple[float, str]:
    main = float(fact_pack.capital_flow_facts.get("main_net_inflow") or 0)
    northbound = float(fact_pack.capital_flow_facts.get("northbound_net_inflow") or 0)
    score = 55 + main * 8 + northbound * 6
    return _clamp(score), f"main_net_inflow={main}, northbound_net_inflow={northbound}"


def _clamp(value: float) -> float:
    return max(0, min(100, round(value, 2)))

