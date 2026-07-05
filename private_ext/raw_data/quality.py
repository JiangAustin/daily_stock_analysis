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
) -> RawDataQualityReport:
    missing_fields = [name for name, value in field_values.items() if value in (None, "", [], {})]
    present_count = len(field_values) - len(missing_fields)
    coverage_ratio = round(present_count / len(field_values), 2) if field_values else 0.0
    missing_critical = [field for field in CRITICAL_FIELDS if field in missing_fields]
    critical_fields_present = not missing_critical

    quality_level = "good"
    notes: list[str] = []
    if coverage_ratio < 0.20:
        quality_level = "failed"
        notes.append("Almost no usable raw fields were collected.")
    elif coverage_ratio < 0.50:
        quality_level = "poor"
        notes.append("Raw data is too sparse for strong investment suggestions.")
    elif coverage_ratio < 0.80:
        quality_level = "degraded"
        notes.append("Partial data is available; downstream scoring must stay conservative.")

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
        quality_level=quality_level,
        can_score=can_score,
        can_make_decision=can_make_decision,
        notes=notes,
    )
