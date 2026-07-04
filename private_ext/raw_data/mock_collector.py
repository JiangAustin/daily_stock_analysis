from __future__ import annotations

from copy import deepcopy

from private_ext.raw_data.base import RawDataCollector
from private_ext.raw_data.models import RawStockData


_MOCKS: dict[str, dict] = {
    "600519": {
        "name": "贵州茅台",
        "industry": "白酒",
        "close": 1500.0,
        "pe": 28.0,
        "pb": 9.5,
        "dividend_yield": 2.1,
        "revenue_growth": 8.0,
        "profit_growth": 12.0,
        "roe": 29.0,
        "gross_margin": 91.0,
        "net_margin": 52.0,
        "debt_ratio": 18.0,
        "cashflow_quality": "strong",
        "main_net_inflow": 0.8,
        "northbound_net_inflow": 1.5,
        "trend": "up",
        "volatility": 18.0,
        "sentiment": "positive",
        "risk_events": [],
    },
    "000001": {
        "name": "平安银行",
        "industry": "银行",
        "close": 10.0,
        "pe": 5.5,
        "pb": 0.55,
        "dividend_yield": 4.2,
        "revenue_growth": 3.0,
        "profit_growth": 4.0,
        "roe": 10.5,
        "gross_margin": 45.0,
        "net_margin": 26.0,
        "debt_ratio": 65.0,
        "cashflow_quality": "stable",
        "main_net_inflow": 0.2,
        "northbound_net_inflow": 0.1,
        "trend": "sideways",
        "volatility": 12.0,
        "sentiment": "neutral",
        "risk_events": ["净息差承压"],
    },
    "300750": {
        "name": "宁德时代",
        "industry": "新能源电池",
        "close": 200.0,
        "pe": 36.0,
        "pb": 5.8,
        "dividend_yield": 0.8,
        "revenue_growth": 24.0,
        "profit_growth": 28.0,
        "roe": 22.0,
        "gross_margin": 24.0,
        "net_margin": 12.0,
        "debt_ratio": 42.0,
        "cashflow_quality": "improving",
        "main_net_inflow": 1.8,
        "northbound_net_inflow": 2.4,
        "trend": "up",
        "volatility": 34.0,
        "sentiment": "positive",
        "risk_events": ["高估值", "行业竞争加剧"],
    },
}


class MockRawDataCollector(RawDataCollector):
    provider = "mock"

    def collect(self, symbol: str, trade_date: str) -> RawStockData:
        data = deepcopy(_MOCKS.get(symbol, _neutral_profile(symbol)))
        return RawStockData(
            symbol=symbol,
            trade_date=trade_date,
            basic_info={"name": data["name"], "industry": data["industry"], "market": "cn"},
            market_snapshot={"close": data["close"], "currency": "CNY"},
            kline_summary={"trend": data["trend"], "volatility": data["volatility"], "ma5_above_ma20": data["trend"] == "up"},
            valuation_raw={"pe": data["pe"], "pb": data["pb"], "dividend_yield": data["dividend_yield"]},
            financial_raw={
                "revenue_growth": data["revenue_growth"],
                "profit_growth": data["profit_growth"],
                "roe": data["roe"],
                "gross_margin": data["gross_margin"],
                "net_margin": data["net_margin"],
                "debt_ratio": data["debt_ratio"],
                "operating_cashflow_quality": data["cashflow_quality"],
            },
            capital_flow_raw={"main_net_inflow": data["main_net_inflow"]},
            northbound_raw={"net_inflow": data["northbound_net_inflow"]},
            dragon_tiger_raw={"listed": False, "reason": ""},
            announcements_raw=[
                {"title": f"{data['name']} 经营情况公告", "date": trade_date, "sentiment": data["sentiment"], "summary": "Mock 公告证据"}
            ],
            news_raw=[{"title": f"{data['industry']} 行业跟踪", "date": trade_date, "sentiment": data["sentiment"]}],
            analyst_raw=[{"rating": "neutral", "target_price": round(data["close"] * 1.08, 2)}],
            industry_raw={"industry": data["industry"], "cycle": "stable", "prosperity": data["sentiment"]},
            metadata={"provider": self.provider, "mock": True, "risk_events": data["risk_events"]},
        )


def _neutral_profile(symbol: str) -> dict:
    return {
        "name": f"股票{symbol}",
        "industry": "通用行业",
        "close": 100.0,
        "pe": 18.0,
        "pb": 2.0,
        "dividend_yield": 1.5,
        "revenue_growth": 8.0,
        "profit_growth": 8.0,
        "roe": 12.0,
        "gross_margin": 35.0,
        "net_margin": 10.0,
        "debt_ratio": 45.0,
        "cashflow_quality": "stable",
        "main_net_inflow": 0.0,
        "northbound_net_inflow": 0.0,
        "trend": "sideways",
        "volatility": 20.0,
        "sentiment": "neutral",
        "risk_events": [],
    }
