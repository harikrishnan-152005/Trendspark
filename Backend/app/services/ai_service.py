# app/services/ai_service.py

import json
import re
from typing import Any, Dict, List, Optional

from app.services.model_manager import generate_ai
from app.models.models import IdeaInput
from app.core.cache import generate_cache_key, get_cache, set_cache

MIN_SWOT_POINTS = 5
MIN_KEYWORDS = 5
STOP_WORDS = {
    "a", "an", "and", "app", "business", "for", "from", "in", "into",
    "of", "on", "or", "platform", "service", "startup", "the", "to", "with"
}
SWOT_SECTIONS = ("strengths", "weaknesses", "opportunities", "threats")


def safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    if not text or not isinstance(text, str):
        return None

    cleaned = re.sub(
        r"^(?:\s*```(?:json)?\s*|\s*```)\s*|\s*(?:```(?:json)?\s*|\s*```)\s*$",
        "",
        text.strip(),
        flags=re.MULTILINE | re.IGNORECASE,
    )

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
        return None
    except Exception as e:
        print("JSON parsing error:", e)
        return None


def _clean_text_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    cleaned = []
    seen = set()

    for item in value:
        text = str(item).strip()
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(text)

    return cleaned


def _keyword_fallbacks(idea: IdeaInput) -> List[str]:
    candidates: List[str] = []

    def add_candidate(text: str):
        cleaned = text.strip().lower()
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)

    if idea.title:
        title_tokens = [
            token.lower()
            for token in re.findall(r"[A-Za-z][A-Za-z0-9+-]{2,}", idea.title)
            if token.lower() not in STOP_WORDS
        ]
        for token in title_tokens:
            add_candidate(token)

    if idea.industry:
        add_candidate(idea.industry)

    if idea.target_audience:
        add_candidate(idea.target_audience)

    if idea.description:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9+-]{3,}", idea.description):
            lowered = token.lower()
            if lowered in STOP_WORDS:
                continue
            add_candidate(lowered)

    return candidates[:MIN_KEYWORDS]


def normalize_structure(data: Dict[str, Any], idea: Optional[IdeaInput] = None) -> Dict[str, Any]:
    data.setdefault("swot_analysis", {})
    for section in SWOT_SECTIONS:
        data["swot_analysis"][section] = _clean_text_list(
            data["swot_analysis"].get(section, [])
        )

    data.setdefault("market_analysis", {})
    audience_profile = data["market_analysis"].get("audience_profile", "")
    data["market_analysis"]["audience_profile"] = str(audience_profile).strip()

    keywords = _clean_text_list(data["market_analysis"].get("potential_keywords", []))
    if idea and len(keywords) < MIN_KEYWORDS:
        for keyword in _keyword_fallbacks(idea):
            if keyword not in {item.lower() for item in keywords}:
                keywords.append(keyword)
            if len(keywords) >= MIN_KEYWORDS:
                break
    data["market_analysis"]["potential_keywords"] = keywords

    data["executive_summary"] = str(data.get("executive_summary", "")).strip()
    data["recommended_next_steps"] = _clean_text_list(data.get("recommended_next_steps", []))

    try:
        data["overall_score"] = float(data.get("overall_score", 5))
    except Exception:
        data["overall_score"] = 5.0

    return data


def _expand_swot_if_needed(idea: IdeaInput, data: Dict[str, Any]) -> Dict[str, Any]:
    if all(len(data["swot_analysis"][section]) >= MIN_SWOT_POINTS for section in SWOT_SECTIONS):
        return data

    current_swot = {
        section: data["swot_analysis"].get(section, [])
        for section in SWOT_SECTIONS
    }

    prompt = f"""
You are an experienced startup investor and market analyst.

Expand the SWOT analysis for this startup idea.

Title: {idea.title}
Description: {idea.description}
Industry: {idea.industry or "Not specified"}
Target Audience: {idea.target_audience or "Not specified"}

Current SWOT:
{json.dumps(current_swot, ensure_ascii=True)}

Rules:
- Return ONLY valid JSON
- No markdown
- No explanations
- Keep existing useful points
- Each SWOT section must have at least 5 concise, specific, non-overlapping points

Return EXACTLY:
{{
  "swot_analysis": {{
    "strengths": ["", "", "", "", ""],
    "weaknesses": ["", "", "", "", ""],
    "opportunities": ["", "", "", "", ""],
    "threats": ["", "", "", "", ""]
  }}
}}
"""

    response_text = generate_ai(prompt)
    expanded = safe_json_parse(response_text) if response_text else None

    if not expanded or not isinstance(expanded.get("swot_analysis"), dict):
        return data

    for section in SWOT_SECTIONS:
        merged = list(data["swot_analysis"].get(section, []))
        existing_lower = {item.lower() for item in merged}

        for item in _clean_text_list(expanded["swot_analysis"].get(section, [])):
            if item.lower() in existing_lower:
                continue
            merged.append(item)
            existing_lower.add(item.lower())

        data["swot_analysis"][section] = merged

    return data


def fallback_structure(cache_key: str) -> Dict[str, Any]:
    fallback = {
        "swot_analysis": {
            "strengths": ["AI temporarily unavailable"],
            "weaknesses": [],
            "opportunities": [],
            "threats": [],
        },
        "market_analysis": {
            "audience_profile": "Unavailable",
            "potential_keywords": [],
        },
        "executive_summary": "AI service temporarily unavailable.",
        "overall_score": 5.0,
        "recommended_next_steps": [
            "Retry later",
            "Validate manually",
        ],
    }

    set_cache(cache_key, fallback)
    return fallback


def generate_full_ai_report(idea: IdeaInput) -> Dict[str, Any]:
    cache_key = generate_cache_key({
        "type": "full_ai_report",
        "idea": idea.model_dump(),
    })

    cached = get_cache(cache_key)
    if cached:
        print("Cached Full AI Report")
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
- Each SWOT section must contain at least 5 concise, specific points
- potential_keywords must contain at least 5 relevant search keywords
- recommended_next_steps should contain at least 3 items

Return EXACTLY this structure:

{{
  "swot_analysis": {{
      "strengths": ["", "", "", "", ""],
      "weaknesses": ["", "", "", "", ""],
      "opportunities": ["", "", "", "", ""],
      "threats": ["", "", "", "", ""]
  }},
  "market_analysis": {{
      "audience_profile": "",
      "potential_keywords": ["", "", "", "", ""]
  }},
  "executive_summary": "",
  "overall_score": 0.0,
  "recommended_next_steps": ["", "", ""]
}}
"""

    for attempt in range(2):
        print(f"Gemini attempt {attempt + 1}")

        response_text = generate_ai(prompt)
        if not response_text:
            print("Empty AI response")
            continue

        print("\nRAW AI RESPONSE:\n")
        print(response_text)
        print("\n---------------------------------\n")

        data = safe_json_parse(response_text)
        if not data:
            print("JSON parsing failed")
            continue

        data = normalize_structure(data, idea)
        data = _expand_swot_if_needed(idea, data)
        data = normalize_structure(data, idea)

        set_cache(cache_key, data)
        return data

    print("AI failed after retries - using fallback")
    return fallback_structure(cache_key)
