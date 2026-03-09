from pytrends.request import TrendReq
from app.core.cache import generate_cache_key, get_cache, set_cache
from app.services.analytics_engine import compute_trend_score
import asyncio


# --------------------------------------------------
# 🔹 Map Startup Idea → Broad Trend Terms
# --------------------------------------------------
def map_to_trend_terms(keywords):

    text = " ".join(keywords).lower()

    # 🍎 Food / Grocery / Agriculture
    if any(x in text for x in ["food", "organic", "vegetable", "rice", "millet", "farm"]):
        return ["organic food", "vegetables", "grocery"]

    # 💻 Tech / AI / Software
    if any(x in text for x in ["tech", "ai", "software", "app", "saas"]):
        return ["technology", "software", "startup"]

    # 🏥 Health / Fitness
    if any(x in text for x in ["health", "fitness", "medical", "wellness"]):
        return ["health", "fitness", "wellness"]

    # 🛒 Ecommerce / Retail
    if any(x in text for x in ["shop", "store", "marketplace", "delivery", "commerce"]):
        return ["ecommerce", "online shopping", "retail"]

    # 🎓 Education
    if any(x in text for x in ["education", "learning", "course", "school", "edtech"]):
        return ["education", "online learning"]

    # Default fallback
    return ["business", "startup"]


# --------------------------------------------------
# 🔹 Industry Baseline Selector
# --------------------------------------------------
def get_baseline_keywords(mapped_keywords):

    joined = " ".join(mapped_keywords)

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


# --------------------------------------------------
# 🔹 Main Async Function
# --------------------------------------------------
async def get_trend_analysis(keywords, location="IN"):

    # ------------------------------------------
    # 🔹 No Keywords Case
    # ------------------------------------------
    if not keywords:
        return {
            "trend_score": 35,
            "trend_direction": "Baseline demand"
        }

    cache_key = generate_cache_key({
        "type": "trend_analysis",
        "keywords": keywords,
        "location": location
    })

    cached = get_cache(cache_key)
    if cached:
        print("⚡ Cached Trend Analysis")
        return cached

    try:
        # ------------------------------------------
        # 🔥 Blocking Google Trends Call
        # ------------------------------------------
        def fetch_trend_data():

            pytrends = TrendReq(
                hl="en-IN",
                tz=330,
                retries=2,
                backoff_factor=0.2
            )

            # ⭐ Convert idea → category terms
            mapped = map_to_trend_terms(keywords)

            if not mapped:
                mapped = ["business"]

            baseline = get_baseline_keywords(mapped)

            kw_list = mapped + baseline

            # Google limit safeguard
            kw_list = kw_list[:5]

            pytrends.build_payload(
                kw_list=kw_list,
                timeframe="today 12-m",  # more stable
                geo=location
            )

            data = pytrends.interest_over_time()

            return data, mapped, baseline

        # Run blocking code in thread
        data, target_keywords, baseline_keywords = await asyncio.to_thread(fetch_trend_data)

        # ------------------------------------------
        # 🔹 No Data Case
        # ------------------------------------------
        if data.empty:
            result = {
                "trend_score": 40,
                "trend_direction": "Emerging / Low-volume demand"
            }
            set_cache(cache_key, result)
            return result

        if "isPartial" in data.columns:
            data = data.drop(columns=["isPartial"])

        target_avg = data[target_keywords].mean().mean()
        baseline_avg = data[baseline_keywords].mean().mean()

        # ------------------------------------------
        # 🔹 Score Calculation
        # ------------------------------------------
        if baseline_avg == 0:
            raw_score = 40
        else:
            raw_score = (target_avg / baseline_avg) * 100

        normalized_score = compute_trend_score(raw_score)

        # ------------------------------------------
        # 🔹 Demand Classification
        # ------------------------------------------
        if normalized_score > 70:
            direction = "High demand"
        elif normalized_score > 50:
            direction = "Moderate demand"
        elif normalized_score > 35:
            direction = "Growing demand"
        else:
            direction = "Niche demand"

        result = {
            "trend_score": float(round(normalized_score, 2)),
            "trend_direction": direction
        }

        set_cache(cache_key, result)
        return result

    except Exception as e:
        print("Google Trends error:", e)

        # ------------------------------------------
        # 🔥 Smart Fallback
        # ------------------------------------------
        fallback = {
            "trend_score": 38,
            "trend_direction": "Baseline demand (fallback)"
        }

        set_cache(cache_key, fallback)
        return fallback