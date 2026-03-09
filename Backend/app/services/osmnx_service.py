import osmnx as ox

def get_competitor_density(industry: str, location= str):
    try:
        industry_tags = {
        "EdTech": {"amenity": "school"},
        "Health": {"amenity": "hospital"},
        "Ecommerce": {"shop": True},
        "Fintech": {"office": "financial"},
        "AI": {"office": True}
    }

        tags = industry_tags.get(industry, {"shop": True})

        gdf = ox.features_from_place(location, tags)

        if gdf is None or len(gdf) == 0:
            return {
                "competitor_count": 0,
                "competition_level": "Low"
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
            "competition_level": level
        }

    except Exception as e:
        print("OSMnx Error:", e)
        return {
            "competitor_count": 0,
            "competition_level": "Unknown"
        }