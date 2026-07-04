from private_ext.config import Settings, settings
from private_ext.database.repo import ResearchRepository
from private_ext.decisions.models import InvestmentDecision
from private_ext.paper_trading.models import PaperTradeExecution


MOCK_PRICES = {"600519": 1500.0, "000001": 10.0, "300750": 200.0}


class PaperBroker:
    def __init__(self, config: Settings = settings, repo: ResearchRepository | None = None):
        self.config = config
        self.repo = repo
        self.cash = config.initial_cash
        self.positions: dict[str, tuple[int, float]] = {}

    def apply(self, decision_id: int, decision: InvestmentDecision) -> PaperTradeExecution:
        price = MOCK_PRICES.get(decision.symbol, 100.0)
        signal_id = self.repo.save_paper_signal(decision_id, decision) if self.repo else None

        if decision.action == "buy" and decision.risk_gate_passed and decision.target_position > 0:
            budget = self.config.initial_cash * min(decision.target_position, self.config.max_position_per_stock)
            effective_price = price * (1 + self.config.slippage_rate)
            quantity = int(budget // (effective_price * 100)) * 100
            amount = round(quantity * effective_price, 2)
            fee = round(amount * self.config.commission_rate, 2)
            if quantity > 0 and amount + fee <= self.cash:
                self.cash -= amount + fee
                self.positions[decision.symbol] = (quantity, effective_price)
                if self.repo:
                    self.repo.save_paper_order(signal_id, decision.trade_date, decision.symbol, "buy", effective_price, quantity, amount, fee, "risk gate passed")
                    self.repo.upsert_position(decision.trade_date, decision.symbol, quantity, effective_price, price)
                    self.mark_to_market(decision.trade_date)
                return PaperTradeExecution(action="buy", price=effective_price, quantity=quantity, amount=amount, fee=fee, executed=True, reason="risk gate passed")
            return PaperTradeExecution(action="buy", price=price, quantity=0, amount=0, fee=0, executed=False, reason="insufficient budget or lot size")

        if decision.action == "reduce" and decision.symbol in self.positions:
            quantity, cost_price = self.positions.pop(decision.symbol)
            effective_price = price * (1 - self.config.slippage_rate)
            amount = round(quantity * effective_price, 2)
            fee = round(amount * (self.config.commission_rate + self.config.stamp_tax_rate), 2)
            self.cash += amount - fee
            if self.repo:
                self.repo.save_paper_order(signal_id, decision.trade_date, decision.symbol, "sell", effective_price, quantity, amount, fee, "reduce signal")
                self.repo.upsert_position(decision.trade_date, decision.symbol, 0, cost_price, price)
                self.mark_to_market(decision.trade_date)
            return PaperTradeExecution(action="reduce", price=effective_price, quantity=quantity, amount=amount, fee=fee, executed=True, reason="reduce signal")

        return PaperTradeExecution(action=decision.action, price=price, quantity=0, amount=0, fee=0, executed=False, reason=f"{decision.action} only")

    def mark_to_market(self, trade_date: str) -> int | None:
        market_value = 0.0
        if self.repo:
            for symbol, (quantity, cost_price) in self.positions.items():
                price = MOCK_PRICES.get(symbol, 100.0)
                market_value += quantity * price
                self.repo.upsert_position(trade_date, symbol, quantity, cost_price, price)
            return self.repo.save_nav(trade_date, round(self.cash, 2), round(market_value, 2))
        return None
