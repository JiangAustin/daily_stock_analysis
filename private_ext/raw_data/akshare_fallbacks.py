from __future__ import annotations

from typing import Any


KEY_FIELDS = [
    "market_snapshot.close",
    "market_snapshot.pct_change",
    "market_snapshot.turnover_rate",
    "market_snapshot.market_cap",
    "valuation_raw.pe",
    "valuation_raw.pb",
    "financial_raw.roe",
    "financial_raw.net_profit_growth",
    "kline_summary.return_5d",
    "kline_summary.return_20d",
    "kline_summary.return_60d",
]


def build_field_provenance(
    *,
    source: str | None,
    fallback_level: int,
    is_cached: bool,
    confidence: str,
) -> dict[str, Any]:
    return {
        "source": source,
        "fallback_level": fallback_level,
        "is_cached": is_cached,
        "confidence": confidence,
    }


def fill_market_snapshot(
    *,
    spot_row: dict[str, Any],
    info_map: dict[str, Any],
    hist_summary: dict[str, Any],
    source_context: dict[str, dict[str, Any]],
    cached_raw: dict[str, Any] | None = None,
    as_float,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[str]]:
    snapshot: dict[str, Any] = {"currency": "CNY"}
    provenance: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    def candidate(value, source: str | None, fallback_level: int, confidence: str):
        is_cached = source == "raw_cache" or bool(source and source_context.get(source, {}).get("is_cached"))
        return value, build_field_provenance(
            source=source,
            fallback_level=fallback_level,
            is_cached=is_cached,
            confidence=confidence,
        )

    close, close_prov = first_available(
        [
            candidate(as_float(first_present(spot_row, ["最新价", "收盘"])), "stock_zh_a_spot_em", 0, "high"),
            candidate(as_float(hist_summary.get("latest_close")), "stock_zh_a_hist", 1, "medium"),
            candidate(as_float((cached_raw or {}).get("market_snapshot", {}).get("close")), "raw_cache", 2, "medium"),
        ]
    )
    pct_change, pct_change_prov = first_available(
        [
            candidate(as_float(first_present(spot_row, ["涨跌幅", "涨跌幅(%)"])), "stock_zh_a_spot_em", 0, "high"),
            candidate(as_float(hist_summary.get("latest_pct_change")), "stock_zh_a_hist", 1, "medium"),
            candidate(
                as_float((cached_raw or {}).get("market_snapshot", {}).get("pct_change")),
                "raw_cache",
                2,
                "medium",
            ),
        ]
    )
    turnover_rate, turnover_rate_prov = first_available(
        [
            candidate(as_float(first_present(spot_row, ["换手率"])), "stock_zh_a_spot_em", 0, "high"),
            candidate(
                as_float((cached_raw or {}).get("market_snapshot", {}).get("turnover_rate")),
                "raw_cache",
                2,
                "low",
            ),
        ]
    )
    market_cap, market_cap_prov = first_available(
        [
            candidate(as_float(first_present(spot_row, ["总市值"])), "stock_zh_a_spot_em", 0, "high"),
            candidate(as_float(first_present(info_map, ["总市值"])), "stock_individual_info_em", 1, "medium"),
            candidate(
                as_float(
                    first_present(
                        (cached_raw or {}).get("market_snapshot", {}),
                        ["market_cap", "total_market_value"],
                    )
                ),
                "raw_cache",
                2,
                "low",
            ),
        ]
    )
    float_market_cap, _ = first_available(
        [
            candidate(as_float(first_present(spot_row, ["流通市值"])), "stock_zh_a_spot_em", 0, "high"),
            candidate(as_float(first_present(info_map, ["流通市值"])), "stock_individual_info_em", 1, "medium"),
            candidate(
                as_float(
                    first_present(
                        (cached_raw or {}).get("market_snapshot", {}),
                        ["float_market_value", "float_market_cap"],
                    )
                ),
                "raw_cache",
                2,
                "low",
            ),
        ]
    )
    turnover_amount, _ = first_available(
        [
            candidate(as_float(first_present(spot_row, ["成交额"])), "stock_zh_a_spot_em", 0, "high"),
            candidate(
                as_float((cached_raw or {}).get("market_snapshot", {}).get("turnover_amount")),
                "raw_cache",
                2,
                "low",
            ),
        ]
    )

    snapshot.update(
        {
            "close": close,
            "pct_change": pct_change,
            "turnover_rate": turnover_rate,
            "turnover_amount": turnover_amount,
            "total_market_value": market_cap,
            "market_cap": market_cap,
            "float_market_value": float_market_cap,
        }
    )
    provenance["market_snapshot.close"] = close_prov
    provenance["market_snapshot.pct_change"] = pct_change_prov
    provenance["market_snapshot.turnover_rate"] = turnover_rate_prov
    provenance["market_snapshot.market_cap"] = market_cap_prov

    if close is None:
        warnings.append("market_snapshot.close_missing_after_fallback")
    if pct_change is None:
        warnings.append("market_snapshot.pct_change_missing_after_fallback")
    return snapshot, provenance, warnings


