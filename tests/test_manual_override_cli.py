from __future__ import annotations

from pathlib import Path

import pytest

from scripts import check_realdata_health, run_stock_report


pytestmark = [pytest.mark.private_ext]


def test_run_stock_report_parses_manual_args():
    args = run_stock_report._parse_args(
        [
            "--stocks",
            "600519",
            "--date",
            "2026-07-03",
            "--raw-data",
            "composite_manual",
            "--manual-data-dir",
            "storage/manual_data",
            "--manual-file-format",
            "auto",
            "--research-adapter",
            "mock",
            "--paper-trading",
            "off",
        ]
    )

    assert args.manual_data_dir == "storage/manual_data"
    assert args.manual_file_format == "auto"


def test_check_realdata_health_parses_manual_args():
    args = check_realdata_health.parse_args(
        [
            "--stocks",
            "600519",
            "--date",
            "2026-07-03",
            "--raw-data",
            "manual_csv",
            "--manual-data-dir",
            "storage/manual_data",
            "--manual-file-format",
            "csv",
        ]
    )

    assert args.manual_data_dir == "storage/manual_data"
    assert args.manual_file_format == "csv"


def test_check_realdata_health_reads_manual_csv(tmp_path: Path, monkeypatch, capsys):
    manual_dir = tmp_path / "manual_data"
    manual_dir.mkdir(parents=True, exist_ok=True)
    (manual_dir / "600519_2026-07-03.csv").write_text(
        "field,value,source_note,source_url,updated_at,confidence,allow_override\n"
        "market_snapshot.close,1500,manual csv close,https://example.com/manual,2026-07-05,high,false\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "check_realdata_health.py",
            "--stocks",
            "600519",
            "--date",
            "2026-07-03",
            "--raw-data",
            "manual_csv",
            "--manual-data-dir",
            str(manual_dir),
            "--manual-file-format",
            "csv",
        ],
    )

    exit_code = check_realdata_health.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "manual_csv" in captured.out
