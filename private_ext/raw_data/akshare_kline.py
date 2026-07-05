from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable


def normalize_a_share_symbol(symbol: str) -> str:
    text = str(symbol or "").strip().upper().replace(".", "")
    for prefix in ("SH", "SZ", "BJ"):
        if text.startswith(prefix):
            text = text[len(prefix):]
        if text.endswith(prefix):
            text = text[: -len(prefix)]
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 6:
        return digits[-6:]
    raise ValueError(f"Unsupported A-share symbol: {symbol}")


def build_akshare_symbol_candidates(symbol: str) -> list[str]:
    normalized = normalize_a_share_symbol(symbol)
    market = infer_market_from_symbol(normalized)
    return [normalized, f"{market}{normalized}"]


def infer_market_from_symbol(symbol: str) -> str:
    normalized = normalize_a_share_symbol(symbol)
    return "sh" if normalized.startswith(("5", "6", "9")) else "sz"


def fetch_hist_kline_with_fallbacks(
    *,
    symbol: str,
    requested_date: str,
    safe_call: Callable[..., list[dict[str, Any]]],
    ak_client: Any,
) -> dict[str, Any]:
    start_date = (datetime.strptime(requested_date, "%Y-%m-%d") - timedelta(days=120)).strftime("%Y%m%d")
    end_date = requested_date.replace("-", "")
    warnings: list[str] = []
    failed_sources: list[str] = []
    successful_sources: list[str] = []
    raw_payloads: dict[str, Any] = {}

    for candidate in build_akshare_symbol_candidates(symbol):
        records = safe_call(
            "stock_zh_a_hist",
            ak_client.stock_zh_a_hist,
            symbol=candidate,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
        raw_payloads[candidate] = records
        if records:
            successful_sources.append("stock_zh_a_hist")
            return {
                "records": records,
                "warnings": warnings,
                "failed_sources": failed_sources,
                "successful_sources": successful_sources,
                "raw": raw_payloads,
            }
        warnings.append(f"stock_zh_a_hist_empty:{candidate}")
    failed_sources.append("stock_zh_a_hist")
    return {
        "records": [],
        "warnings": warnings,
        "failed_sources": failed_sources,
        "successful_sources": successful_sources,
        "raw": raw_payloads,
    }


def extract_latest_close_and_pct_change(rows: Any, *, as_float: Callable[[Any], float | None] | None = None) -> dict[str, Any]:
    ordered = sort_kline_rows(rows)
    if not ordered:
        return {"latest_close": None, "latest_pct_change": None, "actual_data_date": None, "warnings": ["kline_history_missing"]}

    to_float = as_float or _as_float
    closes = [_row_close(row, to_float) for row in ordered]
    valid = [(row, close) for row, close in zip(ordered, closes) if close not in (None, 0)]
    if not valid:
        return {"latest_close": None, "latest_pct_change": None, "actual_data_date": None, "warnings": ["kline_close_missing"]}

    latest_row, latest_close = valid[-1]
    latest_pct_change = None
    if len(valid) >= 2:
        prev_close = valid[-2][1]
        if prev_close not in (None, 0):
            latest_pct_change = latest_close / prev_close - 1
    return {
        "latest_close": latest_close,
        "latest_pct_change": latest_pct_change,
        "actual_data_date": _normalize_date(_row_date(latest_row)),
        "warnings": [],
    }


def compute_kline_returns(rows: Any, *, as_float: Callable[[Any], float | None] | None = None) -> dict[str, Any]:
    ordered = sort_kline_rows(rows)
    extracted = extract_latest_close_and_pct_change(ordered, as_float=as_float)
    warnings = list(extracted.get("warnings", []))
    to_float = as_float or _as_float
    valid = [
        (row, _row_close(row, to_float))
        for row in ordered
    ]
    valid = [(row, close) for row, close in valid if close not in (None, 0)]
    if not valid:
        return {
            **extracted,
            "return_5d": None,
            "return_20d": None,
            "return_60d": None,
            "warnings": warnings,
        }

    closes = [close for _, close in valid]
    return_5d = _window_return(closes, 5)
    return_20d = _window_return(closes, 20)
    return_60d = _window_return(closes, 60)
    if return_20d is None and len(closes) >= 5:
        warnings.append("insufficient_kline_window_for_return_20d")
    return {
        **extracted,
        "return_5d": return_5d,
        "return_20d": return_20d,
        "return_60d": return_60d,
        "warnings": list(dict.fromkeys(warnings)),
    }


def sort_kline_rows(rows: Any) -> list[dict[str, Any]]:
    normalized_rows = _coerce_rows(rows)
    normalized_rows.sort(key=lambda row: _normalize_date(_row_date(row)) or "")
    return normalized_rows


def _coerce_rows(rows: Any) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if isinstance(rows, list):
        return [dict(item) for item in rows if isinstance(item, dict)]
    to_dict = getattr(rows, "to_dict", None)
    if callable(to_dict):
        try:
            return [dict(item) for item in to_dict(orient="records")]
        except Exception:
            return []
    return []


def _row_close(row: dict[str, Any], as_float: Callable[[Any], float | None]) -> float | None:
    for key in ("收盘", "收盘价", "close", "Close"):
        if key in row:
            return as_float(row.get(key))
    return None


def _row_date(row: dict[str, Any]) -> Any:
    for key in ("日期", "date", "Date", "交易日期"):
        if key in row:
            return row.get(key)
    return None


def _window_return(closes: list[float], window: int) -> float | None:
    if len(closes) <= window:
        return None
    base = closes[-window - 1]
    latest = closes[-1]
    if base in (None, 0):
        return None
    return latest / base - 1


def _normalize_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text[:10] if len(text) >= 10 else text


def _as_float(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None
