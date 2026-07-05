from __future__ import annotations

import pytest


pytestmark = [pytest.mark.private_ext]


class _FakeFrame:
    def __init__(self, rows):
        self.rows = rows

    def to_dict(self, orient: str = "records"):
        assert orient == "records"
        return list(self.rows)


def test_snapshot_parser_extracts_close_pct_change_pe_pb_from_dict():
    from private_ext.raw_data.eastmoney_parsers import parse_snapshot_payload

    parsed = parse_snapshot_payload(
        {
            "f43": 150000,
            "f170": 125,
            "f168": 45,
            "f116": 1900000000000,
            "f9": 24.5,
            "f23": 8.6,
        }
    )

    assert parsed["fields"]["close"] == 1500.0
    assert parsed["fields"]["pct_change"] == 0.0125
    assert parsed["fields"]["pe"] == 24.5
    assert parsed["fields"]["pb"] == 8.6


def test_snapshot_parser_handles_missing_markers():
    from private_ext.raw_data.eastmoney_parsers import parse_snapshot_payload

    parsed = parse_snapshot_payload({"f43": "--", "f170": "-", "f9": None, "f23": ""})

    assert parsed["fields"]["close"] is None
    assert parsed["fields"]["pct_change"] is None
    assert parsed["fields"]["pe"] is None
    assert parsed["fields"]["pb"] is None


def test_kline_parser_computes_return20d_from_list_str():
    from private_ext.raw_data.eastmoney_parsers import parse_kline_payload

    payload = [
        f"2026-06-{day:02d},10.{day:02d},10.{day:02d},10.{day:02d},10.{day:02d},10000"
        for day in range(1, 26)
    ]

    parsed = parse_kline_payload(payload)

    assert parsed["fields"]["return_20d"] is not None
    assert parsed["fields"]["actual_data_date"] == "2026-06-25"


def test_kline_parser_computes_close_and_pct_change_from_dataframe_like():
    from private_ext.raw_data.eastmoney_parsers import parse_kline_payload

    payload = _FakeFrame(
        [
            {"date": "2026-07-01", "close": 10.0},
            {"date": "2026-07-02", "close": 10.2},
            {"date": "2026-07-03", "close": 10.5},
        ]
    )

    parsed = parse_kline_payload(payload)

    assert parsed["fields"]["close"] == 10.5
    assert parsed["fields"]["pct_change"] is not None
