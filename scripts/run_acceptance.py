from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

CORE_TEST_FILES = [
    "tests/test_fact_pack_builder.py",
    "tests/test_score_engine.py",
    "tests/test_decision_engine.py",
    "tests/test_risk_gate.py",
    "tests/test_private_ext_report_renderer.py",
    "tests/test_paper_broker.py",
    "tests/test_phase15_stability.py",
]

DOC_PATHS = [
    "docs/ARCHITECTURE.md",
    "docs/DATA_CONTRACT.md",
    "docs/sample_reports/stock_report_600519_2026-07-03.sample.md",
]

REPORT_COMMAND = [
    PYTHON,
    "scripts/run_stock_report.py",
    "--stocks",
    "600519,000001,300750",
    "--date",
    "2026-07-03",
    "--raw-data",
    "mock",
    "--research-adapter",
    "mock",
    "--paper-trading",
    "on",
]

STABLE_OUTPUTS = [
    "storage/raw/000001_2026-07-03.json",
    "storage/raw/300750_2026-07-03.json",
    "storage/raw/600519_2026-07-03.json",
    "storage/fact_packs/000001_2026-07-03.json",
    "storage/fact_packs/300750_2026-07-03.json",
    "storage/fact_packs/600519_2026-07-03.json",
    "storage/scorecards/000001_2026-07-03.json",
    "storage/scorecards/300750_2026-07-03.json",
    "storage/scorecards/600519_2026-07-03.json",
    "storage/reports/stock_report_000001_2026-07-03.md",
    "storage/reports/stock_report_300750_2026-07-03.md",
    "storage/reports/stock_report_600519_2026-07-03.md",
]

KNOWN_MOOTDX_HTTPX_CONFLICT = (
    "mootdx 0.11.7 has requirement httpx<0.26.0,>=0.25.0"
)


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str = ""

    @property
    def failed(self) -> bool:
        return self.status in {"FAIL", "FULL_TESTS_FAILED"}


def run_command(name: str, command: list[str], fail_status: str = "FAIL") -> CheckResult:
    print(f"\n==> {name}")
    print("$ " + " ".join(command))
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        return CheckResult(name, fail_status, f"exited with {result.returncode}")
    return CheckResult(name, "PASS")


def clean_stable_outputs() -> None:
    for relative_path in STABLE_OUTPUTS:
        path = ROOT / relative_path
        if path.exists():
            path.unlink()


