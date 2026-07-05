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
    manual_file_format = kwargs.pop("manual_file_format", "auto")
    manual_required = kwargs.pop("manual_required", True)
    if provider == "mock":
        return MockRawDataCollector()
    if provider == "akshare":
        return AkShareRawDataCollector(**kwargs)
    if provider == "eastmoney":
        return EastMoneyRawDataCollector(**kwargs)
    if provider == "composite":
        return CompositeRawDataCollector(**kwargs)
    if provider in {"manual_csv", "manual_json"}:
        file_format = "csv" if provider.endswith("csv") else "json"
        return ManualOverrideRawDataCollector(
            manual_data_dir=manual_data_dir,
            file_format=file_format,
            provider_name=provider,
            required=manual_required,
            **kwargs,
        )
    if provider == "composite_manual":
        manual_override = kwargs.pop(
            "manual_override",
            ManualOverrideRawDataCollector(
                manual_data_dir=manual_data_dir,
                file_format=manual_file_format,
                provider_name="manual_override",
                required=False,
                **kwargs,
            ),
        )
        return CompositeRawDataCollector(manual_override=manual_override, **kwargs)
    if provider == "a_stock_data":
        raise NotImplementedError(
            "a_stock_data provider is not implemented yet; use --raw-data akshare, eastmoney, composite, manual_csv, manual_json, composite_manual, or mock"
        )
    raise ValueError(f"Unknown raw data provider: {name}")