def fill_valuation(
    *,
    spot_row: dict[str, Any],
    info_map: dict[str, Any],
    financial_row: dict[str, Any],
    source_context: dict[str, dict[str, Any]],
    cached_raw: dict[str, Any] | None = None,
    as_float,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[str]]:
    valuation: dict[str, Any] = {}
    provenance: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    def candidate(value, source: str | None, fallback_level: int, confidence: str):
        is_cached = source == "raw_cache" or bool(source and source_context.get(source, {}).get("is_cached"))
        return value, build_field_provenance(
            source=source,
            fallback_level=fallback_level,
            is_cached=is_cached,
            confidence=confidence,
        )

    pe, pe_prov = first_available(
        [
            candidate(as_float(first_present(spot_row, ["市盈率-动态", "市盈率", "PE"])), "stock_zh_a_spot_em", 0, "high"),
            candidate(as_float(first_present(info_map, ["市盈率", "PE"])), "stock_individual_info_em", 1, "medium"),
            candidate(as_float((cached_raw or {}).get("valuation_raw", {}).get("pe")), "raw_cache", 2, "low"),
        ]
    )
    pb, pb_prov = first_available(
        [
            candidate(as_float(first_present(spot_row, ["市净率", "PB"])), "stock_zh_a_spot_em", 0, "high"),
            candidate(as_float(first_present(info_map, ["市净率", "PB"])), "stock_individual_info_em", 1, "medium"),
            candidate(as_float((cached_raw or {}).get("valuation_raw", {}).get("pb")), "raw_cache", 2, "low"),
        ]
    )
    ps, _ = first_available(
        [
            candidate(as_float(first_present(spot_row, ["市销率", "PS"])), "stock_zh_a_spot_em", 0, "high"),
            candidate(as_float((cached_raw or {}).get("valuation_raw", {}).get("ps")), "raw_cache", 2, "low"),
        ]
    )
    dividend, _ = first_available(
        [
            candidate(as_float(first_present(info_map, ["股息率", "股息率TTM"])), "stock_individual_info_em", 0, "medium"),
            candidate(as_float(first_present(financial_row, ["股息率(%)"])), "stock_financial_analysis_indicator", 1, "medium"),
            candidate(
                as_float((cached_raw or {}).get("valuation_raw", {}).get("dividend_yield")),
                "raw_cache",
                2,
                "low",
            ),
        ]
    )

    valuation.update({"pe": pe, "pb": pb, "ps": ps, "dividend_yield": dividend})
    provenance["valuation_raw.pe"] = pe_prov
    provenance["valuation_raw.pb"] = pb_prov
    if pe is None:
        warnings.append("valuation_raw.pe_missing_after_fallback")
    if pb is None:
        warnings.append("valuation_raw.pb_missing_after_fallback")
    return valuation, provenance, warnings


