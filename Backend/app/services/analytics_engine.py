# app/services/analytics_engine.py

import math


# --------------------------------------------------
# TREND SCORE (RELATIVE DEMAND MODEL)
# --------------------------------------------------
def compute_trend_score(raw_trend_score: float) -> float:
    """
    Normalize trend score into realistic 0–100 band.
    """
    if raw_trend_score <= 0:
        return 35  # baseline niche demand

    return max(min(raw_trend_score, 90), 20)


# --------------------------------------------------
# MARKET STRENGTH (ECONOMIC OPPORTUNITY)
# --------------------------------------------------
def compute_market_strength(tam: float) -> float:
    """
    Convert TAM into normalized 0–100 opportunity score.
    """
    if tam <= 0:
        return 40

    # log scaling prevents massive TAM inflation
    strength = math.log10(tam) * 10
    return min(max(strength, 30), 95)


# --------------------------------------------------
# COMPETITION SCORE (LOG SCALE)
# --------------------------------------------------
def compute_competition_score(competitor_count: int) -> float:
    if competitor_count <= 0:
        return 10.0

    # Assume 1000 competitors = worst case
    max_expected = 1000

    normalized = min(competitor_count / max_expected, 1)

    score = 10 * (1 - normalized**0.5)

    return round(max(1.0, score), 2)


# --------------------------------------------------
# RISK SCORE (DYNAMIC MODEL)
# --------------------------------------------------
def compute_risk_score(ai_score: float,
                       trend_score: float,
                       competition_score: float) -> float:

    demand_penalty = max(0, 60 - trend_score)
    product_penalty = max(0, 60 - (ai_score * 10))

    risk = (
        competition_score * 0.4 +
        demand_penalty * 0.3 +
        product_penalty * 0.3
    )

    return round(min(risk / 10, 10), 2)


# --------------------------------------------------
# FINAL STARTUP VIABILITY INDEX
# --------------------------------------------------
def compute_final_score(ai_score: float,
                        trend_score: float,
                        market_strength: float,
                        competition_score: float,
                        risk_score: float) -> float:

    final = (
        ai_score * 0.40 +
        (trend_score / 10) * 0.25 +
        (market_strength / 10) * 0.20 -
        risk_score * 0.08
    )

    return round(max(min(final, 10), 1), 2)