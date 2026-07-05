from __future__ import annotations

from private_ext.raw_data.akshare_collector import AkShareRawDataCollector
from private_ext.raw_data.base import RawDataCollector
from private_ext.raw_data.mock_collector import MockRawDataCollector


def create_raw_data_collector(name: str, **kwargs) -> RawDataCollector:
    provider = (name or "").strip().lower()
    if provider == "mock":
        return MockRawDataCollector()
    if provider == "akshare":
        return AkShareRawDataCollector(**kwargs)
    if provider == "a_stock_data":
        raise NotImplementedError(
            "a_stock_data provider is not implemented yet; use --raw-data akshare or mock"
        )
    raise ValueError(f"Unknown raw data provider: {name}")
