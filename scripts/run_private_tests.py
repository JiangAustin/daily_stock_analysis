#!/usr/bin/env python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
PRIVATE_TEST_FILES = [
    "tests/test_fact_pack_builder.py",
    "tests/test_score_engine.py",
    "tests/test_decision_engine.py",
    "tests/test_risk_gate.py",
    "tests/test_private_ext_report_renderer.py",
    "tests/test_paper_broker.py",
    "tests/test_phase15_stability.py",
    "tests/test_akshare_collector_mapping.py",
    "tests/test_akshare_fallbacks.py",
    "tests/test_akshare_kline.py",
    "tests/test_raw_data_quality.py",
    "tests/test_raw_data_cache.py",
    "tests/test_source_level_cache.py",
    "tests/test_quality_field_provenance.py",
    "tests/test_realdata_quality_integration.py",
]


def main() -> int:
    command = [PYTHON, "-m", "pytest", *PRIVATE_TEST_FILES]
    print("$ " + " ".join(command))
    result = subprocess.run(command, cwd=ROOT, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
