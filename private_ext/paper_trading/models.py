from pydantic import BaseModel


class PaperTradeExecution(BaseModel):
    action: str
    price: float
    quantity: int
    amount: float
    fee: float
    executed: bool
    reason: str