def hash_stable_outputs() -> dict[str, str]:
    digests: dict[str, str] = {}
    for relative_path in STABLE_OUTPUTS:
        path = ROOT / relative_path
        if not path.exists():
            raise FileNotFoundError(f"Missing deterministic output: {relative_path}")
        digests[relative_path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def verify_deterministic_outputs() -> CheckResult:
    print("\n==> deterministic mock output check")
    try:
        clean_stable_outputs()
        subprocess.run(REPORT_COMMAND, cwd=ROOT, check=True)
        first = hash_stable_outputs()

        clean_stable_outputs()
        subprocess.run(REPORT_COMMAND, cwd=ROOT, check=True)
        second = hash_stable_outputs()
    except Exception as exc:
        return CheckResult("DETERMINISTIC", "FAIL", str(exc))

    if first != second:
        changed = sorted(
            path for path in set(first) | set(second) if first.get(path) != second.get(path)
        )
        return CheckResult(
            "DETERMINISTIC",
            "FAIL",
            "Mock outputs changed: " + ", ".join(changed),
        )
    return CheckResult("DETERMINISTIC", "PASS")


def verify_gitignore() -> CheckResult:
    print("\n==> storage gitignore check")
    ignored_paths = [
        "storage/research.sqlite",
        "storage/raw/600519_2026-07-03.json",
        "storage/fact_packs/600519_2026-07-03.json",
        "storage/scorecards/600519_2026-07-03.json",
        "storage/reports/stock_report_600519_2026-07-03.md",
        "storage/logs/run_stock_report_2026-07-03.log",
    ]
    visible_gitkeep_paths = [
        "storage/.gitkeep",
        "storage/raw/.gitkeep",
        "storage/fact_packs/.gitkeep",
        "storage/scorecards/.gitkeep",
        "storage/reports/.gitkeep",
        "storage/logs/.gitkeep",
    ]

    ignored = subprocess.run(
        ["git", "check-ignore", *ignored_paths],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if ignored.stdout:
        print(ignored.stdout, end="")
    if ignored.returncode != 0:
        return CheckResult("STORAGE IGNORE", "FAIL", "runtime outputs are not ignored")

    for path in visible_gitkeep_paths:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", path],
            cwd=ROOT,
            check=False,
        )
        if result.returncode == 0:
            return CheckResult("STORAGE IGNORE", "FAIL", f"{path} is ignored")
    return CheckResult("STORAGE IGNORE", "PASS")


def verify_docs() -> CheckResult:
    missing = [path for path in DOC_PATHS if not (ROOT / path).exists()]
    if missing:
        return CheckResult("DOCS", "FAIL", "missing: " + ", ".join(missing))
    return CheckResult("DOCS", "PASS")


def run_pip_check(strict_env: bool) -> CheckResult:
    result = run_command("python -m pip check", [PYTHON, "-m", "pip", "check"])
    if result.status == "PASS":
        return CheckResult("PIP CHECK", "PASS")

    pip_output = subprocess.run(
        [PYTHON, "-m", "pip", "check"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    combined = f"{pip_output.stdout}\n{pip_output.stderr}"
    if KNOWN_MOOTDX_HTTPX_CONFLICT in combined:
        detail = "KNOWN_ENV_WARNING: mootdx/httpx version constraint conflict"
        print(detail)
        return CheckResult("PIP CHECK", "FAIL" if strict_env else "WARNING", detail)
    return CheckResult("PIP CHECK", "FAIL" if strict_env else "WARNING", "pip check failed")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ashare-research-os Phase 1.5 acceptance checks."
    )
    parser.add_argument(
        "--full-tests",
        action="store_true",
        help="Run full repository tests. Non-default and not a Phase 1.5 core blocker.",
    )
    parser.add_argument(
        "--strict-env",
        action="store_true",
        help="Treat pip check failures as blocking environment failures.",
    )
    return parser.parse_args(argv)


def print_summary(results: list[CheckResult], full_tests_requested: bool) -> None:
    by_name = {result.name: result for result in results}
    core_failed = any(
        by_name[name].status == "FAIL"
        for name in [
            "CORE TESTS",
            "MOCK MVP",
            "INSPECT DB",
            "DETERMINISTIC",
            "STORAGE IGNORE",
            "DOCS",
        ]
    )

    print("\nAcceptance summary:")
    print(f"CORE ACCEPTANCE: {'FAIL' if core_failed else 'PASS'}")
    for name in [
        "CORE TESTS",
        "MOCK MVP",
        "INSPECT DB",
        "DETERMINISTIC",
        "STORAGE IGNORE",
        "DOCS",
        "PIP CHECK",
    ]:
        result = by_name.get(name)
        if result:
            detail = f" ({result.detail})" if result.detail else ""
            print(f"{name}: {result.status}{detail}")

    full_tests = by_name.get("FULL TESTS")
    if full_tests:
        detail = f" ({full_tests.detail})" if full_tests.detail else ""
        print(f"FULL TESTS: {full_tests.status}{detail}")
    else:
        print("FULL TESTS: SKIPPED unless --full-tests")

    print("\nRisk notes:")
    print("- Full repository tests are not run by default; use --full-tests.")
    print("- Strict environment checks are not blocking by default; use --strict-env.")
    if by_name.get("PIP CHECK", CheckResult("PIP CHECK", "PASS")).status == "WARNING":
        print("- known mootdx/httpx conflict detected.")
    elif by_name.get("PIP CHECK", CheckResult("PIP CHECK", "PASS")).status == "FAIL":
        print("- strict environment check failed.")
    if not full_tests_requested:
        print("- full repo tests not run by default.")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    results: list[CheckResult] = []
    results.append(
        run_command("CORE TESTS", [PYTHON, "-m", "pytest", *CORE_TEST_FILES])
    )
    results.append(run_command("MOCK MVP", REPORT_COMMAND))
    results.append(run_command("INSPECT DB", [PYTHON, "scripts/inspect_db.py"]))
    results.append(verify_deterministic_outputs())
    results.append(verify_gitignore())
    results.append(verify_docs())
    results.append(run_pip_check(strict_env=args.strict_env))

    if args.full_tests:
        results.append(
            run_command(
                "FULL TESTS",
                [PYTHON, "-m", "pytest", "tests"],
                fail_status="FULL_TESTS_FAILED",
            )
        )

    print_summary(results, full_tests_requested=args.full_tests)

    core_blockers = {
        "CORE TESTS",
        "MOCK MVP",
        "INSPECT DB",
        "DETERMINISTIC",
        "STORAGE IGNORE",
        "DOCS",
    }
    for result in results:
        if result.name in core_blockers and result.status == "FAIL":
            return 1
        if result.name == "PIP CHECK" and args.strict_env and result.status == "FAIL":
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
