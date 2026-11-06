from pydantic import BaseModel, Field


class StockScorecard(BaseModel):
    symbol: str
    trade_date: str

    valuation_score: float
    growth_score: float
    profitability_score: float
    financial_health_score: float
    capital_flow_score: float
    technical_score: float
    sentiment_score: float
    risk_score: float

    total_score: float
    rating_band: str

    score_explanations: dict[str, str]
    penalty_reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, str | float | bool | None] = Field(default_factory=dict)
