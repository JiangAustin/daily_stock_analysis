#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
import shutil

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
    run_mode = _resolve_run_mode(args.raw_data, args.research_adapter, args.run_mode)
    file_run_id = _build_file_run_id(args.trade_date, args.raw_data, args.research_adapter, run_mode)
    run_dir = settings.runs_dir / file_run_id
    latest_dir = _latest_dir_for_mode(run_mode)
    run_paths = _build_run_paths(run_dir, latest_dir, args.trade_date)
    logger = setup_run_logger(run_paths["run_log"])

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
        run_id = repo.create_run(
            args.trade_date,
            symbol,
            collector.provider,
            research_adapter.adapter,
            run_mode=run_mode,
            file_run_id=file_run_id,
            run_dir=str(run_dir),
        )
        logger.info("start symbol=%s run_id=%s", symbol, run_id)
        try:
            raw = collector.collect(symbol, args.trade_date)
            raw.metadata = {
                **(raw.metadata or {}),
                "run_mode": run_mode,
                "file_run_id": file_run_id,
                "run_dir": str(run_dir),
                "research_adapter": research_adapter.adapter,
            }
            repo.save_raw_data(run_id, raw, collector.provider)
            raw_path = run_paths["raw_dir"] / f"{symbol}_{args.trade_date}.json"
            latest_raw_path = run_paths["latest_raw_dir"] / f"{symbol}_{args.trade_date}.json"
            _write_json(raw_path, raw.model_dump(mode="json"))
            _write_json(latest_raw_path, raw.model_dump(mode="json"))

            fact_pack = fact_builder.build(raw)
            fact_pack.metadata = {
                **(fact_pack.metadata or {}),
                "run_mode": run_mode,
                "file_run_id": file_run_id,
                "run_dir": str(run_dir),
                "research_adapter": research_adapter.adapter,
            }
            repo.save_fact_pack(run_id, fact_pack)
            fact_pack_path = run_paths["fact_pack_dir"] / f"{symbol}_{args.trade_date}.json"
            latest_fact_pack_path = run_paths["latest_fact_pack_dir"] / f"{symbol}_{args.trade_date}.json"
            _write_json(fact_pack_path, fact_pack.model_dump(mode="json"))
            _write_json(latest_fact_pack_path, fact_pack.model_dump(mode="json"))

            scorecard = score_engine.score(fact_pack)
            scorecard.metadata = {
                **(scorecard.metadata or {}),
                "run_mode": run_mode,
                "file_run_id": file_run_id,
                "run_dir": str(run_dir),
                "research_adapter": research_adapter.adapter,
                "raw_data_provider": collector.provider,
            }
            repo.save_scorecard(run_id, scorecard)
            scorecard_path = run_paths["scorecard_dir"] / f"{symbol}_{args.trade_date}.json"
            latest_scorecard_path = run_paths["latest_scorecard_dir"] / f"{symbol}_{args.trade_date}.json"
            _write_json(scorecard_path, scorecard.model_dump(mode="json"))
            _write_json(latest_scorecard_path, scorecard.model_dump(mode="json"))

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
            report_path = render_stock_report(fact_pack, scorecard, decision, execution, run_paths["reports_dir"])
            latest_report_path = run_paths["latest_reports_dir"] / report_path.name
            latest_report_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(report_path, latest_report_path)
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

    _copy_log_to_latest(run_paths["run_log"], run_paths["latest_log"])

    if not reports:
        print("Stock report run failed for all requested stocks.")
        for symbol, error in failures:
            print(f"- {symbol}: {error}")
        return 1

    summary = {
        "run_id": file_run_id,
        "run_mode": run_mode,
        "run_dir": str(run_dir),
        "raw_data": collector.provider,
        "research_adapter": research_adapter.adapter,
        "reports": [str(path) for path in reports],
        "database": str(settings.db_path),
        "date": args.trade_date,
        "stocks": stocks,
        "failures": failures,
    }
    if args.print_json_summary:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    print("Stock report run completed.")
    print(f"Date: {args.trade_date}")
    print(f"Run mode: {run_mode}")
    print(f"Raw data: {collector.provider}")
    print(f"Research adapter: {research_adapter.adapter}")
    print(f"Run ID: {file_run_id}")
    print(f"Run directory: {run_dir}")
    print(f"Stocks: {','.join(stocks)}")
    print(f"Reports: {run_paths['reports_dir']}/")
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
    parser.add_argument(
        "--refresh-data",
        action="store_true",
        help="Force live fetch for this run and disable cache fallback.",
    )
    parser.add_argument("--run-mode", choices=["mock_mvp", "realdata_smoke", "manual"])
    parser.add_argument("--print-json-summary", action="store_true")
    return parser.parse_args()


def _ensure_dirs() -> None:
    for path in (
        settings.storage_dir,
        settings.runs_dir,
        settings.latest_mock_mvp_dir,
        settings.latest_realdata_smoke_dir,
        settings.latest_manual_dir,
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


def _resolve_run_mode(raw_data: str, research_adapter: str, explicit_run_mode: str | None) -> str:
    if explicit_run_mode:
        return explicit_run_mode
    if raw_data == "mock" and research_adapter == "mock":
        return "mock_mvp"
    if raw_data in {"akshare", "eastmoney", "composite"}:
        return "realdata_smoke"
    return "manual"


def _build_file_run_id(trade_date: str, raw_data: str, research_adapter: str, run_mode: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{trade_date}_{raw_data}_{research_adapter}_{run_mode}_{timestamp}"


def _latest_dir_for_mode(run_mode: str) -> Path:
    if run_mode == "mock_mvp":
        return settings.latest_mock_mvp_dir
    if run_mode == "realdata_smoke":
        return settings.latest_realdata_smoke_dir
    return settings.latest_manual_dir


def _build_run_paths(run_dir: Path, latest_dir: Path, trade_date: str) -> dict[str, Path]:
    return {
        "run_dir": run_dir,
        "raw_dir": run_dir / "raw",
        "fact_pack_dir": run_dir / "fact_packs",
        "scorecard_dir": run_dir / "scorecards",
        "reports_dir": run_dir / "reports",
        "logs_dir": run_dir / "logs",
        "run_log": run_dir / "logs" / f"run_stock_report_{trade_date}.log",
        "latest_raw_dir": latest_dir / "raw",
        "latest_fact_pack_dir": latest_dir / "fact_packs",
        "latest_scorecard_dir": latest_dir / "scorecards",
        "latest_reports_dir": latest_dir / "reports",
        "latest_logs_dir": latest_dir / "logs",
        "latest_log": latest_dir / "logs" / f"run_stock_report_{trade_date}.log",
    }


def _copy_log_to_latest(run_log: Path, latest_log: Path) -> None:
    if not run_log.exists():
        return
    latest_log.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(run_log, latest_log)


if __name__ == "__main__":
    raise SystemExit(main())
