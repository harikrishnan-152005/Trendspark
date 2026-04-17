# app/services/search_service.py

import os
from typing import Dict, List

from dotenv import load_dotenv
from serpapi import Client

from app.core.cache import generate_cache_key, get_cache, set_cache

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
MIN_COMPETITORS = 5


def _clean_query_terms(terms: List[str]) -> List[str]:
    cleaned = []
    seen = set()

    for term in terms:
        text = str(term).strip()
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(text)

    return cleaned


def _build_queries(
    keywords: List[str],
    idea_title: str = "",
    industry: str = "",
    target_audience: str = "",
) -> List[str]:
    cleaned_keywords = _clean_query_terms(keywords)

    queries = []
    if cleaned_keywords:
        queries.append(" OR ".join(cleaned_keywords[:3]))
        queries.extend(cleaned_keywords[:5])

    if idea_title:
        queries.append(idea_title)

    if industry and target_audience:
        queries.append(f"{industry} products for {target_audience}")

    if industry:
        queries.append(f"{industry} startups")
        queries.append(f"{industry} apps")

    return _clean_query_terms(queries)


def _dedupe_competitors(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    deduped = []
    seen = set()

    for item in items:
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        snippet = str(item.get("snippet", "")).strip()

        if not name and not url:
            continue

        key = (url or name).lower()
        if key in seen:
            continue

        seen.add(key)
        deduped.append({
            "name": name or "Unknown",
            "url": url or "#",
            "snippet": snippet,
        })

    return deduped


def get_competitor_search(
    keywords: List[str],
    location: str,
    idea_title: str = "",
    industry: str = "",
    target_audience: str = "",
) -> List[dict]:
    """
    Uses SerpAPI to fetch real Google competitors.
    Tries multiple related queries and keeps collecting until we have enough results.
    """
    query_list = _build_queries(keywords, idea_title, industry, target_audience)

    cache_key = generate_cache_key({
        "type": "competitor",
        "queries": query_list,
        "location": location,
    })

    cached = get_cache(cache_key)
    if cached:
        print("Cached Competitor Search")
        return cached

    if not SERPAPI_KEY or not query_list:
        print("SerpAPI key missing or no keywords")
        return []

    client = Client(api_key=SERPAPI_KEY)
    competitors: List[Dict[str, str]] = []

    base_params = {
        "engine": "google",
        "location": location,
        "hl": "en",
        "gl": "in",
        "api_key": SERPAPI_KEY,
    }

    try:
        for query in query_list:
            params = dict(base_params)
            params["q"] = query

            results = client.search(params).as_dict()
            for item in results.get("organic_results", [])[:8]:
                competitors.append({
                    "name": item.get("title", "Unknown"),
                    "url": item.get("link", "#"),
                    "snippet": item.get("snippet", ""),
                })

            competitors = _dedupe_competitors(competitors)
            if len(competitors) >= MIN_COMPETITORS:
                break

        print(f"SerpAPI found {len(competitors)} competitors")
        set_cache(cache_key, competitors)
        return competitors

    except Exception as e:
        print("SerpAPI error:", e)
        return []
