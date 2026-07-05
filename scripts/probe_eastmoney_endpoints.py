#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from private_ext.raw_data import create_raw_data_collector


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe EastMoney endpoint candidates without running reports.")
    parser.add_argument("--stocks", default="600519,000001,300750")
    parser.add_argument("--date", default="2026-07-03")
    parser.add_argument("--group", choices=["snapshot", "kline", "valuation", "financial"])
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    collector = create_raw_data_collector("eastmoney", use_cache=True, refresh=args.refresh_data)
    rows: list[dict[str, object]] = []
    success = False
    for symbol in [item.strip() for item in args.stocks.split(",") if item.strip()]:
        diagnostics = collector.probe_endpoints(symbol, args.date, group=args.group, refresh=args.refresh_data)
        for item in diagnostics.get("candidate_results", []):
            row = {
                "symbol": symbol,
                "group": item.get("endpoint_group"),
                "candidate": item.get("candidate_name"),
                "status": item.get("status"),
                "fields_found": item.get("fields_found", []),
                "fields_missing": item.get("fields_missing", []),
                "error_type": item.get("error_type"),
                "used_cache": item.get("used_cache"),
                "elapsed_ms": item.get("elapsed_ms", 0),
            }
            rows.append(row)
            if item.get("status") in {"success", "cache"}:
                success = True

    if args.print_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        headers = ["symbol", "group", "candidate", "status", "fields_found", "fields_missing", "error_type", "used_cache", "elapsed_ms"]
        print("| " + " | ".join(headers) + " |")
        print("|" + "|".join(["---"] * len(headers)) + "|")
        for row in rows:
            print(
                "| {symbol} | {group} | {candidate} | {status} | {fields_found} | {fields_missing} | {error_type} | {used_cache} | {elapsed_ms} |".format(
                    symbol=row["symbol"],
                    group=row["group"],
                    candidate=row["candidate"],
                    status=row["status"],
                    fields_found=",".join(row["fields_found"]) if row["fields_found"] else "-",
                    fields_missing=",".join(row["fields_missing"]) if row["fields_missing"] else "-",
                    error_type=row["error_type"] or "-",
                    used_cache=row["used_cache"],
                    elapsed_ms=row["elapsed_ms"],
                )
            )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
