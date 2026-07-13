from private_ext.fact_pack.models import StockFactPack
from private_ext.scoring.common import clamp_score


def score_sentiment(fact_pack: StockFactPack) -> tuple[float, str]:
    sentiments = [
        item.get("sentiment")
        for item in [*fact_pack.announcement_facts, *fact_pack.news_facts]
        if item.get("sentiment")
    ]
    if not sentiments:
        return 50.0, "sentiments=missing; conservative_due_to_missing=sentiment_inputs"
    score = 60
    if sentiments.count("positive") > sentiments.count("negative"):
        score += 12
    elif sentiments.count("negative") > 0:
        score -= 12
    return clamp_score(score), f"sentiments={','.join(sentiments)}"
