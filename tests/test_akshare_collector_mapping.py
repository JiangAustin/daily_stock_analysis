from __future__ import annotations

from types import SimpleNamespace

import pytest

from private_ext.fact_pack.builder import FactPackBuilder
from private_ext.raw_data.models import RawStockData
from private_ext.scoring.total import ScoreEngine


pytestmark = pytest.mark.private_ext


class _FakeFrame:
    def __init__(self, rows):
        self.rows = rows

    @property
    def empty(self) -> bool:
        return not self.rows

    def to_dict(self, orient: str = "records"):
        assert orient == "records"
        return list(self.rows)

    def iterrows(self):
        for index, row in enumerate(self.rows):
            yield index, row


def test_factory_creates_mock_and_akshare_collectors():
    from private_ext.raw_data.factory import create_raw_data_collector
    from private_ext.raw_data.akshare_collector import AkShareRawDataCollector
    from private_ext.raw_data.mock_collector import MockRawDataCollector

    assert isinstance(create_raw_data_collector("mock"), MockRawDataCollector)
    assert isinstance(create_raw_data_collector("akshare"), AkShareRawDataCollector)


def test_factory_rejects_unimplemented_a_stock_data_provider():
    from private_ext.raw_data.factory import create_raw_data_collector

    with pytest.raises(NotImplementedError, match="a_stock_data provider is not implemented yet"):
        create_raw_data_collector("a_stock_data")


def test_akshare_collector_maps_fake_payloads_to_raw_stock_data(monkeypatch):
    from private_ext.raw_data.akshare_collector import AkShareRawDataCollector

    fake_ak = SimpleNamespace(
        stock_individual_info_em=lambda symbol: _FakeFrame(
            [
                {"item": "股票简称", "value": "贵州茅台"},
                {"item": "行业", "value": "酿酒行业"},
                {"item": "总市值", "value": "1900000000000"},
                {"item": "流通市值", "value": "1800000000000"},
                {"item": "上市时间", "value": "20010827"},
            ]
        ),
        stock_zh_a_spot_em=lambda: _FakeFrame(
            [
                {
                    "代码": "600519",
                    "名称": "贵州茅台",
                    "最新价": 1500.0,
                    "涨跌幅": 1.25,
                    "成交额": 5200000000.0,
                    "换手率": 0.45,
                    "市盈率-动态": 24.5,
                    "市净率": 8.7,
                }
            ]
        ),
        stock_zh_a_hist=lambda **kwargs: _FakeFrame(
            [
                {"日期": "2026-06-26", "收盘": 1450.0},
                {"日期": "2026-06-27", "收盘": 1460.0},
                {"日期": "2026-06-28", "收盘": 1470.0},
                {"日期": "2026-06-29", "收盘": 1480.0},
                {"日期": "2026-06-30", "收盘": 1490.0},
                {"日期": "2026-07-01", "收盘": 1495.0},
                {"日期": "2026-07-02", "收盘": 1500.0},
                {"日期": "2026-07-03", "收盘": 1502.0},
            ]
        ),
        stock_financial_analysis_indicator=lambda **kwargs: _FakeFrame(
            [
                {
                    "日期": "2026-03-31",
                    "摊薄每股收益(元)": 5.2,
                    "主营业务收入增长率(%)": 12.0,
                    "净利润增长率(%)": 13.5,
                    "净资产收益率(%)": 27.0,
                    "销售毛利率(%)": 91.5,
                    "销售净利率(%)": 52.1,
                    "资产负债率(%)": 18.3,
                }
            ]
        ),
        stock_individual_fund_flow=lambda **kwargs: _FakeFrame(
            [
                {
                    "日期": "2026-07-03",
                    "主力净流入-净额": 230000000.0,
                    "超大单净流入-净额": 120000000.0,
                    "大单净流入-净额": 110000000.0,
                    "中单净流入-净额": -50000000.0,
                    "小单净流入-净额": -180000000.0,
                }
            ]
        ),
        stock_hsgt_individual_em=lambda symbol: _FakeFrame(
            [{"持股日期": "2026-07-03", "持股市值": 1500000000.0, "持股数量": 1000000}]
        ),
        stock_lhb_stock_statistic_em=lambda symbol: _FakeFrame(
            [{"代码": "600519", "最近上榜日": "2026-06-20", "上榜次数": 1}]
        ),
        stock_news_em=lambda symbol: _FakeFrame(
            [{"新闻标题": "白酒需求回暖", "发布时间": "2026-07-03 09:30:00", "文章来源": "测试源"}]
        ),
        stock_research_report_em=lambda symbol: _FakeFrame(
            [{"股票代码": "600519", "评级": "买入", "目标价": 1688.0, "报告日期": "2026-07-01"}]
        ),
    )
    monkeypatch.setattr("private_ext.raw_data.akshare_collector.ak", fake_ak)

    raw = AkShareRawDataCollector().collect("sh600519", "2026-07-03")

    assert isinstance(raw, RawStockData)
    assert raw.symbol == "600519"
    assert raw.basic_info["name"] == "贵州茅台"
    assert raw.market_snapshot["close"] == 1500.0
    assert raw.valuation_raw["pe"] == 24.5
    assert raw.financial_raw["roe"] == 27.0
    assert raw.capital_flow_raw["main_net_inflow"] == 230000000.0
    assert raw.news_raw
    assert raw.metadata["provider"] == "akshare"


