from private_ext.decisions.models import InvestmentDecision
from private_ext.decisions.risk_gate import RiskGate
from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.models import StockScorecard


def test_risk_gate_downgrades_low_confidence_buy_to_watch():
    decision = InvestmentDecision(
        symbol="600519",
        trade_date="2026-07-03",
        rating="bullish",
        action="buy",
        confidence=0.60,
        target_position=0.05,
        horizon="20d",
        thesis="candidate",
        bullish_points=["profitability"],
        bearish_points=[],
        catalysts=[],
        risks=[],
        invalidation_conditions=["score below 60"],
        aggressive_plan="buy",
        balanced_plan="watch",
        conservative_plan="wait",
    )
    scorecard = StockScorecard(
        symbol="600519",
        trade_date="2026-07-03",
        valuation_score=80,
        growth_score=80,
        profitability_score=80,
        financial_health_score=80,
        capital_flow_score=80,
        technical_score=80,
        sentiment_score=80,
        risk_score=80,
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
    )
    fact_pack = StockFactPack(
        symbol="600519",
        trade_date="2026-07-03",
        identity={"name": "贵州茅台"},
        price_facts={},
        valuation_facts={},
        growth_facts={},
        profitability_facts={},
        balance_sheet_facts={},
        cashflow_facts={},
        capital_flow_facts={},
        technical_facts={},
        announcement_facts=[],
        news_facts=[],
        risk_facts=[],
    )

    gated = RiskGate().apply(decision, scorecard, fact_pack)

    assert gated.action == "watch"
    assert gated.target_position == 0
    assert gated.risk_gate_passed is False
    assert "confidence" in (gated.risk_gate_reason or "")

