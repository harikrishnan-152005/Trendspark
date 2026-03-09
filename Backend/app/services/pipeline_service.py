# app/services/pipeline_service.py

import uuid
import asyncio
import time
from typing import List

from app.models.models import (
    IdeaInput,
    ValidationReport,
    SWOT,
    MarketAnalysis,
    Competitor,
    TrendAnalysis,
    MarketSize,
    RiskAnalysis,
    CompetitionAnalysis,
    ScoreBreakdown
)

from app.services.ai_service import generate_full_ai_report
from app.services.search_service import get_competitor_search
from app.services.trend_service import get_trend_analysis
from app.services.osmnx_service import get_competitor_density
from app.services.market_size_service import get_market_size
from app.services.chart_service import generate_score_chart
from app.database.database import save_report
from app.core.cache import generate_cache_key, get_cache, set_cache

from app.services.analytics_engine import (
    compute_trend_score,
    compute_market_strength,
    compute_competition_score,
    compute_risk_score,
    compute_final_score
)


# --------------------------------------------------
# DEBUG HELPER
# --------------------------------------------------
def log_step(step_name: str, status: str):
    print(f"[{step_name}] ➜ {status}")


async def run_validation_pipeline(
    idea: IdeaInput,
    user_id: str
) -> ValidationReport:
    pipeline_start = time.time()

    cache_key = generate_cache_key(idea.model_dump())
    cached_report = get_cache(cache_key)

    if cached_report:
        print("⚡ Returning cached validation result")
        return ValidationReport(**cached_report)
    idea_title = idea.title.strip() if idea.title else "Untitled Idea"

    print("\n" + "=" * 60)
    print(f"🚀 STARTING VALIDATION PIPELINE: {idea_title}")
    print("=" * 60)

    # --------------------------------------------------
    # STEP 1: AI ANALYSIS
    # --------------------------------------------------
    step_start = time.time()
    log_step("STEP 1 - AI ANALYSIS", "START")

    ai_data = generate_full_ai_report(idea)

    log_step("STEP 1 - AI ANALYSIS", "DONE")
    print(f"⏱ Duration: {round(time.time() - step_start, 2)} sec\n")

    swot_data = SWOT(**ai_data["swot_analysis"])
    market_analysis_data = MarketAnalysis(**ai_data["market_analysis"])
    ai_score = float(ai_data.get("overall_score", 5))
    executive_summary = ai_data.get("executive_summary", "")
    recommended_next_steps = ai_data.get("recommended_next_steps", [])

    # --------------------------------------------------
    # STEP 2: COMPETITOR SEARCH
    # --------------------------------------------------
    step_start = time.time()
    log_step("STEP 2 - COMPETITOR SEARCH", "START")

    competitor_data: List[Competitor] = get_competitor_search(
        market_analysis_data.potential_keywords,
        idea.location
    )

    log_step("STEP 2 - COMPETITOR SEARCH", "DONE")
    print(f"⏱ Duration: {round(time.time() - step_start, 2)} sec\n")

    # --------------------------------------------------
    # STEP 3-5: TREND | MARKET | COMPETITION (PARALLEL)
    # --------------------------------------------------
    print("[STEP 3-5 - TREND | MARKET | COMPETITION] ➜ START")

    trend_raw, competition_raw, market_raw = await asyncio.gather(
        get_trend_analysis(
            market_analysis_data.potential_keywords,
            "IN-TN"
        ),
        asyncio.to_thread(
            get_competitor_density,
            idea.industry or "business",
            idea.location
        ),
        get_market_size(
            idea.industry or "",
            idea.location
        )
    )

    print("[STEP 3-5 - TREND | MARKET | COMPETITION] ➜ DONE\n")

    # --------------------------------------------------
    # STEP 6: SCORING ENGINE
    # --------------------------------------------------
    step_start = time.time()
    log_step("STEP 6 - SCORING ENGINE", "START")

    trend_score = compute_trend_score(
        trend_raw.get("trend_score", 35)
    )

    market_strength = compute_market_strength(
        market_raw.get("tam", 0)
    )

    competition_score = compute_competition_score(
        competition_raw.get("competitor_count", 0)
    )

    risk_score = compute_risk_score(
        ai_score,
        trend_score,
        competition_score
    )

    risk_level = (
        "Low Risk" if risk_score < 4
        else "Medium Risk" if risk_score < 7
        else "High Risk"
    )

    risk_data = RiskAnalysis(
        risk_score=risk_score,
        risk_level=risk_level
    )

    final_score = compute_final_score(
        ai_score,
        trend_score,
        market_strength,
        competition_score,
        risk_score
    )

    score_components = ScoreBreakdown(
    ai_score=round(ai_score, 2),
    trend_score=round(trend_score, 2),
    market_strength=round(market_strength, 2),
    competition_score=round(competition_score, 2),
    risk_score=round(risk_score, 2)
    )
    
    log_step("STEP 6 - SCORING ENGINE", "DONE")
    print(f"⏱ Duration: {round(time.time() - step_start, 2)} sec\n")

    # --------------------------------------------------
    # STEP 7: CHART GENERATION
    # --------------------------------------------------
    step_start = time.time()
    log_step("STEP 7 - CHART GENERATION", "START")

    chart_path = generate_score_chart(
        final_score,
        trend_score
    )

    log_step("STEP 7 - CHART GENERATION", "DONE")
    print(f"⏱ Duration: {round(time.time() - step_start, 2)} sec\n")

    # --------------------------------------------------
    # STEP 8: BUILD REPORT
    # --------------------------------------------------
    log_step("STEP 8 - BUILD REPORT", "START")

    report = ValidationReport(
        report_id=str(uuid.uuid4()),
        idea_name=idea_title,
        overall_score=final_score,
        executive_summary=executive_summary,
        swot_analysis=swot_data,
        market_analysis=market_analysis_data,
        competitor_analysis=competitor_data,
        trend_analysis=TrendAnalysis(**trend_raw),
        market_size=MarketSize(**market_raw),
        risk_analysis=risk_data,
        competition_analysis=CompetitionAnalysis(**competition_raw),
        chart_url=chart_path,
        recommended_next_steps=recommended_next_steps,
        score_components=score_components  # 🔥 NEW
    )

    log_step("STEP 8 - BUILD REPORT", "DONE")

    # --------------------------------------------------
    # STEP 9: SAVE + CACHE
    # --------------------------------------------------
    log_step("STEP 9 - SAVE + CACHE", "START")

    save_report(report,user_id)
    set_cache(cache_key, report.model_dump())

    log_step("STEP 9 - SAVE + CACHE", "DONE")

    print("\n" + "=" * 60)
    print(f"✅ PIPELINE COMPLETED in {round(time.time() - pipeline_start, 2)} sec")
    print("=" * 60 + "\n")

    return report