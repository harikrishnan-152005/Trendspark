# app/services/search_service.py

import os
from typing import List
from dotenv import load_dotenv
from serpapi import GoogleSearch

from app.models.models import Competitor
from app.core.cache import generate_cache_key, get_cache, set_cache

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
print("Loaded SERPAPI_KEY:", SERPAPI_KEY)


def get_competitor_search(keywords: List[str], location: str) -> List[Competitor]:
    """
    Uses SerpAPI to fetch real Google competitors
    """
    cache_key = generate_cache_key({
        "type": "competitor",
        "keywords": keywords,
        "location": location
    })

    cached = get_cache(cache_key)
    if cached:
        print("⚡ Cached Competitor Search")
        return cached


    if not SERPAPI_KEY or not keywords:
        print("SerpAPI key missing or no keywords")
        return []

    query = " OR ".join(keywords[:3])

    params = {
        "engine": "google",
        "q": query,
        "location": location,
        "hl": "en",
        "gl": "in",
        "api_key": SERPAPI_KEY
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        competitors = []

        for item in results.get("organic_results", [])[:6]:
            competitors.append(
                Competitor(
                    name=item.get("title", "Unknown"),
                    url=item.get("link", "#"),
                    snippet=item.get("snippet", "")
                )
            )

        print(f"SerpAPI found {len(competitors)} competitors")
        set_cache(cache_key, competitors)
        return competitors

    except Exception as e:
        print("SerpAPI error:", e)
        return []