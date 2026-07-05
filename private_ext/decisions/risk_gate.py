from private_ext.config import Settings, settings
from private_ext.decisions.models import InvestmentDecision
from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.models import StockScorecard


class RiskGate:
    def __init__(self, config: Settings = settings):
        self.config = config

    def apply(
        self,
        decision: InvestmentDecision,
        scorecard: StockScorecard,
        fact_pack: StockFactPack,
        current_positions: int = 0,
    ) -> InvestmentDecision:
        gated = decision.model_copy(deep=True)
        reasons = []
        quality_level = str(fact_pack.metadata.get("quality_level", "good"))
        can_make_decision = bool(fact_pack.metadata.get("can_make_decision", True))
        if gated.target_position > self.config.max_position_per_stock:
            gated.target_position = self.config.max_position_per_stock
            reasons.append("target_position_capped")
        if not can_make_decision and gated.action in {"buy", "watch", "reduce"}:
            gated.action = "hold" if gated.action != "buy" else "watch"
            gated.target_position = 0
            reasons.append("真实数据质量不足，买入信号降级为观察/持有。")
        if quality_level == "poor" and gated.action == "buy":
            gated.action = "watch"
            gated.target_position = 0
            reasons.append("真实数据质量不足，买入信号降级为观察/持有。")
        if quality_level == "degraded" and gated.action == "buy" and gated.confidence < 0.78:
            gated.action = "watch"
            gated.target_position = 0
            reasons.append("真实数据质量不足，买入信号降级为观察/持有。")
        if gated.action == "buy" and gated.confidence < 0.70:
            gated.action = "watch"
            gated.target_position = 0
            reasons.append("confidence_below_buy_threshold")
        if scorecard.risk_score < 50:
            gated.action = "watch" if gated.action == "buy" else gated.action
            gated.target_position = 0
            reasons.append("risk_score_below_threshold")
        if scorecard.penalty_reasons:
            gated.action = "watch" if gated.action == "buy" else gated.action
            gated.target_position = 0
            reasons.append("penalty_risks_present")
        if len(fact_pack.data_quality_warnings) > 2 and gated.action == "buy":
            gated.action = "watch"
            gated.target_position = 0
            reasons.append("data_quality_warnings_too_many")
        if not fact_pack.announcement_facts and gated.action == "buy":
            gated.action = "watch"
            gated.target_position = 0
            reasons.append("announcement_evidence_missing")
        if current_positions >= self.config.max_positions and gated.action == "buy":
            gated.action = "watch"
            gated.target_position = 0
            reasons.append("max_positions_reached")
        gated.risk_gate_passed = not reasons
        gated.risk_gate_reason = "passed" if not reasons else ",".join(reasons)
        return gated
