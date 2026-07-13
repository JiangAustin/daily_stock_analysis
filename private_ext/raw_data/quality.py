from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


CRITICAL_FIELDS = [
    "market_snapshot.close",
    "market_snapshot.pct_change",
    "valuation_raw.pe",
    "valuation_raw.pb",
    "financial_raw.roe",
    "financial_raw.net_profit_growth",
    "kline_summary.return_20d",
]


class RawDataQualityReport(BaseModel):
    symbol: str
    requested_date: str
    actual_data_date: str | None
    provider: str
    critical_fields_present: bool
    field_coverage_ratio: float
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failed_sources: list[str] = Field(default_factory=list)
    successful_sources: list[str] = Field(default_factory=list)
    critical_field_status: dict[str, bool] = Field(default_factory=dict)
    field_provenance_summary: dict[str, dict[str, Any]] = Field(default_factory=dict)
    source_cache_used: list[str] = Field(default_factory=list)
    live_success_count: int = 0
    cache_success_count: int = 0
    live_failure_count: int = 0
    quality_level: str
    can_score: bool
    can_make_decision: bool
    notes: list[str] = Field(default_factory=list)


def build_quality_report(
    *,
    symbol: str,
    requested_date: str,
    provider: str,
    actual_data_date: str | None,
    field_values: dict[str, Any],
    warnings: list[str],
    failed_sources: list[str],
    successful_sources: list[str],
    field_provenance: dict[str, dict[str, Any]] | None = None,
    source_cache_used: list[str] | None = None,
    live_success_count: int = 0,
    cache_success_count: int = 0,
    live_failure_count: int = 0,
) -> RawDataQualityReport:
    missing_fields = [name for name, value in field_values.items() if value in (None, "", [], {})]
    present_count = len(field_values) - len(missing_fields)
    coverage_ratio = round(present_count / len(field_values), 2) if field_values else 0.0
    missing_critical = [field for field in CRITICAL_FIELDS if field in missing_fields]
    critical_field_status = {field: field not in missing_fields for field in CRITICAL_FIELDS}
    critical_fields_present = not missing_critical

    quality_level = "good"
    notes: list[str] = []
    market_fields = [
        field_values.get("market_snapshot.close"),
        field_values.get("market_snapshot.pct_change"),
        field_values.get("kline_summary.return_20d"),
    ]
    market_available_count = sum(value not in (None, "", [], {}) for value in market_fields)
    finance_available_count = sum(
        field_values.get(name) not in (None, "", [], {})
        for name in ["financial_raw.roe", "financial_raw.net_profit_growth"]
    )
    valuation_available_count = sum(
        field_values.get(name) not in (None, "", [], {})
        for name in ["valuation_raw.pe", "valuation_raw.pb"]
    )

    close_present = field_values.get("market_snapshot.close") not in (None, "", [], {})
    pct_present = field_values.get("market_snapshot.pct_change") not in (None, "", [], {})
    return20_present = field_values.get("kline_summary.return_20d") not in (None, "", [], {})

    if coverage_ratio < 0.20:
        quality_level = "failed"
        notes.append("Almost no usable raw fields were collected.")
    elif coverage_ratio < 0.50:
        quality_level = "poor"
        notes.append("Raw data is too sparse for strong investment suggestions.")
    elif coverage_ratio < 0.80:
        quality_level = "degraded"
        notes.append("Partial data is available; downstream scoring must stay conservative.")

    if market_available_count >= 2 and quality_level in {"poor", "failed"}:
        quality_level = "degraded"
        notes.append("At least two core market fields are available, so quality is not lower than degraded.")

    if close_present and return20_present and quality_level in {"poor", "failed"}:
        quality_level = "degraded"
        notes.append("Close and return_20d are available, so market quality stays at degraded or above.")

    if close_present and not pct_present and return20_present and quality_level == "poor":
        quality_level = "degraded"
        notes.append("Close and return_20d are available even though pct_change is missing.")

    if not close_present and return20_present and quality_level == "good":
        quality_level = "degraded"
        notes.append("Close is missing but return_20d is available; scoring stays enabled with degraded quality.")

    if valuation_available_count == 0 and market_available_count >= 2 and finance_available_count >= 1 and quality_level == "poor":
        quality_level = "degraded"
        notes.append("Valuation fields are missing, but market and finance data keep quality at degraded.")

    if finance_available_count == 0 and market_available_count >= 2 and valuation_available_count >= 1 and quality_level == "poor":
        quality_level = "degraded"
        notes.append("Financial fields are missing, but market and valuation data keep quality at degraded.")

    if missing_critical and quality_level == "good":
        quality_level = "degraded"
        notes.append("Critical fields are missing, so quality is downgraded.")
    elif missing_critical and quality_level == "degraded":
        notes.append("Critical fields are missing.")

    can_score = quality_level != "failed"
    can_make_decision = quality_level == "good"
    if quality_level == "degraded":
        can_make_decision = "market_snapshot.close" not in missing_fields
    if quality_level in {"poor", "failed"} or "market_snapshot.close" in missing_fields:
        can_make_decision = False
        if "market_snapshot.close" in missing_fields:
            notes.append("Close price is missing; only watch/hold decisions are allowed.")

    return RawDataQualityReport(
        symbol=symbol,
        requested_date=requested_date,
        actual_data_date=actual_data_date,
        provider=provider,
        critical_fields_present=critical_fields_present,
        field_coverage_ratio=coverage_ratio,
        missing_fields=missing_fields,
        warnings=sorted(set(warnings)),
        failed_sources=sorted(set(failed_sources)),
        successful_sources=sorted(set(successful_sources)),
        critical_field_status=critical_field_status,
        field_provenance_summary=field_provenance or {},
        source_cache_used=sorted(set(source_cache_used or [])),
        live_success_count=live_success_count,
        cache_success_count=cache_success_count,
        live_failure_count=live_failure_count,
        quality_level=quality_level,
        can_score=can_score,
        can_make_decision=can_make_decision,
        notes=notes,
    )
