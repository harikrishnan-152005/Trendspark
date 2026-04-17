import osmnx as ox


INDUSTRY_TAGS = {
    "edtech": {"amenity": "school"},
    "education": {"amenity": "school"},
    "health": {"amenity": "hospital"},
    "healthtech": {"amenity": "hospital"},
    "wellness": {"amenity": "hospital"},
    "ecommerce": {"shop": True},
    "retail": {"shop": True},
    "fintech": {"office": "financial"},
    "finance": {"office": "financial"},
    "banking": {"office": "financial"},
    "ai": {"office": True},
    "saas": {"office": True},
    "technology": {"office": True},
}


def _resolve_tags(industry: str):
    normalized_industry = str(industry or "").strip().lower()

    for key, value in INDUSTRY_TAGS.items():
        if key in normalized_industry:
            return value

    return {"office": True}


def get_competitor_density(industry: str, location=str):
    try:
        if hasattr(ox, "settings"):
            ox.settings.requests_timeout = 10

        tags = _resolve_tags(industry)
        gdf = ox.features_from_place(location, tags)

        if gdf is None or len(gdf) == 0:
            return {
                "competitor_count": 0,
                "competition_level": "Low",
            }

        count = len(gdf)

        if count > 300:
            level = "Very High"
        elif count > 150:
            level = "High"
        elif count > 50:
            level = "Medium"
        else:
            level = "Low"

        return {
            "competitor_count": count,
            "competition_level": level,
        }

    except Exception as error:
        print("OSMnx Error:", error)
        return {
            "competitor_count": 0,
            "competition_level": "Unknown",
        }
