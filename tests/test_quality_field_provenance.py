import pytest
from pathlib import Path

from private_ext.decisions.models import InvestmentDecision
from private_ext.fact_pack.models import StockFactPack
from private_ext.paper_trading.models import PaperTradeExecution
from private_ext.raw_data.quality import build_quality_report
from private_ext.reports.stock_report import render_stock_report
from private_ext.scoring.models import StockScorecard

pytestmark = pytest.mark.private_ext


def test_quality_report_keeps_provenance_and_cache_counters():
    report = build_quality_report(
        symbol="600519",
        requested_date="2026-07-03",
        provider="akshare",
        actual_data_date="2026-07-03",
        field_values={
            "market_snapshot.close": 1500.0,
            "market_snapshot.pct_change": 1.2,
            "valuation_raw.pe": None,
            "valuation_raw.pb": 8.5,
            "financial_raw.roe": 27.0,
            "financial_raw.net_profit_growth": 14.0,
            "kline_summary.return_20d": 5.6,
        },
        warnings=["used_source_cache:stock_zh_a_hist"],
        failed_sources=["stock_zh_a_spot_em"],
        successful_sources=["stock_zh_a_hist", "stock_financial_analysis_indicator"],
        field_provenance={
            "market_snapshot.close": {
                "source": "stock_zh_a_hist",
                "fallback_level": 1,
                "is_cached": True,
                "confidence": "medium",
            }
        },
        source_cache_used=["stock_zh_a_hist"],
        live_success_count=2,
        cache_success_count=1,
        live_failure_count=1,
    )

    assert report.field_provenance_summary["market_snapshot.close"]["source"] == "stock_zh_a_hist"
    assert report.source_cache_used == ["stock_zh_a_hist"]
    assert report.live_success_count == 2
    assert report.cache_success_count == 1
    assert report.live_failure_count == 1


def test_report_renderer_includes_key_field_provenance_table(tmp_path: Path):
    fact_pack = StockFactPack(
        symbol="600519",
        trade_date="2026-07-03",
        identity={"name": "贵州茅台", "industry": "白酒"},
        price_facts={"close": 1500.0},
        valuation_facts={"pe": 24.0, "pb": 8.0},
        growth_facts={"net_profit_growth": 14.0},
        profitability_facts={"roe": 27.0},
        balance_sheet_facts={},
        cashflow_facts={},
        capital_flow_facts={},
        technical_facts={"return_20d": 5.8},
        announcement_facts=[],
        news_facts=[],
        risk_facts=[],
        metadata={
            "provider": "akshare",
            "requested_date": "2026-07-03",
            "actual_data_date": "2026-07-03",
            "quality_level": "degraded",
            "field_coverage_ratio": 0.72,
            "can_score": True,
            "can_make_decision": True,
            "failed_sources": ["stock_zh_a_spot_em"],
            "successful_sources": ["stock_zh_a_hist", "stock_financial_analysis_indicator"],
            "field_provenance": {
                "market_snapshot.close": {
                    "source": "stock_zh_a_hist",
                    "fallback_level": 1,
                    "is_cached": True,
                    "confidence": "medium",
                },
                "valuation_raw.pe": {
                    "source": "stock_individual_info_em",
                    "fallback_level": 1,
                    "is_cached": False,
                    "confidence": "medium",
                },
            },
            "source_cache_used": ["stock_zh_a_hist"],
            "live_success_count": 2,
            "cache_success_count": 1,
            "live_failure_count": 1,
        },
    )
    scorecard = StockScorecard(
        symbol="600519",
        trade_date="2026-07-03",
        valuation_score=70,
        growth_score=65,
        profitability_score=85,
        financial_health_score=75,
        capital_flow_score=60,
        technical_score=72,
        sentiment_score=55,
        risk_score=70,
        total_score=68,
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
        confidence=0.62,
        target_position=0.01,
        horizon="20d",
        thesis="watch fallback-backed signal",
        bullish_points=["盈利能力稳定"],
        bearish_points=["部分字段来自回退源"],
        catalysts=["半年报"],
        risks=["数据源波动"],
        invalidation_conditions=["趋势转弱"],
        aggressive_plan="watch",
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
    content = path.read_text(encoding="utf-8")

    assert "### 关键字段来源" in content
    assert "| market_snapshot.close | 是 | stock_zh_a_hist |" in content
    assert "### 数据源成功/失败统计" in content
    assert "source cache" in content.lower() or "缓存" in content
