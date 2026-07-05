from private_ext.decisions.decision_engine import DecisionEngine
from private_ext.decisions.models import InvestmentDecision
from private_ext.decisions.risk_gate import RiskGate
from private_ext.fact_pack.models import StockFactPack
from private_ext.research.models import ResearchOutput
from private_ext.scoring.models import StockScorecard
from private_ext.scoring.total import ScoreEngine


def _fact_pack(quality_level: str, coverage: float, can_make_decision: bool) -> StockFactPack:
    return StockFactPack(
        symbol="600519",
        trade_date="2026-07-03",
        identity={"name": "贵州茅台"},
        price_facts={"close": 1500.0},
        valuation_facts={"pe": 24.0, "pb": 8.0},
        growth_facts={"revenue_growth": 12.0, "profit_growth": 14.0},
        profitability_facts={"roe": 27.0, "net_margin": 50.0},
        balance_sheet_facts={"debt_ratio": 18.0},
        cashflow_facts={"operating_cashflow_quality": "strong"},
        capital_flow_facts={"main_net_inflow": 1.0, "northbound_net_inflow": 1.0},
        technical_facts={"trend": "up", "volatility": 18.0},
        announcement_facts=[],
        news_facts=[],
        risk_facts=[],
        metadata={
            "quality_level": quality_level,
            "field_coverage_ratio": coverage,
            "can_score": quality_level != "failed",
            "can_make_decision": can_make_decision,
            "provider": "akshare",
        },
    )


def _research_output() -> ResearchOutput:
    return ResearchOutput(
        symbol="600519",
        trade_date="2026-07-03",
        adapter="mock",
        raw_output="mock",
        summary="mock summary",
    )


def test_degraded_quality_caps_total_score():
    fact_pack = _fact_pack("degraded", 0.65, True)

    scorecard = ScoreEngine().score(fact_pack)

    assert scorecard.total_score <= 75
    assert any("data_quality" in reason for reason in scorecard.penalty_reasons)


def test_poor_quality_disallows_buy_after_decision_and_risk_gate():
    fact_pack = _fact_pack("poor", 0.35, False)
    scorecard = StockScorecard(
        symbol="600519",
        trade_date="2026-07-03",
        valuation_score=85,
        growth_score=85,
        profitability_score=85,
        financial_health_score=85,
        capital_flow_score=85,
        technical_score=85,
        sentiment_score=70,
        risk_score=60,
        total_score=82,
        rating_band="strong",
        score_explanations={key: "ok" for key in (
            "valuation",
            "growth",
            "profitability",
            "financial_health",
            "capital_flow",
            "technical",
            "sentiment",
            "risk",
        )},
        penalty_reasons=["data_quality:poor"],
    )

    decision = DecisionEngine().build(scorecard, _research_output(), fact_pack=fact_pack)
    gated = RiskGate().apply(decision, scorecard, fact_pack)

    assert decision.action in {"watch", "hold"}
    assert gated.action in {"watch", "hold"}
    assert "真实数据质量不足" in (gated.risk_gate_reason or "")
