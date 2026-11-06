from pydantic import BaseModel


class ResearchOutput(BaseModel):
    symbol: str
    trade_date: str
    adapter: str
    raw_output: str
    summary: str