def test_akshare_collector_gracefully_degrades_when_partial_payloads_are_missing(monkeypatch):
    from private_ext.raw_data.akshare_collector import AkShareRawDataCollector

    fake_ak = SimpleNamespace(
        stock_individual_info_em=lambda symbol: _FakeFrame(
            [{"item": "股票简称", "value": "平安银行"}]
        ),
        stock_zh_a_spot_em=lambda: _FakeFrame(
            [{"代码": "000001", "名称": "平安银行", "最新价": 10.2}]
        ),
        stock_zh_a_hist=lambda **kwargs: _FakeFrame(
            [{"日期": "2026-07-03", "收盘": 10.2}]
        ),
        stock_financial_analysis_indicator=lambda **kwargs: _FakeFrame([]),
        stock_individual_fund_flow=lambda **kwargs: _FakeFrame([]),
        stock_hsgt_individual_em=lambda symbol: _FakeFrame([]),
        stock_lhb_stock_statistic_em=lambda symbol: _FakeFrame([]),
        stock_news_em=lambda symbol: _FakeFrame([]),
        stock_research_report_em=lambda symbol: _FakeFrame([]),
    )
    monkeypatch.setattr("private_ext.raw_data.akshare_collector.ak", fake_ak)

    raw = AkShareRawDataCollector().collect("000001.SZ", "2026-07-03")
    fact_pack = FactPackBuilder().build(raw)
    scorecard = ScoreEngine().score(fact_pack)

    assert raw.symbol == "000001"
    assert fact_pack.missing_fields
    assert fact_pack.data_quality_warnings
    assert 0 <= scorecard.total_score <= 100
    assert any("missing" in reason for reason in scorecard.penalty_reasons)


def test_akshare_collector_can_fallback_to_cache_when_live_fetch_is_too_poor(monkeypatch, tmp_path):
    from private_ext.raw_data.akshare_collector import AkShareRawDataCollector
    from private_ext.raw_data.cache import RawDataCache

    cache = RawDataCache(tmp_path)
    cached_raw = RawStockData(
        symbol="600519",
        trade_date="2026-07-03",
        basic_info={"name": "贵州茅台", "industry": "白酒", "market": "cn"},
        market_snapshot={"close": 1500.0, "pct_change": 1.1},
        kline_summary={"return_20d": 4.5, "pct_change_20d": 4.5, "trend": "up", "volatility": 18.0},
        valuation_raw={"pe": 24.0, "pb": 8.5},
        financial_raw={"roe": 27.0, "net_profit_growth": 14.0},
        capital_flow_raw={},
        northbound_raw={},
        dragon_tiger_raw={},
        announcements_raw=[],
        news_raw=[],
        analyst_raw=[],
        industry_raw={},
        metadata={
            "provider": "akshare",
            "quality_report": {
                "provider": "akshare",
                "quality_level": "good",
                "warnings": [],
                "failed_sources": [],
                "successful_sources": ["cache_seed"],
                "field_coverage_ratio": 0.9,
                "can_score": True,
                "can_make_decision": True,
                "requested_date": "2026-07-03",
                "actual_data_date": "2026-07-03",
                "critical_fields_present": True,
                "missing_fields": [],
                "notes": [],
                "symbol": "600519",
            },
            "data_quality_warnings": [],
        },
    )
    cache.write("akshare", "600519", "2026-07-03", cached_raw)

    fake_ak = SimpleNamespace(
        stock_individual_info_em=lambda symbol: _FakeFrame([]),
        stock_zh_a_spot_em=lambda: _FakeFrame([]),
        stock_zh_a_hist=lambda **kwargs: _FakeFrame([]),
        stock_financial_analysis_indicator=lambda **kwargs: _FakeFrame([]),
        stock_individual_fund_flow=lambda **kwargs: _FakeFrame([]),
        stock_hsgt_individual_em=lambda symbol: _FakeFrame([]),
        stock_lhb_stock_statistic_em=lambda symbol: _FakeFrame([]),
        stock_news_em=lambda symbol: _FakeFrame([]),
        stock_research_report_em=lambda symbol: _FakeFrame([]),
    )
    monkeypatch.setattr("private_ext.raw_data.akshare_collector.ak", fake_ak)

    collector = AkShareRawDataCollector(cache_dir=tmp_path, use_cache=True, refresh=True)
    raw = collector.collect("600519", "2026-07-03")

    assert raw.market_snapshot["close"] == 1500.0
    assert raw.metadata["loaded_from_cache"] is True
    assert "used_stale_cache_due_to_live_failure" in raw.metadata["data_quality_warnings"]
