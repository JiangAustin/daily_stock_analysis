#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from private_ext.config import settings
from private_ext.database.repo import ResearchRepository


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
        for run in latest_runs:
            line = (
                f"{run['run_date']} {run['symbol']} {run['raw_data_provider']} "
                f"{run['research_adapter']} {run['status']}"
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
