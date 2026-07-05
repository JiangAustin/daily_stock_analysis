from private_ext.fact_pack.builder import FactPackBuilder
from private_ext.raw_data.mock_collector import MockRawDataCollector


def test_fact_pack_builder_generates_structured_facts_from_mock_raw_data():
    raw = MockRawDataCollector().collect("600519", "2026-07-03")

    fact_pack = FactPackBuilder().build(raw)

    assert fact_pack.symbol == "600519"
    assert fact_pack.trade_date == "2026-07-03"
    assert fact_pack.identity["name"] == "贵州茅台"
    assert fact_pack.valuation_facts["pe"] > 0
    assert fact_pack.profitability_facts["roe"] > 0
    assert fact_pack.missing_fields == []

