from __future__ import annotations

import json
from pathlib import Path

from private_ext.raw_data.models import RawStockData


class RawDataCache:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def path_for(self, provider: str, symbol: str, requested_date: str) -> Path:
        return self.root_dir / provider / f"{symbol}_{requested_date}.json"

    def read(self, provider: str, symbol: str, requested_date: str) -> RawStockData | None:
        path = self.path_for(provider, symbol, requested_date)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return RawStockData.model_validate(payload)

    def write(self, provider: str, symbol: str, requested_date: str, raw: RawStockData) -> Path:
        path = self.path_for(provider, symbol, requested_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(raw.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path
