# app/services/market_size_service.py

import requests
import math
import asyncio


# --------------------------------------------------
# STATIC CITY POPULATION DATABASE
# --------------------------------------------------
CITY_POPULATION = {
    "Chennai": 7_000_000,
    "Coimbatore": 2_500_000,
    "Madurai": 1_500_000,
    "Trichy": 1_200_000,
    "Bangalore": 13_000_000,
    "Mumbai": 20_000_000,
    "Delhi": 19_000_000
}

INDIA_POPULATION = 1_420_000_000


# --------------------------------------------------
# INDUSTRY GDP FACTOR MAP
# --------------------------------------------------
INDUSTRY_FACTOR = {
    "EdTech": 0.02,
    "Fintech": 0.05,
    "Health": 0.04,
    "Ecommerce": 0.06,
    "AI": 0.03,
    "Food": 0.05,
    "Retail": 0.07,
    "Agriculture": 0.08,
    "Logistics": 0.04,
    "SaaS": 0.03
}


# --------------------------------------------------
# BLOCKING GDP FETCH (SYNC)
# --------------------------------------------------
def fetch_india_gdp_sync():

    try:
        url = "https://api.worldbank.org/v2/country/IN/indicator/NY.GDP.MKTP.CD?format=json"
        response = requests.get(url, timeout=8)
        res = response.json()

        if isinstance(res, list) and len(res) > 1:
            for entry in res[1]:
                if entry.get("value"):
                    return entry["value"]

    except Exception as e:
        print("GDP fetch error:", e)

    print("⚠️ Using estimated India GDP fallback")
    return 3_400_000_000_000  # fallback


# --------------------------------------------------
# BLOCKING MARKET CALCULATION
# --------------------------------------------------
def compute_market_size_sync(industry: str, location: str = None):

    gdp = fetch_india_gdp_sync()
    factor = INDUSTRY_FACTOR.get(industry, 0.04)

    national_tam = gdp * factor

    if location and location in CITY_POPULATION:
        city_pop = CITY_POPULATION[location]
    else:
        city_pop = 3_000_000

    population_ratio = city_pop / INDIA_POPULATION
    city_tam = national_tam * population_ratio

    adjusted_tam = math.log10(city_tam + 1) * 10_000_000

    sam = adjusted_tam * 0.30
    som = sam * 0.10

    return {
        "tam": round(adjusted_tam, 2),
        "sam": round(sam, 2),
        "som": round(som, 2)
    }


# --------------------------------------------------
# ASYNC WRAPPER (SAFE FOR FASTAPI)
# --------------------------------------------------
async def get_market_size(industry: str, location: str = None):

    try:
        return await asyncio.to_thread(
            compute_market_size_sync,
            industry,
            location
        )

    except Exception as e:
        print("Market size error:", e)

        base = 500_000_000
        return {
            "tam": base,
            "sam": base * 0.30,
            "som": base * 0.03
        }