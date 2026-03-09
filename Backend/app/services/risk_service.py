def calculate_risk(score, trend_score, competitor_count):
    risk = 0

    if score < 5:
        risk += 4

    if trend_score < 30:
        risk += 3

    if competitor_count > 300:
        risk += 3

    if risk >= 7:
        level = "High Risk"
    elif risk >= 4:
        level = "Medium Risk"
    else:
        level = "Low Risk"

    return {
        "risk_score": risk,
        "risk_level": level
    }