from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable

from private_ext.raw_data.akshare_fallbacks import build_field_provenance, summarize_field_provenance
from private_ext.raw_data.akshare_kline import normalize_a_share_symbol
from private_ext.raw_data.base import RawDataCollector
from private_ext.raw_data.cache import RawDataCache
from private_ext.raw_data.eastmoney_diagnostics import (
    EastMoneyCandidateResult,
    EastMoneyDiagnosticsReport,
    EastMoneyEndpointResult,
)
from private_ext.raw_data.eastmoney_endpoints import EndpointCandidate, build_default_endpoint_candidates
from private_ext.raw_data.models import RawStockData
from private_ext.raw_data.quality import build_quality_report


class EastMoneyRawDataCollector(RawDataCollector):
    provider = "eastmoney"

    def __init__(
        self,
        cache_dir=None,
        use_cache: bool = True,
        refresh: bool = False,
        fetchers: dict[str, Callable[..., list[dict[str, Any]]]] | None = None,
    ):
        from private_ext.config import settings

        self.cache = RawDataCache(cache_dir or settings.raw_cache_dir)
        self.use_cache = use_cache
        self.refresh = refresh
        self.endpoint_groups = build_default_endpoint_candidates(fetchers)

    def collect(self, symbol: str, trade_date: str) -> RawStockData:
        normalized_symbol = normalize_a_share_symbol(symbol)
        context = self._run_groups(normalized_symbol, trade_date)
        warnings = context["warnings"]
        failed_sources = context["failed_sources"]
        successful_sources = context["successful_sources"]
        source_cache_used = context["source_cache_used"]
        group_cache_hit = context["group_cache_hit"]
        source_payloads = context["source_payloads"]
        field_provenance: dict[str, dict[str, Any]] = {}
        live_success_count = context["live_success_count"]
        cache_success_count = context["cache_success_count"]
        live_failure_count = context["live_failure_count"]
        diagnostics: EastMoneyDiagnosticsReport = context["diagnostics"]

        snapshot_fields = context["group_fields"].get("snapshot", {})
        valuation_fields = context["group_fields"].get("valuation", {})
        kline_fields = context["group_fields"].get("kline", {})
        financial_fields = context["group_fields"].get("financial", {})

        close, close_source, close_fallback_level = first_non_missing_with_source(
            ("eastmoney_snapshot", snapshot_fields.get("close"), 0),
            ("eastmoney_kline", kline_fields.get("close"), 1),
        )
        pct_change, pct_change_source, pct_change_fallback_level = first_non_missing_with_source(
            ("eastmoney_snapshot", snapshot_fields.get("pct_change"), 0),
            ("eastmoney_kline", kline_fields.get("pct_change"), 1),
        )
        turnover_rate, turnover_rate_source, turnover_rate_fallback_level = first_non_missing_with_source(
            ("eastmoney_snapshot", snapshot_fields.get("turnover_rate"), 0),
        )
        market_cap, market_cap_source, market_cap_fallback_level = first_non_missing_with_source(
            ("eastmoney_snapshot", snapshot_fields.get("market_cap"), 0),
        )
        pe, pe_source, pe_fallback_level = first_non_missing_with_source(
            ("eastmoney_snapshot", snapshot_fields.get("pe"), 0),
            ("eastmoney_valuation", valuation_fields.get("pe"), 0),
        )
        pb, pb_source, pb_fallback_level = first_non_missing_with_source(
            ("eastmoney_snapshot", snapshot_fields.get("pb"), 0),
            ("eastmoney_valuation", valuation_fields.get("pb"), 0),
        )
        roe, roe_source, roe_fallback_level = first_non_missing_with_source(
            ("eastmoney_financial", financial_fields.get("roe"), 0),
        )
        net_profit_growth, net_profit_growth_source, net_profit_growth_fallback_level = first_non_missing_with_source(
            ("eastmoney_financial", financial_fields.get("net_profit_growth"), 0),
        )
        return_5d, return_5d_source, return_5d_fallback_level = first_non_missing_with_source(
            ("eastmoney_kline", kline_fields.get("return_5d"), 0),
        )
        return_20d, return_20d_source, return_20d_fallback_level = first_non_missing_with_source(
            ("eastmoney_kline", kline_fields.get("return_20d"), 0),
        )
        return_60d, return_60d_source, return_60d_fallback_level = first_non_missing_with_source(
            ("eastmoney_kline", kline_fields.get("return_60d"), 0),
        )

        market_snapshot = {
            "close": first_non_missing(snapshot_fields.get("close"), kline_fields.get("close")),
            "pct_change": first_non_missing(snapshot_fields.get("pct_change"), kline_fields.get("pct_change")),
            "turnover_rate": first_non_missing(snapshot_fields.get("turnover_rate")),
            "market_cap": first_non_missing(snapshot_fields.get("market_cap")),
            "currency": "CNY",
        }
        valuation_raw = {
            "pe": first_non_missing(snapshot_fields.get("pe"), valuation_fields.get("pe")),
            "pb": first_non_missing(snapshot_fields.get("pb"), valuation_fields.get("pb")),
        }
        financial_raw = {
            "roe": first_non_missing(financial_fields.get("roe")),
            "net_profit_growth": first_non_missing(financial_fields.get("net_profit_growth")),
        }
        kline_summary = {
            "return_5d": first_non_missing(kline_fields.get("return_5d")),
            "return_20d": first_non_missing(kline_fields.get("return_20d")),
            "return_60d": first_non_missing(kline_fields.get("return_60d")),
            "pct_change_5d": first_non_missing(kline_fields.get("return_5d")),
            "pct_change_20d": first_non_missing(kline_fields.get("return_20d")),
            "pct_change_60d": first_non_missing(kline_fields.get("return_60d")),
            "latest_close": first_non_missing(kline_fields.get("close")),
            "latest_pct_change": first_non_missing(kline_fields.get("pct_change")),
            "actual_data_date": kline_fields.get("actual_data_date"),
            "close_series_length": len(context["kline_rows"]),
            "return_available_window": kline_fields.get("return_available_window", 0),
        }
        basic_info = {
            "name": context["basic_info"].get("name", normalized_symbol),
            "industry": context["basic_info"].get("industry", "A股"),
            "market": "cn",
        }
        actual_data_date = kline_summary.get("actual_data_date") or context["basic_info"].get("report_date")

        field_provenance["market_snapshot.close"] = build_field_provenance(
            source=close_source,
            fallback_level=close_fallback_level,
            is_cached=bool(close_source and group_cache_hit.get(_group_name_for_source(close_source), False)),
            confidence="high" if close is not None else "missing",
        )
        field_provenance["market_snapshot.pct_change"] = build_field_provenance(
            source=pct_change_source,
            fallback_level=pct_change_fallback_level,
            is_cached=bool(pct_change_source and group_cache_hit.get(_group_name_for_source(pct_change_source), False)),
            confidence="high" if pct_change is not None else "missing",
        )
        field_provenance["market_snapshot.turnover_rate"] = build_field_provenance(
            source=turnover_rate_source,
            fallback_level=turnover_rate_fallback_level,
            is_cached=bool(turnover_rate_source and group_cache_hit.get(_group_name_for_source(turnover_rate_source), False)),
            confidence="high" if turnover_rate is not None else "missing",
        )
        field_provenance["market_snapshot.market_cap"] = build_field_provenance(
            source=market_cap_source,
            fallback_level=market_cap_fallback_level,
            is_cached=bool(market_cap_source and group_cache_hit.get(_group_name_for_source(market_cap_source), False)),
            confidence="high" if market_cap is not None else "missing",
        )
        field_provenance["valuation_raw.pe"] = build_field_provenance(
            source=pe_source,
            fallback_level=pe_fallback_level,
            is_cached=bool(pe_source and group_cache_hit.get(_group_name_for_source(pe_source), False)),
            confidence="high" if pe is not None else "missing",
        )
        field_provenance["valuation_raw.pb"] = build_field_provenance(
            source=pb_source,
            fallback_level=pb_fallback_level,
            is_cached=bool(pb_source and group_cache_hit.get(_group_name_for_source(pb_source), False)),
            confidence="high" if pb is not None else "missing",
        )
        field_provenance["financial_raw.roe"] = build_field_provenance(
            source=roe_source,
            fallback_level=roe_fallback_level,
            is_cached=bool(roe_source and group_cache_hit.get(_group_name_for_source(roe_source), False)),
            confidence="high" if roe is not None else "missing",
        )
        field_provenance["financial_raw.net_profit_growth"] = build_field_provenance(
            source=net_profit_growth_source,
            fallback_level=net_profit_growth_fallback_level,
            is_cached=bool(net_profit_growth_source and group_cache_hit.get(_group_name_for_source(net_profit_growth_source), False)),
            confidence="high" if net_profit_growth is not None else "missing",
        )
        kline_source_map = {
            "return_5d": (return_5d_source, return_5d_fallback_level, return_5d),
            "return_20d": (return_20d_source, return_20d_fallback_level, return_20d),
            "return_60d": (return_60d_source, return_60d_fallback_level, return_60d),
        }
        for key, (source, fallback_level, value) in kline_source_map.items():
            field_provenance[f"kline_summary.{key}"] = build_field_provenance(
                source=source,
                fallback_level=fallback_level,
                is_cached=bool(source and group_cache_hit.get(_group_name_for_source(source), False)),
                confidence="high" if value is not None else "missing",
            )
        field_provenance = summarize_field_provenance(field_provenance)
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
        quality_payload = quality_report.model_dump(mode="json")
        quality_payload["diagnostics"] = diagnostics.to_metadata()
        warnings.extend(f"missing:{field}" for field in quality_report.missing_fields)

        raw = RawStockData(
            symbol=normalized_symbol,
            trade_date=trade_date,
            basic_info=basic_info,
            market_snapshot=market_snapshot,
            kline_summary=kline_summary,
            valuation_raw=valuation_raw,
            financial_raw=financial_raw,
            capital_flow_raw={},
            northbound_raw={},
            dragon_tiger_raw={},
            announcements_raw=[],
            news_raw=[],
            analyst_raw=[],
            industry_raw={"industry": basic_info["industry"]},
            metadata={
                "provider": self.provider,
                "providers_used": [self.provider],
                "requested_date": trade_date,
                "actual_data_date": actual_data_date,
                "field_provenance": field_provenance,
            "quality_report": quality_payload,
            "data_quality_warnings": sorted(set(warnings)),
            "missing_fields": quality_report.missing_fields,
            "failed_sources": sorted(set(failed_sources)),
            "successful_sources": sorted(set(successful_sources)),
            "source_cache_used": sorted(set(source_cache_used)),
            "source_payloads": source_payloads,
            "eastmoney_diagnostics": diagnostics.to_metadata(),
        },
    )
        if self.use_cache:
            self.cache.write(self.provider, normalized_symbol, trade_date, raw)
        return raw

    def probe_endpoints(
        self,
        symbol: str,
        trade_date: str,
        group: str | None = None,
        refresh: bool | None = None,
    ) -> dict[str, Any]:
        normalized_symbol = normalize_a_share_symbol(symbol)
        return self._run_groups(normalized_symbol, trade_date, group_filter=group, refresh=refresh)["diagnostics"].to_metadata()

    def _run_groups(
        self,
        normalized_symbol: str,
        trade_date: str,
        *,
        group_filter: str | None = None,
        refresh: bool | None = None,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        failed_sources: list[str] = []
        successful_sources: list[str] = []
        source_cache_used: list[str] = []
        group_cache_hit: dict[str, bool] = {}
        source_payloads: dict[str, Any] = {}
        candidate_results: list[EastMoneyCandidateResult] = []
        endpoint_results: list[EastMoneyEndpointResult] = []
        live_success_count = 0
        cache_success_count = 0
        live_failure_count = 0
        group_fields: dict[str, dict[str, Any]] = {}
        best_candidate_by_group: dict[str, str] = {}
        fields_filled_by_candidate: dict[str, list[str]] = {}
        basic_info: dict[str, Any] = {}
        kline_rows: list[dict[str, Any]] = []

        effective_refresh = self.refresh if refresh is None else refresh
        selected_groups = (
            {group_filter: self.endpoint_groups[group_filter]}
            if group_filter
            else self.endpoint_groups
        )

        for group_name, candidates in selected_groups.items():
            group_status = "failed"
            group_found: list[str] = []
            group_missing: list[str] = []
            had_hard_failure = False
            for candidate in sorted(candidates, key=lambda item: item.priority):
                start = time.perf_counter()
                payload = None
                last_exc: Exception | None = None
                for _attempt in range(2):
                    try:
                        args = (normalized_symbol, trade_date) if group_name == "kline" else (normalized_symbol,)
                        payload = candidate.fetcher(*args)
                        last_exc = None
                        break
                    except Exception as exc:
                        if not _should_retry_exception(exc):
                            last_exc = exc
                            break
                        last_exc = exc
                elapsed_ms = int((time.perf_counter() - start) * 1000)

                if last_exc is not None:
                    live_failure_count += 1
                    had_hard_failure = True
                    cached_payload = (
                        self.cache.read_source(self.provider, candidate.name, normalized_symbol, trade_date)
                        if self.use_cache and not effective_refresh
                        else None
                    )
                    if cached_payload:
                        parsed = candidate.parser(cached_payload)
                        source_cache_used.append(candidate.name)
                        cache_success_count += 1
                        group_cache_hit[group_name] = True
                        group_fields[group_name] = parsed["fields"]
                        if group_name == "kline":
                            kline_rows = parsed.get("rows", [])
                        if group_name == "snapshot":
                            basic_info["name"] = _first_present(_first_row(cached_payload), ["f58", "name"], fallback=normalized_symbol)
                        candidate_results.append(
                            EastMoneyCandidateResult(
                                candidate_name=candidate.name,
                                endpoint_group=group_name,
                                status="cache",
                                url_summary=candidate.name,
                                error_type=type(last_exc).__name__,
                                error_message=str(last_exc),
                                elapsed_ms=elapsed_ms,
                                target_fields=candidate.target_fields,
                                fields_found=parsed["fields_found"],
                                fields_missing=parsed["fields_missing"],
                                used_cache=True,
                                parser_name=candidate.parser.__name__,
                                raw_shape=parsed.get("raw_shape"),
                            )
                        )
                        successful_sources.append(group_name)
                        best_candidate_by_group[group_name] = candidate.name
                        fields_filled_by_candidate[candidate.name] = parsed["fields_found"]
                        group_status = "cache"
                        group_found = parsed["fields_found"]
                        group_missing = parsed["fields_missing"]
                        source_payloads[candidate.name] = cached_payload
                        break
                    failed_sources.append(group_name)
                    warnings.append(f"{group_name}_failed:{type(last_exc).__name__}")
                    candidate_results.append(
                        EastMoneyCandidateResult(
                            candidate_name=candidate.name,
                            endpoint_group=group_name,
                            status="failed",
                            url_summary=candidate.name,
                            error_type=type(last_exc).__name__,
                            error_message=str(last_exc),
                            elapsed_ms=elapsed_ms,
                            target_fields=candidate.target_fields,
                            fields_found=[],
                            fields_missing=candidate.target_fields,
                            used_cache=False,
                            parser_name=candidate.parser.__name__,
                        )
                    )
                    continue

                parsed = candidate.parser(payload)
                source_payloads[candidate.name] = payload
                if parsed["fields_found"]:
                    live_success_count += 1
                    successful_sources.append(group_name)
                    group_cache_hit[group_name] = False
                    group_fields[group_name] = parsed["fields"]
                    if group_name == "kline":
                        kline_rows = parsed.get("rows", [])
                        if parsed["fields"].get("return_20d") is None and parsed["fields"].get("return_available_window", 0) >= 2:
                            warnings.append("eastmoney_insufficient_kline_window_for_return_20d")
                    if group_name == "snapshot":
                        row = _first_row(payload)
                        basic_info["name"] = _first_present(row, ["f58", "name"], fallback=normalized_symbol)
                    if group_name == "financial":
                        row = _first_row(payload)
                        basic_info["industry"] = _first_present(row, ["industry"], fallback="A股")
                        basic_info["report_date"] = _normalize_date(_first_present(row, ["report_date"]))
                    if self.use_cache:
                        self.cache.write_source(self.provider, candidate.name, normalized_symbol, trade_date, payload)
                    candidate_results.append(
                        EastMoneyCandidateResult(
                            candidate_name=candidate.name,
                            endpoint_group=group_name,
                            status="success",
                            url_summary=candidate.name,
                            elapsed_ms=elapsed_ms,
                            target_fields=candidate.target_fields,
                            fields_found=parsed["fields_found"],
                            fields_missing=parsed["fields_missing"],
                            used_cache=False,
                            parser_name=candidate.parser.__name__,
                            raw_shape=parsed.get("raw_shape"),
                            notes=parsed.get("warnings", []),
                        )
                    )
                    best_candidate_by_group[group_name] = candidate.name
                    fields_filled_by_candidate[candidate.name] = parsed["fields_found"]
                    group_status = "success"
                    group_found = parsed["fields_found"]
                    group_missing = parsed["fields_missing"]
                    break

                candidate_results.append(
                    EastMoneyCandidateResult(
                        candidate_name=candidate.name,
                        endpoint_group=group_name,
                        status="parsed_empty",
                        url_summary=candidate.name,
                        elapsed_ms=elapsed_ms,
                        target_fields=candidate.target_fields,
                        fields_found=[],
                        fields_missing=candidate.target_fields,
                        used_cache=False,
                        parser_name=candidate.parser.__name__,
                        raw_shape=parsed.get("raw_shape"),
                    )
                )
                group_status = "skipped"
                group_missing = candidate.target_fields
            endpoint_results.append(
                EastMoneyEndpointResult(
                    endpoint_name=group_name,
                    purpose=f"{group_name} group",
                    status=group_status if group_status != "failed" or had_hard_failure else "skipped",
                    elapsed_ms=sum(item.elapsed_ms for item in candidate_results if item.endpoint_group == group_name),
                    target_fields=candidates[0].target_fields,
                    fields_found=group_found,
                    fields_missing=group_missing or candidates[0].target_fields,
                    used_cache=group_status == "cache",
                    notes=[f"best_candidate:{best_candidate_by_group.get(group_name, '-')}"],
                )
            )

        field_values = {
            "market_snapshot.close": group_fields.get("snapshot", {}).get("close") or group_fields.get("kline", {}).get("close"),
            "market_snapshot.pct_change": group_fields.get("snapshot", {}).get("pct_change") or group_fields.get("kline", {}).get("pct_change"),
            "valuation_raw.pe": group_fields.get("snapshot", {}).get("pe") or group_fields.get("valuation", {}).get("pe"),
            "valuation_raw.pb": group_fields.get("snapshot", {}).get("pb") or group_fields.get("valuation", {}).get("pb"),
            "financial_raw.roe": group_fields.get("financial", {}).get("roe"),
            "financial_raw.net_profit_growth": group_fields.get("financial", {}).get("net_profit_growth"),
            "kline_summary.return_20d": group_fields.get("kline", {}).get("return_20d"),
            "kline_summary.return_5d": group_fields.get("kline", {}).get("return_5d"),
            "kline_summary.return_60d": group_fields.get("kline", {}).get("return_60d"),
        }
        diagnostics = EastMoneyDiagnosticsReport(
            symbol=normalized_symbol,
            requested_date=trade_date,
            endpoint_results=endpoint_results,
            candidate_results=candidate_results,
            successful_endpoints=[item.endpoint_name for item in endpoint_results if item.status in {"success", "cache"}],
            failed_endpoints=[item.endpoint_name for item in endpoint_results if item.status == "failed"],
            group_status={item.endpoint_name: item.status for item in endpoint_results},
            best_candidate_by_group=best_candidate_by_group,
            fields_filled_by_endpoint={item.endpoint_name: item.fields_found for item in endpoint_results if item.fields_found},
            fields_filled_by_candidate=fields_filled_by_candidate,
            unresolved_fields=[field for field, value in field_values.items() if value in (None, "", [], {})],
            remote_errors=[f"{item.candidate_name}:{item.error_type}" for item in candidate_results if item.error_type],
            parse_errors=[item.candidate_name for item in candidate_results if item.status == "parsed_empty"],
            cache_used=sorted(set(source_cache_used)),
            notes=[],
        )
        return {
            "warnings": warnings,
            "failed_sources": sorted(set(failed_sources)),
            "successful_sources": sorted(set(successful_sources)),
            "source_cache_used": sorted(set(source_cache_used)),
            "group_cache_hit": group_cache_hit,
            "source_payloads": source_payloads,
            "live_success_count": live_success_count,
            "cache_success_count": cache_success_count,
            "live_failure_count": live_failure_count,
            "diagnostics": diagnostics,
            "group_fields": group_fields,
            "basic_info": basic_info,
            "kline_rows": kline_rows,
        }

def _first_present(payload: dict[str, Any], keys: list[str], fallback: Any = None) -> Any:
    for key in keys:
        value = payload.get(key) if isinstance(payload, dict) else None
        if not _is_missing(value):
            return value
    return fallback


def first_non_missing(*values: Any) -> Any:
    for value in values:
        if not _is_missing(value):
            return value
    return None


def first_non_missing_with_source(*values: tuple[str, Any, int]) -> tuple[Any, str | None, int]:
    for source, value, fallback_level in values:
        if not _is_missing(value):
            return value, source, fallback_level
    return None, None, 0


def _group_name_for_source(source: str) -> str:
    if source in {"eastmoney_snapshot", "eastmoney_kline"}:
        return "snapshot" if source == "eastmoney_snapshot" else "kline"
    if source == "eastmoney_valuation":
        return "valuation"
    if source == "eastmoney_financial":
        return "financial"
    return source


def _first_row(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        return data if isinstance(data, dict) else {}
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                return item
    return {}


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


def _should_retry_exception(exc: Exception) -> bool:
    return type(exc).__name__ in {"RemoteDisconnected", "TimeoutError", "URLError", "RuntimeError"}


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return value != value
    if isinstance(value, str):
        return value.strip() in {"", "-", "N/A", "n/a", "--"}
    return value in ([], {})
