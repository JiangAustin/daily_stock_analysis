from __future__ import annotations

import re
import math
from datetime import datetime
from typing import Any, Callable

try:
    import akshare as ak
except ImportError:  # pragma: no cover - exercised through runtime entrypoint
    ak = None

from private_ext.raw_data.base import RawDataCollector
from private_ext.raw_data.akshare_fallbacks import (
    KEY_FIELDS,
    fill_capital_flow,
    fill_financial_metrics,
    fill_kline_summary,
    fill_market_snapshot,
    fill_valuation,
    summarize_field_provenance,
)
from private_ext.raw_data.akshare_kline import fetch_hist_kline_with_fallbacks
from private_ext.raw_data.cache import RawDataCache
from private_ext.raw_data.models import RawStockData
from private_ext.raw_data.quality import CRITICAL_FIELDS, build_quality_report


class AkShareNotInstalledError(RuntimeError):
    """Raised when the optional AkShare dependency is unavailable."""


class AkShareRawDataCollector(RawDataCollector):
    provider = "akshare"

    def __init__(self, cache_dir=None, use_cache: bool = True, refresh: bool = False):
        from private_ext.config import settings

        self.cache = RawDataCache(cache_dir or settings.raw_cache_dir)
        self.use_cache = use_cache
        self.refresh = refresh

    def collect(self, symbol: str, trade_date: str) -> RawStockData:
        if ak is None:
            raise AkShareNotInstalledError(
                "AkShare is not installed. Run: pip install -r requirements-realdata.txt"
            )

        normalized_symbol = _normalize_symbol(symbol)
        cached = self.cache.read(self.provider, normalized_symbol, trade_date) if self.use_cache else None
        if self.use_cache and not self.refresh:
            cached_quality = ((cached.metadata or {}).get("quality_report", {}) if cached else {}) or {}
            if cached is not None and cached_quality.get("quality_level") in {"good", "degraded"}:
                cached = _backfill_cached_quality_metadata(cached)
                cached.metadata = {**(cached.metadata or {}), "loaded_from_cache": True}
                return cached

        market = _infer_market(normalized_symbol)
        warnings: list[str] = []
        payloads: dict[str, Any] = {}
        failed_sources: list[str] = []
        successful_sources: list[str] = []
        source_cache_used: list[str] = []
        source_context: dict[str, dict[str, Any]] = {}
        live_success_count = 0
        cache_success_count = 0
        live_failure_count = 0

        def safe_call(name: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            nonlocal live_success_count, cache_success_count, live_failure_count
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                warnings.append(f"{name}_failed:{type(exc).__name__}")
                payloads[name] = {"error": str(exc)}
                failed_sources.append(name)
                live_failure_count += 1
                cached_source = self.cache.read_source(self.provider, name, normalized_symbol, trade_date) if self.use_cache else None
                if cached_source:
                    warnings.append(f"used_source_cache:{name}")
                    source_cache_used.append(name)
                    source_context[name] = {"is_cached": True, "fallback_level": 1}
                    cache_success_count += 1
                    payloads[name] = cached_source
                    return cached_source
                source_context[name] = {"is_cached": False, "fallback_level": 0}
                return []

            records = _to_records(result)
            if not records:
                warnings.append(f"{name}_empty")
                cached_source = self.cache.read_source(self.provider, name, normalized_symbol, trade_date) if self.use_cache else None
                if cached_source:
                    warnings.append(f"used_source_cache:{name}")
                    source_cache_used.append(name)
                    source_context[name] = {"is_cached": True, "fallback_level": 1}
                    cache_success_count += 1
                    payloads[name] = cached_source
                    return cached_source
                payloads[name] = records
                source_context[name] = {"is_cached": False, "fallback_level": 0}
            else:
                successful_sources.append(name)
                payloads[name] = records
                source_context[name] = {"is_cached": False, "fallback_level": 0}
                live_success_count += 1
                if self.use_cache:
                    self.cache.write_source(self.provider, name, normalized_symbol, trade_date, records)
            return records

        info_records = safe_call("stock_individual_info_em", ak.stock_individual_info_em, symbol=normalized_symbol)
        spot_records = safe_call("stock_zh_a_spot_em", ak.stock_zh_a_spot_em)
        hist_fetch = fetch_hist_kline_with_fallbacks(
            symbol=normalized_symbol,
            requested_date=trade_date,
            safe_call=safe_call,
            ak_client=ak,
        )
        hist_records = hist_fetch["records"]
        warnings.extend(hist_fetch.get("warnings", []))
        failed_sources.extend(hist_fetch.get("failed_sources", []))
        successful_sources.extend(hist_fetch.get("successful_sources", []))
        if hist_fetch.get("raw"):
            payloads["stock_zh_a_hist_candidates"] = hist_fetch["raw"]
        financial_records = safe_call(
            "stock_financial_analysis_indicator",
            ak.stock_financial_analysis_indicator,
            symbol=normalized_symbol,
            start_year=str(max(2000, int(trade_date[:4]) - 2)),
        )
        fund_flow_records = safe_call(
            "stock_individual_fund_flow",
            ak.stock_individual_fund_flow,
            stock=normalized_symbol,
            market=market,
        )
        northbound_records = safe_call("stock_hsgt_individual_em", ak.stock_hsgt_individual_em, symbol=normalized_symbol)
        dragon_tiger_records = safe_call(
            "stock_lhb_stock_statistic_em",
            ak.stock_lhb_stock_statistic_em,
            symbol="近一月",
        )
        news_records = safe_call("stock_news_em", ak.stock_news_em, symbol=normalized_symbol)
        analyst_records = safe_call("stock_research_report_em", ak.stock_research_report_em, symbol=normalized_symbol)

        info_map = _records_to_item_map(info_records)
        spot_row = _find_record_by_symbol(spot_records, normalized_symbol)
        latest_financial = financial_records[-1] if financial_records else {}
        latest_flow = fund_flow_records[-1] if fund_flow_records else {}
        latest_northbound = northbound_records[-1] if northbound_records else {}
        latest_dragon = _find_record_by_symbol(dragon_tiger_records, normalized_symbol)

        cached_raw_dump = cached.model_dump(mode="json") if cached is not None else None
        kline_summary, kline_provenance, kline_warnings = fill_kline_summary(
            hist_records=hist_records,
            source_context=source_context,
            cached_raw=cached_raw_dump,
            as_float=_as_float,
        )
        warnings.extend(kline_warnings)

        basic_info = {
            "name": _first_present(
                spot_row,
                ["名称", "股票简称"],
                fallback=_first_present(info_map, ["股票简称", "股票名称"], fallback=normalized_symbol),
            ),
            "industry": _first_present(info_map, ["行业", "所属行业"], fallback="A股"),
            "market": "cn",
            "listed_date": _normalize_date(_first_present(info_map, ["上市时间", "上市日期"])),
        }

        market_snapshot, market_provenance, market_warnings = fill_market_snapshot(
            spot_row=spot_row,
            info_map=info_map,
            hist_summary=kline_summary,
            source_context=source_context,
            cached_raw=cached_raw_dump,
            as_float=_as_float,
        )
        valuation_raw, valuation_provenance, valuation_warnings = fill_valuation(
            spot_row=spot_row,
            info_map=info_map,
            financial_row=latest_financial,
            source_context=source_context,
            cached_raw=cached_raw_dump,
            as_float=_as_float,
        )
        financial_raw, financial_provenance, financial_warnings = fill_financial_metrics(
            financial_row=latest_financial,
            info_map=info_map,
            source_context=source_context,
            cached_raw=cached_raw_dump,
            as_float=_as_float,
            classify_cashflow=_classify_cashflow,
        )
        capital_flow_raw, flow_warnings = fill_capital_flow(
            flow_row=latest_flow,
            source_context=source_context,
            cached_raw=cached_raw_dump,
            as_float=_as_float,
        )
        warnings.extend(market_warnings)
        warnings.extend(valuation_warnings)
        warnings.extend(financial_warnings)
        warnings.extend(flow_warnings)

        northbound_raw = {
            "net_inflow": _as_float(
                _first_present(latest_northbound, ["持股市值", "当日增持估计-市值", "当日持股市值"])
            ),
            "holding_shares": _as_float(_first_present(latest_northbound, ["持股数量", "持股数"])),
            "trade_date": _normalize_date(_first_present(latest_northbound, ["持股日期", "日期"])),
        }

        dragon_tiger_raw = {
            "listed": bool(latest_dragon),
            "reason": _first_present(latest_dragon, ["解读", "上榜原因", "最近上榜日"], fallback=""),
            "raw": latest_dragon or {},
        }

        announcements_raw: list[dict[str, Any]] = []
        news_raw = [
            {
                "title": _first_present(item, ["新闻标题", "标题"], fallback=""),
                "date": _normalize_date(_first_present(item, ["发布时间", "日期"])),
                "source": _first_present(item, ["文章来源", "来源"], fallback=""),
                "sentiment": "neutral",
            }
            for item in news_records[:10]
            if _first_present(item, ["新闻标题", "标题"])
        ]
        analyst_raw = [
            {
                "rating": _first_present(item, ["评级", "最新评级"], fallback=""),
                "target_price": _as_float(_first_present(item, ["目标价", "目标价(元)"])),
                "date": _normalize_date(_first_present(item, ["报告日期", "日期"])),
                "title": _first_present(item, ["报告名称", "标题"], fallback=""),
            }
            for item in analyst_records[:10]
            if _first_present(item, ["评级", "最新评级", "目标价", "目标价(元)"])
        ]
        industry_raw = {
            "industry": basic_info["industry"],
            "concepts": _split_text(_first_present(info_map, ["概念板块", "所属概念"])),
            "region": _first_present(info_map, ["地域", "地区"], fallback=""),
        }
        field_provenance = {
            **market_provenance,
            **valuation_provenance,
            **financial_provenance,
            **kline_provenance,
        }
        field_provenance = summarize_field_provenance(field_provenance)

        actual_data_date = _first_non_empty(
            [
                _normalize_date(kline_summary.get("actual_data_date")),
                _normalize_date(_first_present(hist_records[-1], ["日期"])) if hist_records else None,
                northbound_raw.get("trade_date"),
                _normalize_date(_first_present(latest_financial, ["日期"])),
                _normalize_date(_first_present(analyst_raw[0], ["date"])) if analyst_raw else None,
            ]
        )
        quality_report = build_quality_report(
            symbol=normalized_symbol,
            requested_date=trade_date,
            provider=self.provider,
            actual_data_date=actual_data_date,
            field_values={
                "market_snapshot.close": market_snapshot.get("close"),
                "market_snapshot.pct_change": market_snapshot.get("pct_change"),
                "valuation_raw.pe": valuation_raw.get("pe"),
                "valuation_raw.pb": valuation_raw.get("pb"),
                "financial_raw.roe": financial_raw.get("roe"),
                "financial_raw.net_profit_growth": financial_raw.get("net_profit_growth"),
                "kline_summary.return_20d": kline_summary.get("return_20d"),
                "basic_info.name": basic_info.get("name"),
                "basic_info.industry": basic_info.get("industry"),
                "market_snapshot.turnover_rate": market_snapshot.get("turnover_rate"),
                "market_snapshot.market_cap": market_snapshot.get("market_cap"),
            },
            warnings=warnings,
            failed_sources=failed_sources,
            successful_sources=successful_sources,
            field_provenance=field_provenance,
            source_cache_used=source_cache_used,
            live_success_count=live_success_count,
            cache_success_count=cache_success_count,
            live_failure_count=live_failure_count,
        )
        warnings.extend(f"missing:{field}" for field in quality_report.missing_fields)

        if not _has_any_value(
            basic_info,
            market_snapshot,
            valuation_raw,
            financial_raw,
            capital_flow_raw,
            news_raw,
            analyst_raw,
        ):
            if cached is not None:
                return _mark_cache_fallback(cached)
            raise RuntimeError(f"AkShare collector could not fetch any usable data for {normalized_symbol}")

        raw = RawStockData(
            symbol=normalized_symbol,
            trade_date=trade_date,
            basic_info=basic_info,
            market_snapshot=market_snapshot,
            kline_summary=kline_summary,
            valuation_raw=valuation_raw,
            financial_raw=financial_raw,
            capital_flow_raw=capital_flow_raw,
            northbound_raw=northbound_raw,
            dragon_tiger_raw=dragon_tiger_raw,
            announcements_raw=announcements_raw,
            news_raw=news_raw,
            analyst_raw=analyst_raw,
            industry_raw=industry_raw,
            metadata={
                "provider": self.provider,
                "original_symbol": symbol,
                "normalized_symbol": normalized_symbol,
                "requested_date": trade_date,
                "actual_data_date": actual_data_date,
                "data_quality_warnings": sorted(set(warnings)),
                "missing_fields": quality_report.missing_fields,
                "quality_report": quality_report.model_dump(mode="json"),
                "failed_sources": sorted(set(failed_sources)),
                "successful_sources": sorted(set(successful_sources)),
                "field_provenance": field_provenance,
                "source_cache_used": sorted(set(source_cache_used)),
                "source_payloads": payloads,
            },
        )
        if cached is not None and (
            (failed_sources and quality_report.quality_level in {"poor", "failed"})
            or (not successful_sources and quality_report.quality_level in {"poor", "failed"})
            or (not successful_sources and not source_cache_used)
            or not quality_report.can_make_decision
        ):
            return _mark_cache_fallback(cached)
        if self.use_cache:
            self.cache.write(self.provider, normalized_symbol, trade_date, raw)
        return raw


def _normalize_symbol(symbol: str) -> str:
    text = (symbol or "").strip().upper()
    text = text.replace(".", "")
    text = re.sub(r"^(SH|SZ|BJ)", "", text)
    text = re.sub(r"(SH|SZ|BJ)$", "", text)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 6:
        return digits[-6:]
    raise ValueError(f"Unsupported A-share symbol: {symbol}")


def _infer_market(symbol: str) -> str:
    if symbol.startswith(("5", "6", "9")):
        return "sh"
    return "sz"


def _to_records(frame: Any) -> list[dict[str, Any]]:
    if frame is None:
        return []
    empty = getattr(frame, "empty", None)
    if empty is True:
        return []
    try:
        records = frame.to_dict(orient="records")
    except Exception:
        return []
    return [dict(item) for item in records]


def _records_to_item_map(records: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in records:
        key = item.get("item") or item.get("项目") or item.get("指标")
        value = item.get("value") if "value" in item else item.get("值")
        if key:
            result[str(key)] = value
    return result


def _find_record_by_symbol(records: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
    for item in records:
        code = _normalize_code_like(
            _first_present(item, ["代码", "股票代码", "证券代码", "code"], fallback="")
        )
        if code == symbol:
            return item
    return {}


def _normalize_code_like(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[-6:] if len(digits) >= 6 else digits


def _build_kline_summary(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if not records:
        return {}, ["kline_history_missing"]

    closes = [_as_float(_first_present(item, ["收盘", "收盘价", "close"])) for item in records]
    closes = [item for item in closes if item is not None]
    if not closes:
        return {}, ["kline_close_missing"]

    ma5 = _moving_average(closes, 5)
    ma20 = _moving_average(closes, 20)
    ma60 = _moving_average(closes, 60)
    latest = closes[-1]
    daily_returns = []
    for prev, current in zip(closes, closes[1:]):
        if prev:
            daily_returns.append((current / prev - 1) * 100)
    volatility = round(statistics.pstdev(daily_returns), 2) if len(daily_returns) >= 2 else None

    trend = "sideways"
    if ma20 is not None and latest > ma20:
        trend = "up"
    elif ma20 is not None and latest < ma20:
        trend = "down"

    return (
        {
            "close_series_length": len(closes),
            "pct_change_5d": _window_return(closes, 5),
            "pct_change_20d": _window_return(closes, 20),
            "pct_change_60d": _window_return(closes, 60),
            "return_20d": _window_return(closes, 20),
            "ma5": ma5,
            "ma20": ma20,
            "ma60": ma60,
            "ma5_above_ma20": bool(ma5 is not None and ma20 is not None and ma5 >= ma20),
            "trend": trend,
            "volatility": volatility,
        },
        warnings,
    )


def _moving_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return round(sum(values[-window:]) / window, 4)


def _window_return(values: list[float], window: int) -> float | None:
    if len(values) <= window:
        return None
    base = values[-window - 1]
    if not base:
        return None
    return round((values[-1] / base - 1) * 100, 2)


def _first_present(payload: dict[str, Any], keys: list[str], fallback: Any = None) -> Any:
    for key in keys:
        value = payload.get(key) if isinstance(payload, dict) else None
        if value not in (None, "", [], {}):
            return value
    return fallback


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
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _classify_cashflow(value: float | None) -> str | None:
    if value is None:
        return None
    if value > 1:
        return "strong"
    if value > 0:
        return "improving"
    return "weak"


def _split_text(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    for splitter in (";", "；", ",", "，", "|", "/"):
        text = text.replace(splitter, " ")
    return [item for item in text.split() if item]


def _missing_field_names(payload: dict[str, Any]) -> list[str]:
    return [key for key, value in payload.items() if value in (None, "", [], {})]


def _has_any_value(*payloads: Any) -> bool:
    for payload in payloads:
        if isinstance(payload, dict):
            if any(value not in (None, "", [], {}) for value in payload.values()):
                return True
        elif isinstance(payload, list) and payload:
            return True
    return False


def _first_non_empty(values: list[Any]) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _mark_cache_fallback(cached: RawStockData) -> RawStockData:
    cached_copy = _backfill_cached_quality_metadata(cached.model_copy(deep=True))
    metadata = cached_copy.metadata or {}
    warnings = list(metadata.get("data_quality_warnings", []))
    warnings.append("used_stale_cache_due_to_live_failure")
    metadata["data_quality_warnings"] = sorted(set(warnings))
    quality_report = metadata.get("quality_report")
    if isinstance(quality_report, dict):
        quality_warnings = list(quality_report.get("warnings", []))
        quality_warnings.append("used_stale_cache_due_to_live_failure")
        quality_report["warnings"] = sorted(set(quality_warnings))
        quality_report["notes"] = [
            *quality_report.get("notes", []),
            "Loaded cached raw data after live collection failure.",
        ]
        metadata["quality_report"] = quality_report
    metadata["loaded_from_cache"] = True
    cached_copy.metadata = metadata
    return cached_copy


def _backfill_cached_quality_metadata(raw: RawStockData) -> RawStockData:
    metadata = raw.metadata or {}
    quality_report = metadata.get("quality_report")
    quality = dict(quality_report) if isinstance(quality_report, dict) else {}

    field_provenance = metadata.get("field_provenance")
    if not isinstance(field_provenance, dict) or not field_provenance:
        field_provenance = quality.get("field_provenance_summary")
    if not isinstance(field_provenance, dict) or not field_provenance:
        field_provenance = _synthesize_cache_provenance(raw)

    critical_field_status = quality.get("critical_field_status")
    if not isinstance(critical_field_status, dict) or not critical_field_status:
        field_values = _critical_field_values(raw)
        critical_field_status = {
            field: field_values.get(field) not in (None, "", [], {})
            for field in CRITICAL_FIELDS
        }

    quality["field_provenance_summary"] = field_provenance
    quality["source_cache_used"] = metadata.get("source_cache_used", quality.get("source_cache_used", []))
    quality["live_success_count"] = metadata.get("live_success_count", quality.get("live_success_count", 0))
    quality["cache_success_count"] = metadata.get("cache_success_count", quality.get("cache_success_count", 0))
    quality["live_failure_count"] = metadata.get("live_failure_count", quality.get("live_failure_count", 0))
    quality["critical_field_status"] = critical_field_status
    metadata["field_provenance"] = field_provenance
    metadata["source_cache_used"] = quality["source_cache_used"]
    metadata["live_success_count"] = quality["live_success_count"]
    metadata["cache_success_count"] = quality["cache_success_count"]
    metadata["live_failure_count"] = quality["live_failure_count"]
    metadata["quality_report"] = quality
    raw.metadata = metadata
    return raw


def _critical_field_values(raw: RawStockData) -> dict[str, Any]:
    return {
        "market_snapshot.close": (raw.market_snapshot or {}).get("close"),
        "market_snapshot.pct_change": (raw.market_snapshot or {}).get("pct_change"),
        "valuation_raw.pe": (raw.valuation_raw or {}).get("pe"),
        "valuation_raw.pb": (raw.valuation_raw or {}).get("pb"),
        "financial_raw.roe": (raw.financial_raw or {}).get("roe"),
        "financial_raw.net_profit_growth": (raw.financial_raw or {}).get("net_profit_growth"),
        "kline_summary.return_20d": (raw.kline_summary or {}).get("return_20d"),
    }


def _synthesize_cache_provenance(raw: RawStockData) -> dict[str, dict[str, Any]]:
    field_values = {
        "market_snapshot.close": (raw.market_snapshot or {}).get("close"),
        "market_snapshot.pct_change": (raw.market_snapshot or {}).get("pct_change"),
        "market_snapshot.turnover_rate": (raw.market_snapshot or {}).get("turnover_rate"),
        "market_snapshot.market_cap": (raw.market_snapshot or {}).get("market_cap")
        or (raw.market_snapshot or {}).get("total_market_value"),
        "valuation_raw.pe": (raw.valuation_raw or {}).get("pe"),
        "valuation_raw.pb": (raw.valuation_raw or {}).get("pb"),
        "financial_raw.roe": (raw.financial_raw or {}).get("roe"),
        "financial_raw.net_profit_growth": (raw.financial_raw or {}).get("net_profit_growth"),
        "kline_summary.return_5d": (raw.kline_summary or {}).get("return_5d"),
        "kline_summary.return_20d": (raw.kline_summary or {}).get("return_20d"),
        "kline_summary.return_60d": (raw.kline_summary or {}).get("return_60d"),
    }
    provenance: dict[str, dict[str, Any]] = {}
    for field in KEY_FIELDS:
        value = field_values.get(field)
        provenance[field] = {
            "source": "raw_cache" if value not in (None, "", [], {}) else None,
            "fallback_level": 2 if value not in (None, "", [], {}) else 0,
            "is_cached": value not in (None, "", [], {}),
            "confidence": "low" if value not in (None, "", [], {}) else "missing",
        }
    return provenance
