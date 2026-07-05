import json
import sqlite3
from pathlib import Path
from typing import Any

from private_ext.decisions.models import InvestmentDecision
from private_ext.fact_pack.models import StockFactPack
from private_ext.raw_data.models import RawStockData
from private_ext.research.models import ResearchOutput
from private_ext.scoring.models import StockScorecard
from private_ext.utils.dates import utc_now_iso


class ResearchRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def create_run(self, run_date: str, symbol: str, raw_data_provider: str, research_adapter: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO research_runs (run_date, symbol, raw_data_provider, research_adapter, status, started_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_date, symbol, raw_data_provider, research_adapter, "running", utc_now_iso()),
            )
            return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str = "completed", error_message: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE research_runs SET status = ?, finished_at = ?, error_message = ? WHERE id = ?",
                (status, utc_now_iso(), error_message, run_id),
            )

    def save_raw_data(self, run_id: int, raw: RawStockData, provider: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO raw_data_snapshots (run_id, symbol, trade_date, provider, raw_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, raw.symbol, raw.trade_date, provider, _json(raw.model_dump(mode="json"))),
            )
            return int(cursor.lastrowid)

    def save_fact_pack(self, run_id: int, fact_pack: StockFactPack) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO fact_packs (
                    run_id, symbol, trade_date, fact_pack_json, missing_fields_json, data_quality_warnings_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    fact_pack.symbol,
                    fact_pack.trade_date,
                    _json(fact_pack.model_dump(mode="json")),
                    _json(fact_pack.missing_fields),
                    _json(fact_pack.data_quality_warnings),
                ),
            )
            return int(cursor.lastrowid)

    def save_scorecard(self, run_id: int, scorecard: StockScorecard) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scorecards (
                    run_id, symbol, trade_date, total_score, rating_band, scorecard_json, penalty_reasons_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    scorecard.symbol,
                    scorecard.trade_date,
                    scorecard.total_score,
                    scorecard.rating_band,
                    _json(scorecard.model_dump(mode="json")),
                    _json(scorecard.penalty_reasons),
                ),
            )
            return int(cursor.lastrowid)

    def save_research_output(self, run_id: int, output: ResearchOutput) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO research_outputs (run_id, symbol, adapter, raw_output)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, output.symbol, output.adapter, output.raw_output),
            )
            return int(cursor.lastrowid)

    def save_research_decision(self, run_id: int, decision: InvestmentDecision) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO research_decisions (
                    run_id, symbol, trade_date, rating, action, confidence, target_position, horizon,
                    thesis, bullish_points_json, bearish_points_json, catalysts_json, risks_json,
                    invalidation_conditions_json, decision_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    decision.symbol,
                    decision.trade_date,
                    decision.rating,
                    decision.action,
                    decision.confidence,
                    decision.target_position,
                    decision.horizon,
                    decision.thesis,
                    _json(decision.bullish_points),
                    _json(decision.bearish_points),
                    _json(decision.catalysts),
                    _json(decision.risks),
                    _json(decision.invalidation_conditions),
                    _json(decision.model_dump(mode="json")),
                ),
            )
            return int(cursor.lastrowid)

    def save_paper_signal(self, decision_id: int, decision: InvestmentDecision) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO paper_trade_signals (
                    decision_id, trade_date, symbol, action, confidence, target_position, risk_gate_passed, risk_gate_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    decision.trade_date,
                    decision.symbol,
                    decision.action,
                    decision.confidence,
                    decision.target_position,
                    1 if decision.risk_gate_passed else 0,
                    decision.risk_gate_reason,
                ),
            )
            return int(cursor.lastrowid)

    def save_paper_order(
        self,
        signal_id: int | None,
        trade_date: str,
        symbol: str,
        action: str,
        price: float,
        quantity: int,
        amount: float,
        fee: float,
        reason: str,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO paper_orders (signal_id, trade_date, symbol, action, price, quantity, amount, fee, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (signal_id, trade_date, symbol, action, price, quantity, amount, fee, reason),
            )
            return int(cursor.lastrowid)

    def upsert_position(self, trade_date: str, symbol: str, quantity: int, cost_price: float, last_price: float) -> int:
        market_value = quantity * last_price
        unrealized_pnl = (last_price - cost_price) * quantity
        with self._connect() as conn:
            conn.execute("DELETE FROM paper_positions WHERE trade_date = ? AND symbol = ?", (trade_date, symbol))
            cursor = conn.execute(
                """
                INSERT INTO paper_positions (trade_date, symbol, quantity, cost_price, last_price, market_value, unrealized_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (trade_date, symbol, quantity, cost_price, last_price, market_value, unrealized_pnl),
            )
            return int(cursor.lastrowid)

    def save_nav(self, trade_date: str, cash: float, market_value: float, daily_return: float | None = None) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO paper_nav (trade_date, cash, market_value, total_nav, daily_return)
                VALUES (?, ?, ?, ?, ?)
                """,
                (trade_date, cash, market_value, cash + market_value, daily_return),
            )
            return int(cursor.lastrowid)

    def table_counts(self) -> dict[str, int]:
        tables = [
            "research_runs",
            "raw_data_snapshots",
            "fact_packs",
            "scorecards",
            "research_outputs",
            "research_decisions",
            "paper_trade_signals",
            "paper_orders",
            "paper_positions",
            "paper_nav",
            "decision_outcomes",
        ]
        with self._connect() as conn:
            return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}

    def latest_nav(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT trade_date, cash, market_value, total_nav, daily_return FROM paper_nav ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def latest_runs(self, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT run_date, symbol, raw_data_provider, research_adapter, status, error_message
                FROM research_runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
