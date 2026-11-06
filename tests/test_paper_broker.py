import sqlite3
from pathlib import Path

from private_ext.config import Settings
from private_ext.database.init_db import init_db
from private_ext.database.repo import ResearchRepository
from private_ext.decisions.models import InvestmentDecision
from private_ext.paper_trading.broker import PaperBroker


def test_paper_broker_records_buy_signal_order_position_and_nav(tmp_path: Path):
    settings = Settings(
        storage_dir=tmp_path,
        db_path=tmp_path / "research.sqlite",
        raw_dir=tmp_path / "raw",
        fact_pack_dir=tmp_path / "fact_packs",
        scorecard_dir=tmp_path / "scorecards",
        reports_dir=tmp_path / "reports",
        logs_dir=tmp_path / "logs",
        evidence_dir=tmp_path / "evidence",
    )
    init_db(settings)
    repo = ResearchRepository(settings.db_path)
    decision = InvestmentDecision(
        symbol="300750",
        trade_date="2026-07-03",
        rating="bullish",
        action="buy",
        confidence=0.78,
        target_position=0.05,
        horizon="20d",
        thesis="candidate",
        bullish_points=["profitability"],
        bearish_points=[],
        catalysts=[],
        risks=[],
        invalidation_conditions=["score below 60"],
        aggressive_plan="buy",
        balanced_plan="buy small",
        conservative_plan="watch",
        risk_gate_passed=True,
        risk_gate_reason="passed",
    )
    decision_id = repo.save_research_decision(1, decision)

    execution = PaperBroker(settings, repo).apply(decision_id, decision)

    assert execution.executed is True
    assert execution.quantity % 100 == 0
    with sqlite3.connect(settings.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM paper_trade_signals").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM paper_orders").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM paper_positions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM paper_nav").fetchone()[0] == 1
