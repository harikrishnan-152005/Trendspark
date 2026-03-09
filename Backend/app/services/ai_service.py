# app/services/ai_service.py

import json
import re
import time
from typing import Dict, Any, Optional

from app.services.model_manager import generate_ai
from app.models.models import IdeaInput
from app.core.cache import generate_cache_key, get_cache, set_cache


# =================================================
# SAFE JSON PARSER
# =================================================
def safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    if not text or not isinstance(text, str):
        return None

    cleaned = re.sub(
        r'^(?:\s*```(?:json)?\s*|\s*```)\s*|\s*(?:```(?:json)?\s*|\s*```)\s*$',
        '',
        text.strip(),
        flags=re.MULTILINE | re.IGNORECASE
    )

    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
        return None
    except Exception as e:
        print("❌ JSON parsing error:", e)
        return None


# =================================================
# STRUCTURE AUTO-REPAIR
# =================================================
def normalize_structure(data: Dict[str, Any]) -> Dict[str, Any]:

    data.setdefault("swot_analysis", {})
    data["swot_analysis"].setdefault("strengths", [])
    data["swot_analysis"].setdefault("weaknesses", [])
    data["swot_analysis"].setdefault("opportunities", [])
    data["swot_analysis"].setdefault("threats", [])

    data.setdefault("market_analysis", {})
    data["market_analysis"].setdefault("audience_profile", "")
    data["market_analysis"].setdefault("potential_keywords", [])

    data.setdefault("executive_summary", "")
    data.setdefault("recommended_next_steps", [])

    try:
        data["overall_score"] = float(data.get("overall_score", 5))
    except:
        data["overall_score"] = 5.0

    # Ensure keywords list
    if not isinstance(data["market_analysis"]["potential_keywords"], list):
        data["market_analysis"]["potential_keywords"] = []

    return data


# =================================================
# FALLBACK STRUCTURE
# =================================================
def fallback_structure(cache_key: str) -> Dict[str, Any]:

    fallback = {
        "swot_analysis": {
            "strengths": ["AI temporarily unavailable"],
            "weaknesses": [],
            "opportunities": [],
            "threats": []
        },
        "market_analysis": {
            "audience_profile": "Unavailable",
            "potential_keywords": []
        },
        "executive_summary": "AI service temporarily unavailable.",
        "overall_score": 5.0,
        "recommended_next_steps": [
            "Retry later",
            "Validate manually"
        ]
    }

    set_cache(cache_key, fallback)
    return fallback


# =================================================
# FULL AI REPORT (PRODUCTION VERSION)
# =================================================
def generate_full_ai_report(idea: IdeaInput) -> Dict[str, Any]:

    cache_key = generate_cache_key({
        "type": "full_ai_report",
        "idea": idea.model_dump()
    })

    cached = get_cache(cache_key)
    if cached:
        print("⚡ Cached Full AI Report")
        return cached

    prompt = f"""
You are an experienced startup investor and market analyst.

Analyze the startup idea below carefully.

Title: {idea.title}
Description: {idea.description}
Industry: {idea.industry or "Not specified"}
Target Audience: {idea.target_audience or "Not specified"}

STRICT RULES:
- Return ONLY valid JSON
- No markdown
- No explanations
- No extra text
- Response MUST start with {{ and end with }}
- All keys must exist
- overall_score must be a number between 0 and 10

Return EXACTLY this structure:

{{
  "swot_analysis": {{
      "strengths": [],
      "weaknesses": [],
      "opportunities": [],
      "threats": []
  }},
  "market_analysis": {{
      "audience_profile": "",
      "potential_keywords": []
  }},
  "executive_summary": "",
  "overall_score": 0.0,
  "recommended_next_steps": []
}}
"""

    max_retries = 2

    for attempt in range(max_retries):

        print(f"🤖 Gemini attempt {attempt + 1}")

        response_text = generate_ai(prompt)

        if not response_text:
            print("⚠ Empty AI response")
            continue

        print("\n🔎 RAW AI RESPONSE:\n")
        print(response_text)
        print("\n---------------------------------\n")

        data = safe_json_parse(response_text)

        if not data:
            print("❌ JSON parsing failed")
            continue

        data = normalize_structure(data)

        set_cache(cache_key, data)
        return data

        time.sleep(1)

    print("🚨 AI failed after retries — using fallback")
    return fallback_structure(cache_key)