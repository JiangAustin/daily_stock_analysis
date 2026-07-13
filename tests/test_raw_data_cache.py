from pathlib import Path

from private_ext.raw_data.cache import RawDataCache
from private_ext.raw_data.models import RawStockData


def _sample_raw() -> RawStockData:
    return RawStockData(
        symbol="600519",
        trade_date="2026-07-03",
        basic_info={"name": "贵州茅台", "industry": "白酒"},
        market_snapshot={"close": 1500.0},
        kline_summary={"return_20d": 5.0},
        valuation_raw={"pe": 24.0, "pb": 8.0},
        financial_raw={"roe": 27.0, "net_profit_growth": 14.0},
        capital_flow_raw={},
        northbound_raw={},
        dragon_tiger_raw={},
        announcements_raw=[],
        news_raw=[],
        analyst_raw=[],
        industry_raw={},
        metadata={"provider": "akshare"},
    )


def test_raw_data_cache_roundtrip(tmp_path: Path):
    cache = RawDataCache(tmp_path)
    raw = _sample_raw()

    cache.write("akshare", raw.symbol, raw.trade_date, raw)
    loaded = cache.read("akshare", raw.symbol, raw.trade_date)

    assert loaded is not None
    assert loaded.symbol == raw.symbol
    assert loaded.market_snapshot["close"] == 1500.0


def test_raw_data_cache_returns_none_when_missing(tmp_path: Path):
    cache = RawDataCache(tmp_path)

    assert cache.read("akshare", "600519", "2026-07-03") is None
