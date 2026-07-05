from __future__ import annotations

import math
import re
import statistics
from datetime import datetime, timedelta
from typing import Any, Callable

try:
    import akshare as ak
except ImportError:  # pragma: no cover - exercised through runtime entrypoint
    ak = None

from private_ext.raw_data.base import RawDataCollector
from private_ext.raw_data.models import RawStockData


class AkShareNotInstalledError(RuntimeError):
    """Raised when the optional AkShare dependency is unavailable."""


class AkShareRawDataCollector(RawDataCollector):
    provider = "akshare"

    def collect(self, symbol: str, trade_date: str) -> RawStockData:
        if ak is None:
            raise AkShareNotInstalledError(
                "AkShare is not installed. Run: pip install -r requirements-realdata.txt"
            )

        normalized_symbol = _normalize_symbol(symbol)
        market = _infer_market(normalized_symbol)
        trade_date_compact = trade_date.replace("-", "")
        start_date = (
            datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=150)
        ).strftime("%Y%m%d")

        warnings: list[str] = []
        payloads: dict[str, Any] = {}

        def safe_call(name: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                warnings.append(f"{name}_failed:{type(exc).__name__}")
                payloads[name] = {"error": str(exc)}
                return []

            records = _to_records(result)
            payloads[name] = records
            if not records:
                warnings.append(f"{name}_empty")
            return records

        info_records = safe_call("stock_individual_info_em", ak.stock_individual_info_em, symbol=normalized_symbol)
        spot_records = safe_call("stock_zh_a_spot_em", ak.stock_zh_a_spot_em)
        hist_records = safe_call(
            "stock_zh_a_hist",
            ak.stock_zh_a_hist,
            symbol=normalized_symbol,
            period="daily",
            start_date=start_date,
            end_date=trade_date_compact,
            adjust="qfq",
        )
        financial_records = safe_call(
            "stock_financial_analysis_indicator",
            ak.stock_financial_analysis_indicator,
            symbol=normalized_symbol,
            start_year=str(max(2000, int(trade_date[:4]) - 2)),
        )
        fund_flow_records = safe_call(
            "stock_individual_fund_flow",
            ak.stock_individual_fund_flow,
            stock=normalized_symbol,
            market=market,
        )
        northbound_records = safe_call("stock_hsgt_individual_em", ak.stock_hsgt_individual_em, symbol=normalized_symbol)
        dragon_tiger_records = safe_call(
            "stock_lhb_stock_statistic_em",
            ak.stock_lhb_stock_statistic_em,
            symbol="近一月",
        )
        news_records = safe_call("stock_news_em", ak.stock_news_em, symbol=normalized_symbol)
        analyst_records = safe_call("stock_research_report_em", ak.stock_research_report_em, symbol=normalized_symbol)

        info_map = _records_to_item_map(info_records)
        spot_row = _find_record_by_symbol(spot_records, normalized_symbol)
        latest_financial = financial_records[-1] if financial_records else {}
        latest_flow = fund_flow_records[-1] if fund_flow_records else {}
        latest_northbound = northbound_records[-1] if northbound_records else {}
        latest_dragon = _find_record_by_symbol(dragon_tiger_records, normalized_symbol)

        kline_summary, kline_warnings = _build_kline_summary(hist_records)
        warnings.extend(kline_warnings)

        basic_info = {
            "name": _first_present(
                spot_row,
                ["名称", "股票简称"],
                fallback=_first_present(info_map, ["股票简称", "股票名称"], fallback=normalized_symbol),
            ),
            "industry": _first_present(info_map, ["行业", "所属行业"], fallback="A股"),
            "market": "cn",
            "listed_date": _normalize_date(_first_present(info_map, ["上市时间", "上市日期"])),
        }

        market_snapshot = {
            "close": _as_float(_first_present(spot_row, ["最新价", "收盘"])),
            "pct_change": _as_float(_first_present(spot_row, ["涨跌幅", "涨跌幅(%)"])),
            "turnover_amount": _as_float(_first_present(spot_row, ["成交额"])),
            "turnover_rate": _as_float(_first_present(spot_row, ["换手率"])),
            "total_market_value": _as_float(
                _first_present(spot_row, ["总市值"], fallback=_first_present(info_map, ["总市值"]))
            ),
            "float_market_value": _as_float(
                _first_present(spot_row, ["流通市值"], fallback=_first_present(info_map, ["流通市值"]))
            ),
            "currency": "CNY",
        }

        valuation_raw = {
            "pe": _as_float(_first_present(spot_row, ["市盈率-动态", "市盈率", "PE"])),
            "pb": _as_float(_first_present(spot_row, ["市净率", "PB"])),
            "ps": _as_float(_first_present(spot_row, ["市销率", "PS"])),
            "dividend_yield": _as_float(
                _first_present(info_map, ["股息率", "股息率TTM"], fallback=_first_present(latest_financial, ["股息率(%)"]))
            ),
        }

        financial_raw = {
            "revenue_growth": _as_float(
                _first_present(latest_financial, ["主营业务收入增长率(%)", "营业收入同比增长率(%)", "营业总收入同比增长率(%)"])
            ),
            "profit_growth": _as_float(
                _first_present(latest_financial, ["净利润增长率(%)", "净利润同比增长率(%)", "扣非净利润同比增长率(%)"])
            ),
            "roe": _as_float(_first_present(latest_financial, ["净资产收益率(%)", "净资产收益率-摊薄(%)"])),
            "gross_margin": _as_float(_first_present(latest_financial, ["销售毛利率(%)", "毛利率(%)"])),
            "net_margin": _as_float(_first_present(latest_financial, ["销售净利率(%)", "净利率(%)"])),
            "debt_ratio": _as_float(_first_present(latest_financial, ["资产负债率(%)"])),
            "operating_cashflow": _as_float(
                _first_present(latest_financial, ["每股经营性现金流(元)", "每股经营现金流(元)"])
            ),
        }
        financial_raw["operating_cashflow_quality"] = _classify_cashflow(financial_raw["operating_cashflow"])

        capital_flow_raw = {
            "main_net_inflow": _as_float(_first_present(latest_flow, ["主力净流入-净额", "主力净流入净额"])),
            "super_large_net_inflow": _as_float(_first_present(latest_flow, ["超大单净流入-净额"])),
            "large_net_inflow": _as_float(_first_present(latest_flow, ["大单净流入-净额"])),
            "mid_net_inflow": _as_float(_first_present(latest_flow, ["中单净流入-净额"])),
            "small_net_inflow": _as_float(_first_present(latest_flow, ["小单净流入-净额"])),
        }

        northbound_raw = {
            "net_inflow": _as_float(
                _first_present(latest_northbound, ["持股市值", "当日增持估计-市值", "当日持股市值"])
            ),
            "holding_shares": _as_float(_first_present(latest_northbound, ["持股数量", "持股数"])),
            "trade_date": _normalize_date(_first_present(latest_northbound, ["持股日期", "日期"])),
        }

        dragon_tiger_raw = {
            "listed": bool(latest_dragon),
            "reason": _first_present(latest_dragon, ["解读", "上榜原因", "最近上榜日"], fallback=""),
            "raw": latest_dragon or {},
        }

        announcements_raw: list[dict[str, Any]] = []
        news_raw = [
            {
                "title": _first_present(item, ["新闻标题", "标题"], fallback=""),
                "date": _normalize_date(_first_present(item, ["发布时间", "日期"])),
                "source": _first_present(item, ["文章来源", "来源"], fallback=""),
                "sentiment": "neutral",
            }
            for item in news_records[:10]
            if _first_present(item, ["新闻标题", "标题"])
        ]
        analyst_raw = [
            {
                "rating": _first_present(item, ["评级", "最新评级"], fallback=""),
                "target_price": _as_float(_first_present(item, ["目标价", "目标价(元)"])),
                "date": _normalize_date(_first_present(item, ["报告日期", "日期"])),
                "title": _first_present(item, ["报告名称", "标题"], fallback=""),
            }
            for item in analyst_records[:10]
            if _first_present(item, ["评级", "最新评级", "目标价", "目标价(元)"])
        ]
        industry_raw = {
            "industry": basic_info["industry"],
            "concepts": _split_text(_first_present(info_map, ["概念板块", "所属概念"])),
            "region": _first_present(info_map, ["地域", "地区"], fallback=""),
        }

        missing_fields = _missing_field_names(
            {
                "basic_info.name": basic_info.get("name"),
                "market_snapshot.close": market_snapshot.get("close"),
                "valuation_raw.pe": valuation_raw.get("pe"),
                "financial_raw.roe": financial_raw.get("roe"),
            }
        )
        warnings.extend(f"missing:{field}" for field in missing_fields)

        if not _has_any_value(
            basic_info,
            market_snapshot,
            valuation_raw,
            financial_raw,
            capital_flow_raw,
            news_raw,
            analyst_raw,
        ):
            raise RuntimeError(f"AkShare collector could not fetch any usable data for {normalized_symbol}")

        return RawStockData(
            symbol=normalized_symbol,
            trade_date=trade_date,
            basic_info=basic_info,
            market_snapshot=market_snapshot,
            kline_summary=kline_summary,
            valuation_raw=valuation_raw,
            financial_raw=financial_raw,
            capital_flow_raw=capital_flow_raw,
            northbound_raw=northbound_raw,
            dragon_tiger_raw=dragon_tiger_raw,
            announcements_raw=announcements_raw,
            news_raw=news_raw,
            analyst_raw=analyst_raw,
            industry_raw=industry_raw,
            metadata={
                "provider": self.provider,
                "original_symbol": symbol,
                "normalized_symbol": normalized_symbol,
                "data_quality_warnings": sorted(set(warnings)),
                "missing_fields": missing_fields,
                "source_payloads": payloads,
            },
        )


def _normalize_symbol(symbol: str) -> str:
    text = (symbol or "").strip().upper()
    text = text.replace(".", "")
    text = re.sub(r"^(SH|SZ|BJ)", "", text)
    text = re.sub(r"(SH|SZ|BJ)$", "", text)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 6:
        return digits[-6:]
    raise ValueError(f"Unsupported A-share symbol: {symbol}")


def _infer_market(symbol: str) -> str:
    if symbol.startswith(("5", "6", "9")):
        return "sh"
    return "sz"


def _to_records(frame: Any) -> list[dict[str, Any]]:
    if frame is None:
        return []
    empty = getattr(frame, "empty", None)
    if empty is True:
        return []
    try:
        records = frame.to_dict(orient="records")
    except Exception:
        return []
    return [dict(item) for item in records]


def _records_to_item_map(records: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in records:
        key = item.get("item") or item.get("项目") or item.get("指标")
        value = item.get("value") if "value" in item else item.get("值")
        if key:
            result[str(key)] = value
    return result


def _find_record_by_symbol(records: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
    for item in records:
        code = _normalize_code_like(
            _first_present(item, ["代码", "股票代码", "证券代码", "code"], fallback="")
        )
        if code == symbol:
            return item
    return {}


def _normalize_code_like(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[-6:] if len(digits) >= 6 else digits


def _build_kline_summary(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if not records:
        return {}, ["kline_history_missing"]

    closes = [_as_float(_first_present(item, ["收盘", "收盘价", "close"])) for item in records]
    closes = [item for item in closes if item is not None]
    if not closes:
        return {}, ["kline_close_missing"]

    ma5 = _moving_average(closes, 5)
    ma20 = _moving_average(closes, 20)
    ma60 = _moving_average(closes, 60)
    latest = closes[-1]
    daily_returns = []
    for prev, current in zip(closes, closes[1:]):
        if prev:
            daily_returns.append((current / prev - 1) * 100)
    volatility = round(statistics.pstdev(daily_returns), 2) if len(daily_returns) >= 2 else None

    trend = "sideways"
    if ma20 is not None and latest > ma20:
        trend = "up"
    elif ma20 is not None and latest < ma20:
        trend = "down"

    return (
        {
            "close_series_length": len(closes),
            "pct_change_5d": _window_return(closes, 5),
            "pct_change_20d": _window_return(closes, 20),
            "pct_change_60d": _window_return(closes, 60),
            "ma5": ma5,
            "ma20": ma20,
            "ma60": ma60,
            "ma5_above_ma20": bool(ma5 is not None and ma20 is not None and ma5 >= ma20),
            "trend": trend,
            "volatility": volatility,
        },
        warnings,
    )


def _moving_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return round(sum(values[-window:]) / window, 4)


def _window_return(values: list[float], window: int) -> float | None:
    if len(values) <= window:
        return None
    base = values[-window - 1]
    if not base:
        return None
    return round((values[-1] / base - 1) * 100, 2)


def _first_present(payload: dict[str, Any], keys: list[str], fallback: Any = None) -> Any:
    for key in keys:
        value = payload.get(key) if isinstance(payload, dict) else None
        if value not in (None, "", [], {}):
            return value
    return fallback


def _normalize_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text[:10] if len(text) >= 10 else text


def _as_float(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _classify_cashflow(value: float | None) -> str | None:
    if value is None:
        return None
    if value > 1:
        return "strong"
    if value > 0:
        return "improving"
    return "weak"


def _split_text(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    for splitter in (";", "；", ",", "，", "|", "/"):
        text = text.replace(splitter, " ")
    return [item for item in text.split() if item]


def _missing_field_names(payload: dict[str, Any]) -> list[str]:
    return [key for key, value in payload.items() if value in (None, "", [], {})]


def _has_any_value(*payloads: Any) -> bool:
    for payload in payloads:
        if isinstance(payload, dict):
            if any(value not in (None, "", [], {}) for value in payload.values()):
                return True
        elif isinstance(payload, list) and payload:
            return True
    return False