def fill_kline_summary(
    *,
    hist_records: list[dict[str, Any]],
    source_context: dict[str, dict[str, Any]],
    cached_raw: dict[str, Any] | None = None,
    as_float,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[str]]:
    summary, warnings = build_kline_summary(hist_records, as_float=as_float)
    provenance: dict[str, dict[str, Any]] = {}
    cached_kline = (cached_raw or {}).get("kline_summary", {})
    is_hist_cached = bool(source_context.get("stock_zh_a_hist", {}).get("is_cached"))

    for key in ("return_5d", "return_20d", "return_60d"):
        value = summary.get(key)
        fallback_level = 0
        source = "stock_zh_a_hist"
        is_cached = is_hist_cached
        confidence = "high"
        if value is None:
            value = cached_kline.get(key)
            fallback_level = 2
            source = "raw_cache" if value is not None else None
            is_cached = value is not None
            confidence = "low" if value is not None else "missing"
            summary[key] = value
        provenance[f"kline_summary.{key}"] = build_field_provenance(
            source=source,
            fallback_level=fallback_level,
            is_cached=is_cached,
            confidence=confidence,
        )
    return summary, provenance, warnings


def fill_financial_metrics(
    *,
    financial_row: dict[str, Any],
    info_map: dict[str, Any],
    source_context: dict[str, dict[str, Any]],
    cached_raw: dict[str, Any] | None = None,
    as_float,
    classify_cashflow,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[str]]:
    financial: dict[str, Any] = {}
    provenance: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    def candidate(value, source: str | None, fallback_level: int, confidence: str):
        is_cached = source == "raw_cache" or bool(source and source_context.get(source, {}).get("is_cached"))
        return value, build_field_provenance(
            source=source,
            fallback_level=fallback_level,
            is_cached=is_cached,
            confidence=confidence,
        )

    aliases = {
        "revenue_growth": ["主营业务收入增长率(%)", "营业收入同比增长率(%)", "营业总收入同比增长率(%)"],
        "net_profit_growth": ["净利润增长率(%)", "净利润同比增长率(%)", "扣非净利润同比增长率(%)"],
        "roe": ["净资产收益率(%)", "净资产收益率-摊薄(%)", "ROE"],
        "gross_margin": ["销售毛利率(%)", "毛利率(%)"],
        "net_margin": ["销售净利率(%)", "净利率(%)"],
        "debt_ratio": ["资产负债率(%)"],
        "operating_cashflow": ["每股经营性现金流(元)", "每股经营现金流(元)"],
    }
    for key, keys in aliases.items():
        value, prov = first_available(
            [
                candidate(as_float(first_present(financial_row, keys)), "stock_financial_analysis_indicator", 0, "high"),
                candidate(as_float(first_present(info_map, keys)), "stock_individual_info_em", 1, "medium"),
                candidate(as_float((cached_raw or {}).get("financial_raw", {}).get(key)), "raw_cache", 2, "low"),
            ]
        )
        financial[key] = value
        if key in {"roe", "net_profit_growth"}:
            provenance[f"financial_raw.{key}"] = prov
    financial["profit_growth"] = financial.get("net_profit_growth")
    financial["operating_cashflow_quality"] = classify_cashflow(financial.get("operating_cashflow"))
    if financial.get("roe") is None:
        warnings.append("financial_raw.roe_missing_after_fallback")
    if financial.get("net_profit_growth") is None:
        warnings.append("financial_raw.net_profit_growth_missing_after_fallback")
    return financial, provenance, warnings


