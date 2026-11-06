from __future__ import annotations

import math
from typing import Any

from private_ext.raw_data.akshare_fallbacks import KEY_FIELDS, summarize_field_provenance
from private_ext.raw_data.models import RawStockData


MERGE_FIELDS = [
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

RELATIVE_CONFLICT_THRESHOLDS = {
    "market_snapshot.close": 0.03,
    "valuation_raw.pe": 0.10,
    "valuation_raw.pb": 0.10,
}
ABSOLUTE_CONFLICT_THRESHOLDS = {
    "market_snapshot.pct_change": 0.02,
    "kline_summary.return_20d": 0.05,
}


def merge_raw_stock_data(primary: RawStockData, secondary: RawStockData) -> RawStockData:
    merged_payload = primary.model_dump(mode="json")
    secondary_payload = secondary.model_dump(mode="json")
    merged_metadata = dict(merged_payload.get("metadata") or {})
    secondary_metadata = dict(secondary_payload.get("metadata") or {})
    merge_warnings = list(dict.fromkeys([
        *(merged_metadata.get("merge_warnings") or []),
        *(secondary_metadata.get("merge_warnings") or []),
    ]))

    primary_provenance = dict(merged_metadata.get("field_provenance") or {})
    secondary_provenance = dict(secondary_metadata.get("field_provenance") or {})
    merged_provenance = {**primary_provenance}

    for field in MERGE_FIELDS:
        primary_value = _get_nested(merged_payload, field)
        secondary_value = _get_nested(secondary_payload, field)
        primary_meta = primary_provenance.get(field, {})
        secondary_meta = secondary_provenance.get(field, {})

        if _is_missing(primary_value) and not _is_missing(secondary_value):
            _set_nested(merged_payload, field, secondary_value)
            merged_provenance[field] = secondary_meta
            continue

        if _is_missing(secondary_value) or _is_missing(primary_value):
            if field in primary_provenance:
                merged_provenance[field] = primary_meta
            continue

        if _should_override_cached_primary(primary_meta, secondary_meta):
            _set_nested(merged_payload, field, secondary_value)
            merged_provenance[field] = secondary_meta
            continue

        if _has_conflict(field, primary_value, secondary_value):
            merge_warnings.append(f"provider_value_conflict:{field}")
        merged_provenance[field] = primary_meta or secondary_meta

    merged_metadata["provider"] = "composite"
    merged_metadata["providers_used"] = _unique_list([
        *(merged_metadata.get("providers_used") or [primary.metadata.get("provider", "akshare")]),
        *(secondary_metadata.get("providers_used") or [secondary.metadata.get("provider", "eastmoney")]),
    ])
    merged_metadata["provider_reports"] = {
        primary.metadata.get("provider", "akshare"): primary.metadata.get("quality_report", {}),
        secondary.metadata.get("provider", "eastmoney"): secondary.metadata.get("quality_report", {}),
    }
    merged_metadata["merge_warnings"] = _unique_list(merge_warnings)
    merged_metadata["field_provenance"] = summarize_field_provenance({**merged_provenance})
    merged_metadata["data_quality_warnings"] = _unique_list([
        *(merged_metadata.get("data_quality_warnings") or []),
        *(secondary_metadata.get("data_quality_warnings") or []),
        *merged_metadata["merge_warnings"],
    ])
    merged_payload["metadata"] = merged_metadata
    return RawStockData.model_validate(merged_payload)


def _should_override_cached_primary(primary_meta: dict[str, Any], secondary_meta: dict[str, Any]) -> bool:
    primary_cached = bool(primary_meta.get("is_cached")) or primary_meta.get("source") == "raw_cache"
    secondary_live_high = (
        not bool(secondary_meta.get("is_cached"))
        and secondary_meta.get("confidence") == "high"
        and secondary_meta.get("source") not in (None, "", "raw_cache")
    )
    return primary_cached and secondary_live_high


def _has_conflict(field: str, primary_value: Any, secondary_value: Any) -> bool:
    primary_number = _to_number(primary_value)
    secondary_number = _to_number(secondary_value)
    if primary_number is None or secondary_number is None:
        return False

    if field in RELATIVE_CONFLICT_THRESHOLDS:
        if primary_number == 0:
            return False
        return abs(secondary_number - primary_number) / abs(primary_number) > RELATIVE_CONFLICT_THRESHOLDS[field]
    if field in ABSOLUTE_CONFLICT_THRESHOLDS:
        return abs(secondary_number - primary_number) > ABSOLUTE_CONFLICT_THRESHOLDS[field]
    return False


def _to_number(value: Any) -> float | None:
    if _is_missing(value):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _is_missing(value: Any) -> bool:
    if value in (None, "", "-", "--", "N/A", "n/a", [], {}):
        return True
    return isinstance(value, float) and math.isnan(value)


def _get_nested(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _set_nested(payload: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = payload
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def _unique_list(values: list[Any]) -> list[Any]:
    seen: list[Any] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen
