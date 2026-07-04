from private_ext.decisions.decision_engine import DecisionEngine
from private_ext.research.models import ResearchOutput
from private_ext.scoring.models import StockScorecard


def _scorecard(total_score: float) -> StockScorecard:
    return StockScorecard(
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
        total_score=total_score,
        rating_band="strong",
        score_explanations={
            "valuation": "ok",
            "growth": "ok",
            "profitability": "ok",
            "financial_health": "ok",
            "capital_flow": "ok",
            "technical": "ok",
            "sentiment": "ok",
            "risk": "ok",
        },
    )


def test_decision_engine_maps_high_score_to_buy_decision():
    research_output = ResearchOutput(
        symbol="600519",
        trade_date="2026-07-03",
        adapter="mock",
        raw_output="mock",
        summary="high quality opportunity",
    )

    decision = DecisionEngine().build(_scorecard(82), research_output)

    assert decision.action == "buy"
    assert decision.target_position == 0.05
    assert decision.confidence >= 0.70
    assert decision.thesis

