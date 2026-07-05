#!/usr/bin/env python
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from private_ext.config import settings
from private_ext.database.repo import ResearchRepository


def _latest_quality_by_run(db_path: Path) -> dict[tuple[str, str], dict]:
    result: dict[tuple[str, str], dict] = {}
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT symbol, trade_date, raw_json
            FROM raw_data_snapshots
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()
    for symbol, trade_date, raw_json in rows:
        key = (symbol, trade_date)
        if key in result:
            continue
        try:
            payload = json.loads(raw_json)
        except Exception:
            continue
        quality = payload.get("metadata", {}).get("quality_report")
        if isinstance(quality, dict):
            result[key] = quality
    return result


def main() -> int:
    repo = ResearchRepository(settings.db_path)
    print(f"Database: {settings.db_path}")
    print()
    for table, count in repo.table_counts().items():
        print(f"{table}: {count}")
    latest_runs = repo.latest_runs()
    if latest_runs:
        print()
        print("Latest Runs:")
        quality_by_run = _latest_quality_by_run(settings.db_path)
        for run in latest_runs:
            line = (
                f"{run['run_date']} {run['symbol']} {run['raw_data_provider']} "
                f"{run['research_adapter']} {run['status']}"
            )
            quality = quality_by_run.get((run["symbol"], run["run_date"]))
            if quality:
                line += (
                    f" quality={quality.get('quality_level')}"
                    f" coverage={quality.get('field_coverage_ratio')}"
                    f" failed_sources={len(quality.get('failed_sources', []))}"
                )
            if run.get("error_message"):
                line += f" error={run['error_message']}"
            print(line)
    latest_nav = repo.latest_nav()
    if latest_nav:
        print()
        print("Latest NAV:")
        print(f"cash: {latest_nav['cash']}")
        print(f"market_value: {latest_nav['market_value']}")
        print(f"total_nav: {latest_nav['total_nav']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
