#!/usr/bin/env python
from __future__ import annotations

import importlib.util
import json
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
    "--run-mode",
    "realdata_smoke",
    "--print-json-summary",
]


def main() -> int:
    if importlib.util.find_spec("akshare") is None:
        print("AkShare is not installed. Run: pip install -r requirements-realdata.txt")
        return 1

    result = subprocess.run(COMMAND, cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        print("Real-data smoke failed.")
        return result.returncode

    summary = json.loads(result.stdout)
    print("Realdata smoke completed.")
    print(f"Run directory: {summary['run_dir']}")
    print(f"Report: {summary['reports'][0] if summary['reports'] else '-'}")
    print(f"Database: {summary['database']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
