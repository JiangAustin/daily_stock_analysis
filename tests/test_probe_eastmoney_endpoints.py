from __future__ import annotations

import pytest


pytestmark = [pytest.mark.private_ext]


def test_probe_script_returns_zero_when_any_candidate_succeeds(monkeypatch, capsys):
    import scripts.probe_eastmoney_endpoints as probe

    class FakeCollector:
        def probe_endpoints(self, symbol: str, trade_date: str, group: str | None = None, refresh: bool = False):
            return {
                "candidate_results": [
                    {
                        "endpoint_group": group or "snapshot",
                        "candidate_name": "c1",
                        "status": "success",
                        "fields_found": ["close"],
                        "fields_missing": [],
                        "error_type": None,
                        "used_cache": False,
                        "elapsed_ms": 1,
                    }
                ]
            }

    monkeypatch.setattr(probe, "create_raw_data_collector", lambda *args, **kwargs: FakeCollector())
    code = probe.main(["--stocks", "600519"])
    out = capsys.readouterr().out

    assert code == 0
    assert "c1" in out


def test_probe_script_returns_one_when_all_candidates_fail(monkeypatch, capsys):
    import scripts.probe_eastmoney_endpoints as probe

    class FakeCollector:
        def probe_endpoints(self, symbol: str, trade_date: str, group: str | None = None, refresh: bool = False):
            return {
                "candidate_results": [
                    {
                        "endpoint_group": group or "snapshot",
                        "candidate_name": "c1",
                        "status": "failed",
                        "fields_found": [],
                        "fields_missing": ["close"],
                        "error_type": "RuntimeError",
                        "used_cache": False,
                        "elapsed_ms": 1,
                    }
                ]
            }

    monkeypatch.setattr(probe, "create_raw_data_collector", lambda *args, **kwargs: FakeCollector())
    code = probe.main(["--stocks", "600519", "--print-json"])
    out = capsys.readouterr().out

    assert code == 1
    assert '"status": "failed"' in out
