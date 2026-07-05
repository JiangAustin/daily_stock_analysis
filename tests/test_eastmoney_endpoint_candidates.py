from __future__ import annotations

import pytest


pytestmark = [pytest.mark.private_ext]


def test_endpoint_group_tries_candidates_by_priority_and_stops_after_success(tmp_path):
    from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector

    calls: list[str] = []

    def first_snapshot(symbol):
        calls.append("first")
        return {"data": {"f43": 150000, "f170": 125}}

    def second_snapshot(symbol):
        calls.append("second")
        return {"data": {"f43": 160000, "f170": 225}}

    collector = EastMoneyRawDataCollector(
        cache_dir=tmp_path,
        use_cache=False,
        refresh=True,
        fetchers={"eastmoney_push2_snapshot": first_snapshot, "eastmoney_quote_snapshot_fallback": second_snapshot},
    )

    diagnostics = collector.probe_endpoints("600519", "2026-07-03", group="snapshot")

    assert calls == ["first"]
    assert diagnostics["best_candidate_by_group"]["snapshot"] == "eastmoney_push2_snapshot"


def test_candidate_parsed_empty_does_not_count_as_success(tmp_path):
    from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector

    def empty_snapshot(symbol):
        return {"data": {}}

    collector = EastMoneyRawDataCollector(
        cache_dir=tmp_path,
        use_cache=False,
        refresh=True,
        fetchers={
            "eastmoney_push2_snapshot": empty_snapshot,
            "eastmoney_quote_snapshot_fallback": empty_snapshot,
        },
    )

    diagnostics = collector.probe_endpoints("600519", "2026-07-03", group="snapshot")

    result = diagnostics["candidate_results"][0]
    assert result["status"] == "parsed_empty"
    assert diagnostics["group_status"]["snapshot"] == "skipped"


def test_candidate_live_fail_can_use_candidate_cache(tmp_path):
    from private_ext.raw_data.cache import RawDataCache
    from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector

    cache = RawDataCache(tmp_path)
    cache.write_source(
        "eastmoney",
        "eastmoney_push2_snapshot",
        "600519",
        "2026-07-03",
        [{"f43": 150000, "f170": 125}],
    )

    def failing_snapshot(symbol):
        raise RuntimeError("RemoteDisconnected")

    collector = EastMoneyRawDataCollector(
        cache_dir=tmp_path,
        use_cache=True,
        refresh=True,
        fetchers={"eastmoney_push2_snapshot": failing_snapshot},
    )

    diagnostics = collector.probe_endpoints("600519", "2026-07-03", group="snapshot")

    result = diagnostics["candidate_results"][0]
    assert result["status"] == "cache"
    assert result["used_cache"] is True
    assert result["candidate_name"] == "eastmoney_push2_snapshot"
    assert "snapshot" in diagnostics["successful_endpoints"]
