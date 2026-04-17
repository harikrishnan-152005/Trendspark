import asyncio

from pytrends.request import TrendReq

from app.core.cache import generate_cache_key, get_cache, set_cache
from app.services.analytics_engine import compute_trend_score


def _dedupe_terms(values):
    deduped = []
    seen = set()

    for value in values:
        text = str(value).strip()
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue

        seen.add(key)
        deduped.append(text)

    return deduped


def _build_estimated_monthly_series(keywords, base_score):
    labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    normalized_base = max(min(float(base_score or 38), 90), 20)
    seed = sum(ord(char) for char in " ".join(keywords or [])) % 17

    values = []
    for index in range(len(labels)):
        seasonal_wave = ((index % 6) - 2.5) * 1.6
        half_year_wave = (1 if index >= 6 else -1) * ((seed % 5) * 0.35)
        step_variation = ((seed + index * 3) % 7) - 3
        value = normalized_base + seasonal_wave + half_year_wave + (step_variation * 0.45)
        values.append(round(max(min(value, 95), 18), 2))

    return labels, values


def map_to_trend_terms(keywords):
    text = " ".join(keywords).lower()

    if any(value in text for value in ["food", "organic", "vegetable", "rice", "millet", "farm"]):
        return ["organic food", "vegetables", "grocery"]

    if any(value in text for value in ["tech", "ai", "software", "app", "saas"]):
        return ["technology", "software", "startup"]

    if any(value in text for value in ["health", "fitness", "medical", "wellness"]):
        return ["health", "fitness", "wellness"]

    if any(value in text for value in ["shop", "store", "marketplace", "delivery", "commerce"]):
        return ["ecommerce", "online shopping", "retail"]

    if any(value in text for value in ["education", "learning", "course", "school", "edtech"]):
        return ["education", "online learning"]

    return ["business", "startup"]


def get_baseline_keywords(mapped_keywords):
    joined = " ".join(mapped_keywords).lower()

    if "food" in joined or "grocery" in joined:
        return ["food"]

    if "technology" in joined or "software" in joined:
        return ["technology"]

    if "health" in joined or "fitness" in joined:
        return ["health"]

    if "education" in joined:
        return ["education"]

    if "ecommerce" in joined or "retail" in joined:
        return ["shopping"]

    return ["business"]


def _build_result(score, direction, keywords, source, labels=None, values=None):
    monthly_labels = labels or []
    monthly_values = values or []

    if not monthly_labels or not monthly_values:
        monthly_labels, monthly_values = _build_estimated_monthly_series(keywords, score)

    return {
        "trend_score": float(round(score, 2)),
        "trend_direction": direction,
        "monthly_labels": monthly_labels,
        "monthly_interest": monthly_values,
        "source": source,
    }


def _extract_monthly_series(data, target_columns, fallback_keywords, fallback_score):
    target_series = data[target_columns].mean(axis=1)

    try:
        monthly_series = target_series.resample("ME").mean().tail(12)
    except Exception:
        monthly_series = target_series.resample("M").mean().tail(12)

    labels = [date.strftime("%b") for date in monthly_series.index]
    values = [round(float(value), 2) for value in monthly_series.tolist()]

    if not labels or not values:
        return _build_estimated_monthly_series(fallback_keywords, fallback_score)

    return labels, values


async def get_trend_analysis(keywords, location="IN"):
    if not keywords:
        return _build_result(35, "Baseline demand", keywords, "estimated")

    cache_key = generate_cache_key({
        "type": "trend_analysis",
        "keywords": keywords,
        "location": location,
    })

    cached = get_cache(cache_key)
    if cached:
        print("Cached Trend Analysis")
        return cached

    try:
        def fetch_trend_data():
            pytrends = TrendReq(
                hl="en-IN",
                tz=330,
                retries=2,
                backoff_factor=0.2,
            )

            mapped = map_to_trend_terms(keywords) or ["business"]
            mapped = _dedupe_terms(mapped)
            baseline = _dedupe_terms(get_baseline_keywords(mapped))

            mapped_keys = {item.lower() for item in mapped}
            baseline = [term for term in baseline if term.lower() not in mapped_keys]
            if not baseline:
                baseline = ["business"] if "business" not in mapped_keys else ["market"]

            kw_list = _dedupe_terms(mapped + baseline)[:5]

            pytrends.build_payload(
                kw_list=kw_list,
                timeframe="today 12-m",
                geo=location,
            )

            return pytrends.interest_over_time(), mapped, baseline

        data, target_keywords, baseline_keywords = await asyncio.to_thread(fetch_trend_data)

        if data.empty:
            result = _build_result(40, "Emerging / Low-volume demand", keywords, "estimated")
            set_cache(cache_key, result)
            return result

        if "isPartial" in data.columns:
            data = data.drop(columns=["isPartial"])

        target_columns = [keyword for keyword in target_keywords if keyword in data.columns]
        baseline_columns = [keyword for keyword in baseline_keywords if keyword in data.columns]

        if not target_columns or not baseline_columns:
            fallback = _build_result(38, "Baseline demand (fallback)", keywords, "estimated")
            set_cache(cache_key, fallback)
            return fallback

        target_avg = data[target_columns].mean().mean()
        baseline_avg = data[baseline_columns].mean().mean()

        if baseline_avg == 0:
            raw_score = 40
        else:
            raw_score = (target_avg / baseline_avg) * 100

        normalized_score = compute_trend_score(raw_score)

        if normalized_score > 70:
            direction = "High demand"
        elif normalized_score > 50:
            direction = "Moderate demand"
        elif normalized_score > 35:
            direction = "Growing demand"
        else:
            direction = "Niche demand"

        monthly_labels, monthly_values = _extract_monthly_series(
            data,
            target_columns,
            keywords,
            normalized_score,
        )

        result = _build_result(
            normalized_score,
            direction,
            keywords,
            "google_trends",
            monthly_labels,
            monthly_values,
        )
        set_cache(cache_key, result)
        return result

    except Exception as error:
        if "429" in str(error):
            print("Google Trends rate limited; using fallback trend data")
        else:
            print("Google Trends error:", error)

        fallback = _build_result(38, "Baseline demand (fallback)", keywords, "estimated")
        set_cache(cache_key, fallback)
        return fallback
