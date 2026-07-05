from __future__ import annotations

from private_ext.raw_data.akshare_collector import AkShareRawDataCollector
from private_ext.raw_data.base import RawDataCollector
from private_ext.raw_data.composite_collector import CompositeRawDataCollector
from private_ext.raw_data.eastmoney_collector import EastMoneyRawDataCollector
from private_ext.raw_data.manual_override_collector import ManualOverrideRawDataCollector
from private_ext.raw_data.mock_collector import MockRawDataCollector


def create_raw_data_collector(name: str, **kwargs) -> RawDataCollector:
    provider = (name or "").strip().lower()
    manual_data_dir = kwargs.pop("manual_data_dir", None)
    manual_file_format = kwargs.pop("manual_file_format", None)
    manual_required = kwargs.pop("manual_required", True)
    if provider == "mock":
        return MockRawDataCollector()
    if provider == "akshare":
        return AkShareRawDataCollector(**kwargs)
    if provider == "eastmoney":
        return EastMoneyRawDataCollector(**kwargs)
    if provider == "composite":
        return CompositeRawDataCollector(**kwargs)
    if provider == "manual_csv":
        return ManualOverrideRawDataCollector(
            manual_data_dir=manual_data_dir,
            file_format="csv",
            provider_name="manual_csv",
            required=manual_required,
        )
    if provider == "manual_json":
        return ManualOverrideRawDataCollector(
            manual_data_dir=manual_data_dir,
            file_format="json",
            provider_name="manual_json",
            required=manual_required,
        )
    if provider == "composite_manual":
        return CompositeRawDataCollector(
            manual_override=ManualOverrideRawDataCollector(
                manual_data_dir=manual_data_dir,
                file_format=manual_file_format or "auto",
                provider_name="manual_override",
                required=manual_required,
            ),
            **kwargs,
        )
    if provider == "a_stock_data":
        raise NotImplementedError(
            "a_stock_data provider is not implemented yet; use --raw-data akshare, eastmoney, composite, or mock"
        )
    raise ValueError(f"Unknown raw data provider: {name}")
