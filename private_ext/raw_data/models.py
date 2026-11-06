from typing import Any

from pydantic import BaseModel, Field


class RawStockData(BaseModel):
    symbol: str
    trade_date: str

    basic_info: dict[str, Any]
    market_snapshot: dict[str, Any]
    kline_summary: dict[str, Any]
    valuation_raw: dict[str, Any]
    financial_raw: dict[str, Any]
    capital_flow_raw: dict[str, Any]
    northbound_raw: dict[str, Any]
    dragon_tiger_raw: dict[str, Any]
    announcements_raw: list[dict[str, Any]]
    news_raw: list[dict[str, Any]]
    analyst_raw: list[dict[str, Any]]
    industry_raw: dict[str, Any]

    metadata: dict[str, Any] = Field(default_factory=dict)

