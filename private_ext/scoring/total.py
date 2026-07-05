from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.capital_flow import score_capital_flow
from private_ext.scoring.financial_health import score_financial_health
from private_ext.scoring.growth import score_growth
from private_ext.scoring.models import StockScorecard
from private_ext.scoring.profitability import score_profitability
from private_ext.scoring.risk import score_risk
from private_ext.scoring.sentiment import score_sentiment
from private_ext.scoring.technical import score_technical
from private_ext.scoring.valuation import score_valuation


class ScoreEngine:
    def score(self, fact_pack: StockFactPack) -> StockScorecard:
        quality_level = str(fact_pack.metadata.get("quality_level", "good"))
        can_score = bool(fact_pack.metadata.get("can_score", True))
        valuation_score, valuation_explain = score_valuation(fact_pack)
        growth_score, growth_explain = score_growth(fact_pack)
        profitability_score, profitability_explain = score_profitability(fact_pack)
        financial_health_score, financial_health_explain = score_financial_health(fact_pack)
        capital_flow_score, capital_flow_explain = score_capital_flow(fact_pack)
        technical_score, technical_explain = score_technical(fact_pack)
        sentiment_score, sentiment_explain = score_sentiment(fact_pack)
        risk_score, risk_explain, penalty_reasons = score_risk(fact_pack)

        total = (
            valuation_score * 0.15
            + growth_score * 0.15
            + profitability_score * 0.15
            + financial_health_score * 0.15
            + capital_flow_score * 0.10
            + technical_score * 0.10
            + sentiment_score * 0.10
            + risk_score * 0.10
        )
        data_penalty = min(12, len(fact_pack.missing_fields) * 1.5 + len(fact_pack.data_quality_warnings) * 0.5)
        if data_penalty:
            penalty_reasons.extend(
                f"missing_data_penalty:{item}" for item in fact_pack.missing_fields[:8]
            )
            total -= data_penalty
        if not can_score:
            penalty_reasons.append("data_quality:failed")
            total = min(total, 40)
        elif quality_level == "poor":
            penalty_reasons.append("data_quality:poor")
            total = min(total, 60)
        elif quality_level == "degraded":
            penalty_reasons.append("data_quality:degraded")
            total = min(total, 75)
        total_score = round(total, 2)
        return StockScorecard(
            symbol=fact_pack.symbol,
            trade_date=fact_pack.trade_date,
            valuation_score=valuation_score,
            growth_score=growth_score,
            profitability_score=profitability_score,
            financial_health_score=financial_health_score,
            capital_flow_score=capital_flow_score,
            technical_score=technical_score,
            sentiment_score=sentiment_score,
            risk_score=risk_score,
            total_score=total_score,
            rating_band=_rating_band(total_score),
            score_explanations={
                "valuation": valuation_explain,
                "growth": growth_explain,
                "profitability": profitability_explain,
                "financial_health": financial_health_explain,
                "capital_flow": capital_flow_explain,
                "technical": technical_explain,
                "sentiment": sentiment_explain,
                "risk": risk_explain,
            },
            penalty_reasons=penalty_reasons,
            metadata={
                "quality_level": quality_level,
                "field_coverage_ratio": fact_pack.metadata.get("field_coverage_ratio"),
                "can_score": can_score,
                "can_make_decision": fact_pack.metadata.get("can_make_decision", True),
            },
        )


def _rating_band(total_score: float) -> str:
    if total_score >= 80:
        return "strong"
    if total_score >= 65:
        return "positive"
    if total_score >= 50:
        return "neutral"
    return "weak"