def fill_capital_flow(
    *,
    flow_row: dict[str, Any],
    source_context: dict[str, dict[str, Any]],
    cached_raw: dict[str, Any] | None = None,
    as_float,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    capital_flow = {
        "main_net_inflow": first_available_value(
            [
                as_float(first_present(flow_row, ["主力净流入-净额", "主力净流入净额"])),
                as_float((cached_raw or {}).get("capital_flow_raw", {}).get("main_net_inflow")),
            ]
        ),
        "super_large_net_inflow": first_available_value(
            [
                as_float(first_present(flow_row, ["超大单净流入-净额"])),
                as_float((cached_raw or {}).get("capital_flow_raw", {}).get("super_large_net_inflow")),
            ]
        ),
        "large_net_inflow": first_available_value(
            [
                as_float(first_present(flow_row, ["大单净流入-净额"])),
                as_float((cached_raw or {}).get("capital_flow_raw", {}).get("large_net_inflow")),
            ]
        ),
        "mid_net_inflow": first_available_value(
            [
                as_float(first_present(flow_row, ["中单净流入-净额"])),
                as_float((cached_raw or {}).get("capital_flow_raw", {}).get("mid_net_inflow")),
            ]
        ),
        "small_net_inflow": first_available_value(
            [
                as_float(first_present(flow_row, ["小单净流入-净额"])),
                as_float((cached_raw or {}).get("capital_flow_raw", {}).get("small_net_inflow")),
            ]
        ),
    }
    if capital_flow["main_net_inflow"] is None:
        warnings.append("capital_flow_missing_after_fallback")
    return capital_flow, warnings


def summarize_field_provenance(field_provenance: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {key: field_provenance.get(key, build_field_provenance(source=None, fallback_level=0, is_cached=False, confidence="missing")) for key in KEY_FIELDS}


def first_present(payload: dict[str, Any], keys: list[str], fallback: Any = None) -> Any:
    if not isinstance(payload, dict):
        return fallback
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return value
    return fallback


def first_available(candidates: list[tuple[Any, dict[str, Any]]]) -> tuple[Any, dict[str, Any]]:
    for value, provenance in candidates:
        if value not in (None, "", [], {}):
            return value, provenance
    return None, build_field_provenance(source=None, fallback_level=0, is_cached=False, confidence="missing")


def first_available_value(candidates: list[Any]) -> Any:
    for value in candidates:
        if value not in (None, "", [], {}):
            return value
    return None


def build_kline_summary(records: list[dict[str, Any]], *, as_float) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if not records:
        return {}, ["kline_history_missing"]
    closes = [as_float(first_present(item, ["收盘", "收盘价", "close"])) for item in records]
    closes = [item for item in closes if item is not None]
    if not closes:
        return {}, ["kline_close_missing"]

    ma5 = moving_average(closes, 5)
    ma20 = moving_average(closes, 20)
    ma60 = moving_average(closes, 60)
    latest = closes[-1]
    prev = closes[-2] if len(closes) > 1 else None
    latest_pct = round((latest / prev - 1) * 100, 2) if prev not in (None, 0) else None
    daily_returns = []
    for prev_close, current_close in zip(closes, closes[1:]):
        if prev_close:
            daily_returns.append((current_close / prev_close - 1) * 100)
    volatility = round((sum((item - (sum(daily_returns) / len(daily_returns))) ** 2 for item in daily_returns) / len(daily_returns)) ** 0.5, 2) if len(daily_returns) >= 2 else None

    trend = "sideways"
    if ma20 is not None and latest > ma20:
        trend = "up"
    elif ma20 is not None and latest < ma20:
        trend = "down"

    return (
        {
            "close_series_length": len(closes),
            "latest_close": latest,
            "latest_pct_change": latest_pct,
            "pct_change_5d": window_return(closes, 5),
            "pct_change_20d": window_return(closes, 20),
            "pct_change_60d": window_return(closes, 60),
            "return_5d": window_return(closes, 5),
            "return_20d": window_return(closes, 20),
            "return_60d": window_return(closes, 60),
            "ma5": ma5,
            "ma20": ma20,
            "ma60": ma60,
            "ma5_above_ma20": bool(ma5 is not None and ma20 is not None and ma5 >= ma20),
            "trend": trend,
            "volatility": volatility,
        },
        warnings,
    )


def moving_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return round(sum(values[-window:]) / window, 4)


def window_return(values: list[float], window: int) -> float | None:
    if len(values) > window:
        base = values[-window - 1]
        if base:
            return round((values[-1] / base - 1) * 100, 2)
    if len(values) > 1:
        base = values[0]
        if base:
            return round((values[-1] / base - 1) * 100, 2)
    return None
