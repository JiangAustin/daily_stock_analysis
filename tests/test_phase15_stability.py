from pathlib import Path
import importlib.util
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def load_acceptance_module():
    module_path = ROOT / "scripts/run_acceptance.py"
    spec = importlib.util.spec_from_file_location("run_acceptance_for_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase15_acceptance_assets_exist():
    required_paths = [
        ".gitignore",
        "constraints.txt",
        "scripts/run_acceptance.py",
        "docs/ARCHITECTURE.md",
        "docs/DATA_CONTRACT.md",
        "docs/ENVIRONMENT.md",
        "docs/sample_reports/stock_report_600519_2026-07-03.sample.md",
        "storage/.gitkeep",
        "storage/raw/.gitkeep",
        "storage/fact_packs/.gitkeep",
        "storage/scorecards/.gitkeep",
        "storage/reports/.gitkeep",
        "storage/logs/.gitkeep",
    ]

    missing = [path for path in required_paths if not (ROOT / path).exists()]

    assert missing == []


def test_gitignore_keeps_runtime_outputs_out_of_version_control():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    required_patterns = [
        "storage/*.sqlite",
        "storage/**/*.json",
        "storage/**/*.md",
        "storage/**/*.log",
        "storage/**/*.parquet",
        "storage/**/*.csv",
        "!storage/**/.gitkeep",
    ]

    for pattern in required_patterns:
        assert pattern in gitignore


def test_gitignore_keeps_storage_gitkeep_files_visible():
    gitkeep_paths = [
        "storage/.gitkeep",
        "storage/raw/.gitkeep",
        "storage/fact_packs/.gitkeep",
        "storage/scorecards/.gitkeep",
        "storage/reports/.gitkeep",
        "storage/logs/.gitkeep",
    ]

    for path in gitkeep_paths:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", path],
            cwd=ROOT,
            check=False,
        )
        assert result.returncode == 1, f"{path} should not be ignored"


def test_constraints_pin_httpx_for_mootdx_compatibility():
    constraints = (ROOT / "constraints.txt").read_text(encoding="utf-8")

    assert "httpx>=0.25.0,<0.26.0" in constraints


def test_acceptance_script_declares_required_commands():
    script = (ROOT / "scripts/run_acceptance.py").read_text(encoding="utf-8")

    expected_fragments = [
        "CORE_TEST_FILES",
        "--full-tests",
        "--strict-env",
        "FULL_TESTS_FAILED",
        "KNOWN_ENV_WARNING: mootdx/httpx version constraint conflict",
        "CORE ACCEPTANCE:",
        "FULL TESTS:",
        "scripts/run_stock_report.py",
        "--stocks",
        "600519,000001,300750",
        "--raw-data",
        "mock",
        "--research-adapter",
        "mock",
        "--paper-trading",
        "on",
        "scripts/inspect_db.py",
        "python -m pip check",
    ]

    for fragment in expected_fragments:
        assert fragment in script

    assert '"tests"' not in script.split("CORE_TEST_FILES", 1)[0]


def test_core_acceptance_test_whitelist_excludes_full_repo_tests():
    script = (ROOT / "scripts/run_acceptance.py").read_text(encoding="utf-8")

    expected_tests = [
        "tests/test_fact_pack_builder.py",
        "tests/test_score_engine.py",
        "tests/test_decision_engine.py",
        "tests/test_risk_gate.py",
        "tests/test_private_ext_report_renderer.py",
        "tests/test_paper_broker.py",
        "tests/test_phase15_stability.py",
    ]

    for test_path in expected_tests:
        assert test_path in script

    assert '["tests"]' not in script


def test_full_tests_failure_is_blocking_when_requested(monkeypatch, capsys):
    acceptance = load_acceptance_module()

    def fake_run_command(name, command, fail_status="FAIL"):
        if name == "FULL TESTS":
            return acceptance.CheckResult(name, fail_status, "exited with 1")
        return acceptance.CheckResult(name, "PASS")

    monkeypatch.setattr(acceptance, "run_command", fake_run_command)
    monkeypatch.setattr(
        acceptance,
        "verify_deterministic_outputs",
        lambda: acceptance.CheckResult("DETERMINISTIC", "PASS"),
    )
    monkeypatch.setattr(
        acceptance,
        "verify_gitignore",
        lambda: acceptance.CheckResult("STORAGE IGNORE", "PASS"),
    )
    monkeypatch.setattr(
        acceptance,
        "verify_docs",
        lambda: acceptance.CheckResult("DOCS", "PASS"),
    )
    monkeypatch.setattr(
        acceptance,
        "run_pip_check",
        lambda strict_env: acceptance.CheckResult("PIP CHECK", "PASS"),
    )

    exit_code = acceptance.main(["--full-tests"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "FULL TESTS: FULL_TESTS_FAILED" in output


def test_architecture_and_contract_docs_describe_phase15_boundaries():
    architecture = (ROOT / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs/DATA_CONTRACT.md").read_text(encoding="utf-8")
    environment = (ROOT / "docs/ENVIRONMENT.md").read_text(encoding="utf-8")

    for phrase in [
        "Raw Data",
        "Fact Pack",
        "Scorecard",
        "Decision",
        "Risk Gate",
        "Paper Trading",
        "Evaluation",
    ]:
        assert phrase in architecture

    for model_name in [
        "RawStockData",
        "StockFactPack",
        "StockScorecard",
        "InvestmentDecision",
    ]:
        assert model_name in contract

    for phrase in [
        "mootdx/httpx",
        "Phase 1.5 Mock MVP 不依赖 mootdx",
        "不建议现在为了 mootdx 硬降级主环境 httpx",
    ]:
        assert phrase in environment
