import pytest
from pathlib import Path

from private_ext.raw_data.cache import RawDataCache

pytestmark = pytest.mark.private_ext


def test_source_level_cache_roundtrip(tmp_path: Path):
    cache = RawDataCache(tmp_path)
    payload = [{"代码": "600519", "名称": "贵州茅台", "最新价": 1500.0}]

    path = cache.write_source("akshare", "stock_zh_a_spot_em", "600519", "2026-07-03", payload)
    loaded = cache.read_source("akshare", "stock_zh_a_spot_em", "600519", "2026-07-03")

    assert path.exists()
    assert "source/stock_zh_a_spot_em/600519_2026-07-03.json" in str(path)
    assert loaded == payload


def test_source_level_cache_returns_none_when_missing(tmp_path: Path):
    cache = RawDataCache(tmp_path)

    assert cache.read_source("akshare", "stock_zh_a_spot_em", "600519", "2026-07-03") is None
