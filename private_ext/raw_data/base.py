from abc import ABC, abstractmethod

from private_ext.raw_data.models import RawStockData


class RawDataCollector(ABC):
    provider = "base"

    @abstractmethod
    def collect(self, symbol: str, trade_date: str) -> RawStockData:
        raise NotImplementedError

