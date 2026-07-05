#!/usr/bin/env python
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real-data smoke for a single stock.")
    parser.add_argument("--raw-data", default="akshare", choices=["akshare", "composite", "eastmoney"])
    parser.add_argument("--stock", default="600519")
    parser.add_argument("--date", default="2026-07-03")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.raw_data in {"akshare", "composite"} and importlib.util.find_spec("akshare") is None:
        print("AkShare is not installed. Run: pip install -r requirements-realdata.txt")
        return 1

    command = [
        PYTHON,
        "scripts/run_stock_report.py",
        "--stocks",
        args.stock,
        "--date",
        args.date,
        "--raw-data",
        args.raw_data,
        "--research-adapter",
        "mock",
        "--paper-trading",
        "off",
        "--run-mode",
        "realdata_smoke",
        "--print-json-summary",
    ]

    result = subprocess.run(command, cwd=ROOT, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        print("Real-data smoke failed.")
        return result.returncode

    summary = json.loads(result.stdout)
    print("Realdata smoke completed.")
    print(f"Raw data provider: {args.raw_data}")
    print(f"Run directory: {summary['run_dir']}")
    print(f"Report: {summary['reports'][0] if summary['reports'] else '-'}")
    print(f"Database: {summary['database']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
