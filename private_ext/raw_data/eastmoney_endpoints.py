from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from private_ext.raw_data.eastmoney_parsers import (
    parse_financial_payload,
    parse_kline_payload,
    parse_snapshot_payload,
)


@dataclass(frozen=True)
class EndpointCandidate:
    name: str
    group: str
    purpose: str
    target_fields: list[str]
    fetcher: Callable[..., Any]
    parser: Callable[[Any], dict[str, Any]]
    priority: int = 0
    notes: list[str] = field(default_factory=list)


def build_default_endpoint_candidates(
    fetchers: dict[str, Callable[..., Any]] | None = None,
) -> dict[str, list[EndpointCandidate]]:
    fetchers = fetchers or {}
    def pick(candidate_name: str, group_name: str, default: Callable[..., Any]) -> Callable[..., Any]:
        return fetchers.get(candidate_name) or fetchers.get(group_name) or default
    return {
        "snapshot": [
            EndpointCandidate(
                name="eastmoney_push2_snapshot",
                group="snapshot",
                purpose="push2 snapshot",
                target_fields=["close", "pct_change", "turnover_rate", "market_cap", "pe", "pb"],
                fetcher=pick("eastmoney_push2_snapshot", "snapshot", _fetch_snapshot),
                parser=parse_snapshot_payload,
                priority=1,
            ),
            EndpointCandidate(
                name="eastmoney_quote_snapshot_fallback",
                group="snapshot",
                purpose="quote snapshot fallback",
                target_fields=["close", "pct_change", "turnover_rate", "market_cap", "pe", "pb"],
                fetcher=pick("eastmoney_quote_snapshot_fallback", "snapshot", _fetch_snapshot_fallback),
                parser=parse_snapshot_payload,
                priority=2,
            ),
        ],
        "valuation": [
            EndpointCandidate(
                name="eastmoney_snapshot_valuation",
                group="valuation",
                purpose="snapshot valuation",
                target_fields=["pe", "pb"],
                fetcher=pick("eastmoney_snapshot_valuation", "valuation", _fetch_valuation),
                parser=parse_snapshot_payload,
                priority=1,
            ),
            EndpointCandidate(
                name="eastmoney_info_valuation_fallback",
                group="valuation",
                purpose="info valuation fallback",
                target_fields=["pe", "pb"],
                fetcher=pick("eastmoney_info_valuation_fallback", "valuation", _fetch_valuation_fallback),
                parser=parse_snapshot_payload,
                priority=2,
            ),
        ],
        "kline": [
            EndpointCandidate(
                name="eastmoney_push2his_kline",
                group="kline",
                purpose="push2his kline",
                target_fields=["close", "pct_change", "return_5d", "return_20d", "return_60d", "actual_data_date"],
                fetcher=pick("eastmoney_push2his_kline", "kline", _fetch_kline),
                parser=parse_kline_payload,
                priority=1,
            ),
            EndpointCandidate(
                name="eastmoney_kline_fallback",
                group="kline",
                purpose="kline fallback",
                target_fields=["close", "pct_change", "return_5d", "return_20d", "return_60d", "actual_data_date"],
                fetcher=pick("eastmoney_kline_fallback", "kline", _fetch_kline_fallback),
                parser=parse_kline_payload,
                priority=2,
            ),
        ],
        "financial": [
            EndpointCandidate(
                name="eastmoney_financial_indicator",
                group="financial",
                purpose="financial metrics",
                target_fields=["roe", "net_profit_growth"],
                fetcher=pick("eastmoney_financial_indicator", "financial", _fetch_financial),
                parser=parse_financial_payload,
                priority=1,
            ),
        ],
    }


def eastmoney_secid(symbol: str) -> str:
    return f"{1 if symbol.startswith(('5', '6', '9')) else 0}.{symbol}"


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://quote.eastmoney.com/",
    "Connection": "close",
}


def http_get_json(base_url: str, params: dict[str, str], timeout: float = 8.0) -> dict[str, Any]:
    url = f"{base_url}?{urlencode(params)}"
    try:
        request = Request(url, headers=DEFAULT_HEADERS)
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:  # pragma: no cover
        raise RuntimeError(f"eastmoney_http_status:{exc.code}") from exc
    except URLError as exc:  # pragma: no cover
        raise RuntimeError(f"eastmoney_http_error:{exc.reason}") from exc


def _fetch_snapshot(symbol: str) -> dict[str, Any]:
    return http_get_json(
        "https://push2.eastmoney.com/api/qt/stock/get",
        {"secid": eastmoney_secid(symbol), "fields": "f57,f58,f43,f168,f170,f116,f9,f23"},
    )


def _fetch_snapshot_fallback(symbol: str) -> dict[str, Any]:
    return http_get_json(
        "https://push2.eastmoney.com/api/qt/stock/get",
        {"secid": eastmoney_secid(symbol), "fields": "f43,f170,f168,f116"},
    )


def _fetch_valuation(symbol: str) -> dict[str, Any]:
    return http_get_json(
        "https://push2.eastmoney.com/api/qt/stock/get",
        {"secid": eastmoney_secid(symbol), "fields": "f57,f58,f9,f23"},
    )


def _fetch_valuation_fallback(symbol: str) -> dict[str, Any]:
    return http_get_json(
        "https://push2.eastmoney.com/api/qt/stock/get",
        {"secid": eastmoney_secid(symbol), "fields": "f9,f23"},
    )


def _fetch_kline(symbol: str, trade_date: str) -> dict[str, Any]:
    from datetime import datetime, timedelta

    start_date = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=120)).strftime("%Y%m%d")
    return http_get_json(
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        {
            "secid": eastmoney_secid(symbol),
            "klt": "101",
            "fqt": "1",
            "beg": start_date,
            "end": trade_date.replace("-", ""),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        },
    )


def _fetch_kline_fallback(symbol: str, trade_date: str) -> dict[str, Any]:
    from datetime import datetime, timedelta

    start_date = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=180)).strftime("%Y%m%d")
    return http_get_json(
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        {
            "secid": eastmoney_secid(symbol),
            "klt": "101",
            "fqt": "0",
            "beg": start_date,
            "end": trade_date.replace("-", ""),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        },
    )


def _fetch_financial(symbol: str) -> list[dict[str, Any]]:
    return []
