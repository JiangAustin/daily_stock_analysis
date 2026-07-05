#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
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
                "providers_used": ",".join(raw.metadata.get("providers_used", [])) or quality.get("provider", args.raw_data),
                "quality_level": str(quality.get("quality_level", "unknown")),
                "coverage": str(quality.get("field_coverage_ratio", "")),
                "close": _format_value((raw.market_snapshot or {}).get("close")),
                "pct_change": _format_value((raw.market_snapshot or {}).get("pct_change")),
                "return_20d": _format_value((raw.kline_summary or {}).get("return_20d")),
                "can_score": str(quality.get("can_score", False)),
                "can_make_decision": str(quality.get("can_make_decision", False)),
                "failed_sources": ",".join(quality.get("failed_sources", [])) or "-",
                "missing_fields": ",".join(quality.get("missing_fields", [])) or "-",
            }
        )
        if args.verbose:
            _print_verbose(raw.symbol, quality)

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
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def _print_table(rows: list[dict[str, str]]) -> None:
    headers = [
        "symbol",
        "quality_level",
        "coverage",
        "close",
        "pct_change",
        "return_20d",
        "can_make_decision",
        "provider",
        "providers_used",
        "can_score",
        "failed_sources",
        "missing_fields",
    ]
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        print("| " + " | ".join(row.get(header, "") for header in headers) + " |")


def _print_verbose(symbol: str, quality: dict[str, object]) -> None:
    print(f"\n[{symbol}] verbose quality detail")
    print("providers_used:", ",".join(quality.get("providers_used", [])) or "-")
    print("provider_reports:")
    print(json.dumps(quality.get("provider_reports", {}), ensure_ascii=False, indent=2, sort_keys=True))
    print("merge_warnings:", ",".join(quality.get("merge_warnings", [])) or "-")
    print("critical_field_status:")
    print(json.dumps(quality.get("critical_field_status", {}), ensure_ascii=False, indent=2, sort_keys=True))
    print("source_cache_used:", ",".join(quality.get("source_cache_used", [])) or "-")
    print("live_success_count:", quality.get("live_success_count", 0))
    print("cache_success_count:", quality.get("cache_success_count", 0))
    print("live_failure_count:", quality.get("live_failure_count", 0))
    print("failed_sources:", ",".join(quality.get("failed_sources", [])) or "-")
    print("field_provenance_summary:")
    print(
        json.dumps(
            quality.get("field_provenance_summary", {}),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    diagnostics = (
        quality.get("diagnostics")
        or quality.get("provider_reports", {}).get("eastmoney", {}).get("diagnostics", {})
    )
    if diagnostics:
        print("EastMoney Endpoint Diagnostics:")
        for item in diagnostics.get("endpoint_results", []):
            print(
                "{endpoint}: {status} fields_found={fields_found} fields_missing={fields_missing} error_type={error_type} used_cache={used_cache} elapsed_ms={elapsed_ms}".format(
                    endpoint=item.get("endpoint_name"),
                    status=item.get("status"),
                    fields_found=item.get("fields_found", []),
                    fields_missing=item.get("fields_missing", []),
                    error_type=item.get("error_type") or "-",
                    used_cache=item.get("used_cache"),
                    elapsed_ms=item.get("elapsed_ms", 0),
                )
            )
        candidate_results = diagnostics.get("candidate_results", [])
        if candidate_results:
            print("EastMoney Candidate Diagnostics:")
            print("| group | candidate | status | fields_found | fields_missing | error_type | used_cache | elapsed_ms |")
            print("|---|---|---|---|---|---|---|---|")
            for item in candidate_results:
                print(
                    "| {group} | {candidate} | {status} | {fields_found} | {fields_missing} | {error_type} | {used_cache} | {elapsed_ms} |".format(
                        group=item.get("endpoint_group", "-"),
                        candidate=item.get("candidate_name", "-"),
                        status=item.get("status", "-"),
                        fields_found=",".join(item.get("fields_found", [])) or "-",
                        fields_missing=",".join(item.get("fields_missing", [])) or "-",
                        error_type=item.get("error_type") or "-",
                        used_cache=item.get("used_cache"),
                        elapsed_ms=item.get("elapsed_ms", 0),
                    )
                )


def _format_value(value: object) -> str:
    if value in (None, "", [], {}):
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
