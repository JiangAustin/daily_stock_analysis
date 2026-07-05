import json

from private_ext.fact_pack.models import StockFactPack
from private_ext.research.base import ResearchAdapter
from private_ext.research.models import ResearchOutput
from private_ext.scoring.models import StockScorecard


class MockResearchAdapter(ResearchAdapter):
    adapter = "mock"

    def analyze(self, fact_pack: StockFactPack, scorecard: StockScorecard) -> ResearchOutput:
        if scorecard.total_score >= 80:
            rating, action, confidence = "bullish", "buy", 0.78
        elif scorecard.total_score >= 65:
            rating, action, confidence = "neutral-bullish", "watch", 0.68
        elif scorecard.total_score >= 50:
            rating, action, confidence = "neutral", "hold", 0.55
        else:
            rating, action, confidence = "bearish", "reduce", 0.65
        payload = {
            "rating": rating,
            "action": action,
            "confidence": confidence,
            "summary": f"{fact_pack.identity.get('name', fact_pack.symbol)} mock research score {scorecard.total_score}",
        }
        return ResearchOutput(
            symbol=fact_pack.symbol,
            trade_date=fact_pack.trade_date,
            adapter=self.adapter,
            raw_output=json.dumps(payload, ensure_ascii=False),
            summary=payload["summary"],
        )

