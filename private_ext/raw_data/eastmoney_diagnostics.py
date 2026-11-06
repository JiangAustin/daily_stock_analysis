from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EastMoneyEndpointResult(BaseModel):
    endpoint_name: str
    purpose: str
    status: str
    error_type: str | None = None
    error_message: str | None = None
    elapsed_ms: int = 0
    target_fields: list[str] = Field(default_factory=list)
    fields_found: list[str] = Field(default_factory=list)
    fields_missing: list[str] = Field(default_factory=list)
    used_cache: bool = False
    raw_sample_path: str | None = None
    notes: list[str] = Field(default_factory=list)


class EastMoneyCandidateResult(BaseModel):
    candidate_name: str
    endpoint_group: str
    status: str
    url_summary: str | None = None
    params_summary: dict[str, Any] = Field(default_factory=dict)
    http_status: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    elapsed_ms: int = 0
    target_fields: list[str] = Field(default_factory=list)
    fields_found: list[str] = Field(default_factory=list)
    fields_missing: list[str] = Field(default_factory=list)
    used_cache: bool = False
    parser_name: str | None = None
    raw_shape: str | None = None
    notes: list[str] = Field(default_factory=list)


class EastMoneyDiagnosticsReport(BaseModel):
    symbol: str
    requested_date: str
    endpoint_results: list[EastMoneyEndpointResult] = Field(default_factory=list)
    candidate_results: list[EastMoneyCandidateResult] = Field(default_factory=list)
    successful_endpoints: list[str] = Field(default_factory=list)
    failed_endpoints: list[str] = Field(default_factory=list)
    group_status: dict[str, str] = Field(default_factory=dict)
    best_candidate_by_group: dict[str, str] = Field(default_factory=dict)
    fields_filled_by_endpoint: dict[str, list[str]] = Field(default_factory=dict)
    fields_filled_by_candidate: dict[str, list[str]] = Field(default_factory=dict)
    unresolved_fields: list[str] = Field(default_factory=list)
    remote_errors: list[str] = Field(default_factory=list)
    parse_errors: list[str] = Field(default_factory=list)
    cache_used: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
