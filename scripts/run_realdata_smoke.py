#!/usr/bin/env python
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
COMMAND = [
    PYTHON,
    "scripts/run_stock_report.py",
    "--stocks",
    "600519",
    "--date",
    "2026-07-03",
    "--raw-data",
    "akshare",
    "--research-adapter",
    "mock",
    "--paper-trading",
    "off",
]


def main() -> int:
    if importlib.util.find_spec("akshare") is None:
        print("AkShare is not installed. Run: pip install -r requirements-realdata.txt")
        return 1

    result = subprocess.run(COMMAND, cwd=ROOT, check=False)
    if result.returncode != 0:
        print("Real-data smoke failed.")
        return result.returncode

    print("Real-data smoke passed.")
    print("Report path: storage/reports/stock_report_600519_2026-07-03.md")
    print("Database path: storage/research.sqlite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
