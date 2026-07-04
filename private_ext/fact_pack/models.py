from typing import Any

from pydantic import BaseModel, Field


class StockFactPack(BaseModel):
    symbol: str
    trade_date: str

    identity: dict[str, Any]
    price_facts: dict[str, Any]
    valuation_facts: dict[str, Any]
    growth_facts: dict[str, Any]
    profitability_facts: dict[str, Any]
    balance_sheet_facts: dict[str, Any]
    cashflow_facts: dict[str, Any]
    capital_flow_facts: dict[str, Any]
    technical_facts: dict[str, Any]
    announcement_facts: list[dict[str, Any]]
    news_facts: list[dict[str, Any]]
    risk_facts: list[dict[str, Any]]

    missing_fields: list[str] = Field(default_factory=list)
    data_quality_warnings: list[str] = Field(default_factory=list)

