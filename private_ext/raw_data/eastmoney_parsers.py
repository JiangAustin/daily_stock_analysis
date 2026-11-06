from __future__ import annotations

import math
from typing import Any

from private_ext.raw_data.akshare_kline import compute_kline_returns, sort_kline_rows


SNAPSHOT_FIELDS = ["close", "pct_change", "turnover_rate", "market_cap", "pe", "pb"]
KLINE_FIELDS = ["close", "pct_change", "return_5d", "return_20d", "return_60d", "actual_data_date"]
FINANCIAL_FIELDS = ["roe", "net_profit_growth"]


def parse_snapshot_payload(payload: Any) -> dict[str, Any]:
    row = _first_row(payload)
    fields = {
        "close": _normalize_price(_first_present(row, ["f43", "close", "最新价"])),
        "pct_change": _normalize_ratio(_first_present(row, ["f170", "pct_change", "涨跌幅"])),
        "turnover_rate": _normalize_percent(_first_present(row, ["f168", "turnover_rate", "换手率"])),
        "market_cap": _normalize_numeric(_first_present(row, ["f116", "market_cap", "总市值"])),
        "pe": _normalize_numeric(_first_present(row, ["f9", "pe", "市盈率"])),
        "pb": _normalize_numeric(_first_present(row, ["f23", "pb", "市净率"])),
    }
    return _build_parsed(fields, raw_shape=_shape_of(payload))


def parse_financial_payload(payload: Any) -> dict[str, Any]:
    row = _first_row(payload)
    fields = {
        "roe": _normalize_numeric(_first_present(row, ["roe", "净资产收益率", "ROE"])),
        "net_profit_growth": _normalize_numeric(_first_present(row, ["net_profit_growth", "净利润增长率"])),
    }
    return _build_parsed(fields, raw_shape=_shape_of(payload))


def parse_kline_payload(payload: Any) -> dict[str, Any]:
    rows = _coerce_kline_rows(payload)
    rows = sort_kline_rows(rows)
    result = compute_kline_returns(rows, as_float=_normalize_numeric)
    fields = {
        "close": result.get("latest_close"),
        "pct_change": result.get("latest_pct_change"),
        "return_5d": result.get("return_5d"),
        "return_20d": result.get("return_20d"),
        "return_60d": result.get("return_60d"),
        "actual_data_date": result.get("actual_data_date"),
        "return_available_window": max(0, len(rows) - 1),
    }
    parsed = _build_parsed(fields, raw_shape=_shape_of(payload), report_fields=KLINE_FIELDS)
    parsed["rows"] = rows
    parsed["warnings"] = list(result.get("warnings", []))
    return parsed


def _build_parsed(fields: dict[str, Any], *, raw_shape: str, report_fields: list[str] | None = None) -> dict[str, Any]:
    field_names = list(report_fields or fields.keys())
    fields_found = [key for key, value in fields.items() if value not in (None, "", [], {}) and key in field_names]
    fields_missing = [key for key in field_names if key not in fields_found]
    return {
        "fields": fields,
        "fields_found": fields_found,
        "fields_missing": fields_missing,
        "raw_shape": raw_shape,
    }


def _coerce_kline_rows(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        rows: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, str):
                parts = item.split(",")
                if len(parts) >= 3:
                    rows.append({"date": parts[0], "close": _normalize_numeric(parts[2])})
            elif isinstance(item, dict):
                rows.append(
                    {
                        "date": _first_present(item, ["date", "日期", "f51"]),
                        "close": _normalize_numeric(_first_present(item, ["close", "收盘", "f53", "f43"])),
                    }
                )
        return rows
    to_dict = getattr(payload, "to_dict", None)
    if callable(to_dict):
        return _coerce_kline_rows(to_dict(orient="records"))
    return []


def _first_row(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        data = payload.get("data") if "data" in payload and isinstance(payload.get("data"), dict) else payload
        return data if isinstance(data, dict) else {}
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                return item
    to_dict = getattr(payload, "to_dict", None)
    if callable(to_dict):
        rows = to_dict(orient="records")
        return rows[0] if rows else {}
    return {}


def _first_present(payload: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = payload.get(key) if isinstance(payload, dict) else None
        if not _is_missing(value):
            return value
    return None


def _normalize_price(value: Any) -> float | None:
    number = _normalize_numeric(value)
    if number is None:
        return None
    return number / 100 if abs(number) > 10000 else number


def _normalize_ratio(value: Any) -> float | None:
    number = _normalize_numeric(value)
    if number is None:
        return None
    return number / 10000 if abs(number) > 1 else number


def _normalize_percent(value: Any) -> float | None:
    number = _normalize_numeric(value)
    if number is None:
        return None
    return number / 100 if abs(number) > 1 else number


def _normalize_numeric(value: Any) -> float | None:
    if _is_missing(value):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text or text in {"--", "-", "N/A", "nan"}:
        return None
    if "亿" in text or "万" in text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _is_missing(value: Any) -> bool:
    return value in (None, "", "-", "--", "N/A", [], {}) or (
        isinstance(value, float) and math.isnan(value)
    )


def _shape_of(payload: Any) -> str:
    if isinstance(payload, dict):
        return "dict"
    if isinstance(payload, list):
        return f"list[{len(payload)}]"
    if hasattr(payload, "to_dict"):
        return "dataframe_like"
    return type(payload).__name__
