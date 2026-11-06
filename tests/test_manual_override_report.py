from __future__ import annotations

from pathlib import Path

from private_ext.decisions.models import InvestmentDecision
from private_ext.fact_pack.models import StockFactPack
from private_ext.paper_trading.models import PaperTradeExecution
from private_ext.reports.stock_report import render_stock_report
from private_ext.scoring.models import StockScorecard


def test_report_renders_manual_override_table(tmp_path: Path):
    fact_pack = StockFactPack(
        symbol="600519",
        trade_date="2026-07-03",
        identity={"name": "贵州茅台", "industry": "白酒"},
        price_facts={"close": 1500.0},
        valuation_facts={"pe": 18.0, "pb": 9.5},
        growth_facts={},
        profitability_facts={},
        balance_sheet_facts={},
        cashflow_facts={},
        capital_flow_facts={},
        technical_facts={},
        announcement_facts=[],
        news_facts=[],
        risk_facts=[],
        metadata={
            "quality_level": "good",
            "actual_data_date": "2026-07-03",
            "manual_override": {
                "applied_fields": ["valuation_raw.pe"],
                "applied_records": [
                    {
                        "field": "valuation_raw.pe",
                        "value": 18.0,
                        "source_note": "manual pe",
                        "source_url": "https://example.invalid/manual",
                        "updated_at": "2026-07-05",
                        "confidence": "medium",
                        "allow_override": True,
                        "action": "replaced_live",
                    }
                ],
            },
            "field_provenance": {
                "valuation_raw.pe": {
                    "source": "manual_override",
                    "candidate": "manual_csv",
                    "fallback_level": 0,
                    "is_cached": False,
                    "confidence": "medium",
                    "source_note": "manual pe",
                    "source_url": "https://example.invalid/manual",
                    "updated_at": "2026-07-05",
                    "allow_override": True,
                }
            },
        },
    )
    scorecard = StockScorecard(
        symbol="600519",
        trade_date="2026-07-03",
        valuation_score=70,
        growth_score=60,
        profitability_score=90,
        financial_health_score=80,
        capital_flow_score=70,
        technical_score=70,
        sentiment_score=65,
        risk_score=85,
        total_score=75,
        rating_band="positive",
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
    decision = InvestmentDecision(
        symbol="600519",
        trade_date="2026-07-03",
        rating="neutral-bullish",
        action="watch",
        confidence=0.68,
        target_position=0.02,
        horizon="20d",
        thesis="watch for confirmation",
        bullish_points=["profitability"],
        bearish_points=["valuation"],
        catalysts=["demand recovery"],
        risks=["valuation compression"],
        invalidation_conditions=["growth slows"],
        aggressive_plan="small position",
        balanced_plan="watch",
        conservative_plan="wait",
    )
    execution = PaperTradeExecution(
        action="watch",
        price=1500.0,
        quantity=0,
        amount=0,
        fee=0,
        executed=False,
        reason="watch only",
    )

    report = render_stock_report(fact_pack, scorecard, decision, execution, tmp_path).read_text(encoding="utf-8")

    assert "### 手动覆盖字段" in report
    assert "valuation_raw.pe" in report
    assert "manual pe" in report
    assert "manual_csv" not in report or "manual_override" in report
