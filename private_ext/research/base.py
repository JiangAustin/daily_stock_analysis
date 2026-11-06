from abc import ABC, abstractmethod

from private_ext.fact_pack.models import StockFactPack
from private_ext.research.models import ResearchOutput
from private_ext.scoring.models import StockScorecard


class ResearchAdapter(ABC):
    adapter = "base"

    @abstractmethod
    def analyze(self, fact_pack: StockFactPack, scorecard: StockScorecard) -> ResearchOutput:
        raise NotImplementedError

