from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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

    def source_path_for(self, provider: str, source_name: str, symbol: str, requested_date: str) -> Path:
        return self.root_dir / provider / "source" / source_name / f"{symbol}_{requested_date}.json"

    def read_source(self, provider: str, source_name: str, symbol: str, requested_date: str) -> list[dict[str, Any]] | None:
        path = self.source_path_for(provider, source_name, symbol, requested_date)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else None

    def write_source(
        self,
        provider: str,
        source_name: str,
        symbol: str,
        requested_date: str,
        payload: list[dict[str, Any]],
    ) -> Path:
        path = self.source_path_for(provider, source_name, symbol, requested_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return path
