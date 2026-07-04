from private_ext.fact_pack.models import StockFactPack


def score_sentiment(fact_pack: StockFactPack) -> tuple[float, str]:
    sentiments = [
        item.get("sentiment")
        for item in [*fact_pack.announcement_facts, *fact_pack.news_facts]
        if item.get("sentiment")
    ]
    score = 60
    if sentiments.count("positive") > sentiments.count("negative"):
        score += 12
    elif sentiments.count("negative") > 0:
        score -= 12
    return _clamp(score), f"sentiments={','.join(sentiments) or 'missing'}"


def _clamp(value: float) -> float:
    return max(0, min(100, round(value, 2)))

