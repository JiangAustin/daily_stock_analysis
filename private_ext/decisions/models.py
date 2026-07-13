from pydantic import BaseModel, Field


class InvestmentDecision(BaseModel):
    symbol: str
    trade_date: str

    rating: str
    action: str
    confidence: float
    target_position: float
    horizon: str

    thesis: str
    bullish_points: list[str]
    bearish_points: list[str]
    catalysts: list[str]
    risks: list[str]
    invalidation_conditions: list[str]

    aggressive_plan: str
    balanced_plan: str
    conservative_plan: str

    risk_gate_passed: bool = False
    risk_gate_reason: str | None = None

