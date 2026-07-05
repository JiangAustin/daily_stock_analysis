#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from private_ext.raw_data import AkShareNotInstalledError, create_raw_data_collector


def main() -> int:
    args = parse_args()
    try:
        collector = create_raw_data_collector(
            args.raw_data,
            use_cache=True,
            refresh=args.refresh_data,
        )
    except (AkShareNotInstalledError, NotImplementedError, ValueError) as exc:
        print(str(exc))
        return 1

    stocks = [item.strip() for item in args.stocks.split(",") if item.strip()]
    reports: list[dict[str, str]] = []
    failed_count = 0
    for symbol in stocks:
        try:
            raw = collector.collect(symbol, args.date)
        except Exception as exc:
            failed_count += 1
            reports.append(
                {
                    "symbol": symbol,
                    "provider": args.raw_data,
                    "quality_level": "failed",
                    "coverage": "0.0",
                    "can_score": "False",
                    "can_make_decision": "False",
                    "failed_sources": f"collector_error:{type(exc).__name__}",
                    "missing_fields": "all",
                }
            )
            continue

        quality = raw.metadata.get("quality_report", {})
        reports.append(
            {
                "symbol": raw.symbol,
                "provider": quality.get("provider", args.raw_data),
                "quality_level": str(quality.get("quality_level", "unknown")),
                "coverage": str(quality.get("field_coverage_ratio", "")),
                "can_score": str(quality.get("can_score", False)),
                "can_make_decision": str(quality.get("can_make_decision", False)),
                "failed_sources": ",".join(quality.get("failed_sources", [])) or "-",
                "missing_fields": ",".join(quality.get("missing_fields", [])) or "-",
            }
        )

    _print_table(reports)
    if reports and all(item["quality_level"] == "failed" for item in reports):
        return 1
    if failed_count or any(item["quality_level"] in {"degraded", "poor"} for item in reports):
        print("WARNING: some symbols are degraded or poor.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check raw-data provider health without running reports.")
    parser.add_argument("--stocks", default="600519,000001,300750")
    parser.add_argument("--date", default="2026-07-03")
    parser.add_argument("--raw-data", default="akshare")
    parser.add_argument("--refresh-data", action="store_true")
    return parser.parse_args()


def _print_table(rows: list[dict[str, str]]) -> None:
    headers = [
        "symbol",
        "provider",
        "quality_level",
        "coverage",
        "can_score",
        "can_make_decision",
        "failed_sources",
        "missing_fields",
    ]
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        print("| " + " | ".join(row.get(header, "") for header in headers) + " |")


if __name__ == "__main__":
    raise SystemExit(main())
