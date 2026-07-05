from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    storage_dir: Path = Path("storage")
    db_path: Path = Path("storage/research.sqlite")
    raw_dir: Path = Path("storage/raw")
    raw_cache_dir: Path = Path("storage/raw_cache")
    fact_pack_dir: Path = Path("storage/fact_packs")
    scorecard_dir: Path = Path("storage/scorecards")
    reports_dir: Path = Path("storage/reports")
    logs_dir: Path = Path("storage/logs")
    evidence_dir: Path = Path("storage/evidence")

    initial_cash: float = 1_000_000.0
    max_position_per_stock: float = 0.05
    max_positions: int = 10

    commission_rate: float = 0.0003
    stamp_tax_rate: float = 0.0005
    slippage_rate: float = 0.001

    default_raw_data: str = "mock"
    default_research_adapter: str = "mock"


settings = Settings()
