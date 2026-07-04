from pathlib import Path

from private_ext.decisions.models import InvestmentDecision
from private_ext.fact_pack.models import StockFactPack
from private_ext.paper_trading.models import PaperTradeExecution
from private_ext.reports.stock_report import render_stock_report
from private_ext.scoring.models import StockScorecard


def test_private_ext_report_renderer_writes_required_markdown_sections(tmp_path: Path):
    fact_pack = StockFactPack(
        symbol="600519",
        trade_date="2026-07-03",
        identity={"name": "贵州茅台", "industry": "白酒"},
        price_facts={"close": 1500.0},
        valuation_facts={"pe": 28.0},
        growth_facts={"revenue_growth": 8.0},
        profitability_facts={"roe": 28.0},
        balance_sheet_facts={"debt_ratio": 20.0},
        cashflow_facts={"operating_cashflow_quality": "strong"},
        capital_flow_facts={"main_net_inflow": 1.2},
        technical_facts={"trend": "up"},
        announcement_facts=[],
        news_facts=[],
        risk_facts=[],
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

    path = render_stock_report(fact_pack, scorecard, decision, execution, tmp_path)

    report = path.read_text(encoding="utf-8")
    assert path.name == "stock_report_600519_2026-07-03.md"
    assert "# A股AI投研报告" in report
    assert "## 1. 结论摘要" in report
    assert "## 9. 风险提示" in report
    assert "不构成投资建议" in report
