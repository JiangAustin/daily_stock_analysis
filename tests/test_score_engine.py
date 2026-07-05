from private_ext.fact_pack.builder import FactPackBuilder
from private_ext.raw_data.mock_collector import MockRawDataCollector
from private_ext.scoring.total import ScoreEngine


def test_score_engine_generates_explained_scores_between_zero_and_one_hundred():
    raw = MockRawDataCollector().collect("300750", "2026-07-03")
    fact_pack = FactPackBuilder().build(raw)

    scorecard = ScoreEngine().score(fact_pack)

    assert scorecard.symbol == "300750"
    assert 0 <= scorecard.total_score <= 100
    assert scorecard.rating_band in {"strong", "positive", "neutral", "weak"}
    assert set(scorecard.score_explanations) == {
        "valuation",
        "growth",
        "profitability",
        "financial_health",
        "capital_flow",
        "technical",
        "sentiment",
        "risk",
    }

