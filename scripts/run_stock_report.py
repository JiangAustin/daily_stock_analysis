#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from private_ext.config import settings
from private_ext.database.init_db import init_db
from private_ext.database.repo import ResearchRepository
from private_ext.decisions.decision_engine import DecisionEngine
from private_ext.decisions.risk_gate import RiskGate
from private_ext.fact_pack.builder import FactPackBuilder
from private_ext.paper_trading.broker import PaperBroker
from private_ext.paper_trading.models import PaperTradeExecution
from private_ext.raw_data import AkShareNotInstalledError, create_raw_data_collector
from private_ext.reports.stock_report import render_stock_report
from private_ext.research.mock_adapter import MockResearchAdapter
from private_ext.scoring.total import ScoreEngine
from private_ext.utils.logger import setup_run_logger


def main() -> int:
    args = _parse_args()
    if args.research_adapter != "mock":
        raise SystemExit("Phase 2 only supports --research-adapter mock")

    _ensure_dirs()
    init_db(settings)
    repo = ResearchRepository(settings.db_path)
    logger = setup_run_logger(settings.logs_dir, args.trade_date)

    try:
        collector = create_raw_data_collector(
            args.raw_data,
            use_cache=True,
            refresh=args.refresh_data,
        )
    except AkShareNotInstalledError as exc:
        raise SystemExit(str(exc)) from exc
    except (NotImplementedError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    fact_builder = FactPackBuilder()
    score_engine = ScoreEngine()
    research_adapter = MockResearchAdapter()
    decision_engine = DecisionEngine()
    risk_gate = RiskGate(settings)
    paper_broker = PaperBroker(settings, repo)

    stocks = [stock.strip() for stock in args.stocks.split(",") if stock.strip()]
    reports = []
    failures = []
    for symbol in stocks:
        run_id = repo.create_run(args.trade_date, symbol, collector.provider, research_adapter.adapter)
        logger.info("start symbol=%s run_id=%s", symbol, run_id)
        try:
            raw = collector.collect(symbol, args.trade_date)
            repo.save_raw_data(run_id, raw, collector.provider)
            _write_json(settings.raw_dir / f"{symbol}_{args.trade_date}.json", raw.model_dump(mode="json"))

            fact_pack = fact_builder.build(raw)
            repo.save_fact_pack(run_id, fact_pack)
            _write_json(settings.fact_pack_dir / f"{symbol}_{args.trade_date}.json", fact_pack.model_dump(mode="json"))

            scorecard = score_engine.score(fact_pack)
            repo.save_scorecard(run_id, scorecard)
            _write_json(settings.scorecard_dir / f"{symbol}_{args.trade_date}.json", scorecard.model_dump(mode="json"))

            research_output = research_adapter.analyze(fact_pack, scorecard)
            repo.save_research_output(run_id, research_output)

            decision = decision_engine.build(scorecard, research_output, fact_pack=fact_pack)
            decision = risk_gate.apply(decision, scorecard, fact_pack, current_positions=len(paper_broker.positions))
            decision_id = repo.save_research_decision(run_id, decision)

            if args.paper_trading == "on":
                execution = paper_broker.apply(decision_id, decision)
            else:
                execution = PaperTradeExecution(
                    action=decision.action,
                    price=0,
                    quantity=0,
                    amount=0,
                    fee=0,
                    executed=False,
                    reason="paper trading off",
                )
            report_path = render_stock_report(fact_pack, scorecard, decision, execution, settings.reports_dir)
            reports.append(report_path)
            repo.finish_run(run_id)
            logger.info("completed symbol=%s report=%s", symbol, report_path)
        except Exception as exc:
            repo.finish_run(run_id, status="failed", error_message=str(exc))
            logger.exception("failed symbol=%s", symbol)
            failures.append((symbol, str(exc)))
            continue

    if args.paper_trading == "on":
        paper_broker.mark_to_market(args.trade_date)

    if not reports:
        print("Stock report run failed for all requested stocks.")
        for symbol, error in failures:
            print(f"- {symbol}: {error}")
        return 1

    print("Stock report MVP completed.")
    print(f"Date: {args.trade_date}")
    print(f"Stocks: {','.join(stocks)}")
    print(f"Reports: {settings.reports_dir}/")
    print(f"Database: {settings.db_path}")
    if failures:
        print("Failed Stocks:")
        for symbol, error in failures:
            print(f"- {symbol}: {error}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run A-share research report pipeline.")
    parser.add_argument("--stocks", required=True)
    parser.add_argument("--date", dest="trade_date", required=True)
    parser.add_argument("--raw-data", default=settings.default_raw_data)
    parser.add_argument("--research-adapter", default=settings.default_research_adapter)
    parser.add_argument("--paper-trading", choices=["on", "off"], default="on")
    parser.add_argument("--refresh-data", action="store_true")
    return parser.parse_args()


def _ensure_dirs() -> None:
    for path in (
        settings.storage_dir,
        settings.raw_dir,
        settings.raw_cache_dir,
        settings.fact_pack_dir,
        settings.scorecard_dir,
        settings.reports_dir,
        settings.logs_dir,
        settings.evidence_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
