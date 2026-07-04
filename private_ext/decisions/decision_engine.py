from private_ext.decisions.models import InvestmentDecision
from private_ext.decisions.normalizer import normalize_action
from private_ext.research.models import ResearchOutput
from private_ext.scoring.models import StockScorecard


class DecisionEngine:
    def build(self, scorecard: StockScorecard, research_output: ResearchOutput) -> InvestmentDecision:
        if scorecard.total_score >= 80:
            rating, action, confidence, target_position = "bullish", "buy", 0.78, 0.05
        elif scorecard.total_score >= 65:
            rating, action, confidence, target_position = "neutral-bullish", "watch", 0.68, 0.02
        elif scorecard.total_score >= 50:
            rating, action, confidence, target_position = "neutral", "hold", 0.55, 0.0
        else:
            rating, action, confidence, target_position = "bearish", "reduce", 0.65, 0.0
        return InvestmentDecision(
            symbol=scorecard.symbol,
            trade_date=scorecard.trade_date,
            rating=rating,
            action=normalize_action(action),
            confidence=confidence,
            target_position=target_position,
            horizon="20d",
            thesis=research_output.summary,
            bullish_points=_bullish_points(scorecard),
            bearish_points=_bearish_points(scorecard),
            catalysts=["等待业绩、行业景气和资金面进一步验证"],
            risks=scorecard.penalty_reasons or ["评分或事实链变化导致观点失效"],
            invalidation_conditions=["总分跌破 60", "出现重大减持、问询函或业绩雷", "核心事实链无法验证"],
            aggressive_plan="若风险门通过，按目标仓位上限执行模拟买入。",
            balanced_plan="等待价格和资金面确认后再分批模拟。",
            conservative_plan="只观察，不产生真实交易行为。",
        )


def _bullish_points(scorecard: StockScorecard) -> list[str]:
    points = []
    if scorecard.profitability_score >= 70:
        points.append("盈利质量较强")
    if scorecard.growth_score >= 70:
        points.append("成长评分较高")
    if scorecard.capital_flow_score >= 65:
        points.append("资金面偏积极")
    return points or ["暂无显著看多项"]


def _bearish_points(scorecard: StockScorecard) -> list[str]:
    points = []
    if scorecard.valuation_score < 55:
        points.append("估值压力偏高")
    if scorecard.risk_score < 65:
        points.append("风险评分偏弱")
    if scorecard.technical_score < 55:
        points.append("技术趋势未确认")
    return points or ["暂无显著看空项"]

