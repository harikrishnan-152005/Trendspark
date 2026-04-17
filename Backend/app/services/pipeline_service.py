# app/services/pipeline_service.py

import asyncio
import time
import uuid
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from app.core.cache import generate_cache_key, get_cache, set_cache
from app.database.database import save_report
from app.models.models import (
    CompetitionAnalysis,
    Competitor,
    IdeaInput,
    MarketAnalysis,
    MarketSize,
    RiskAnalysis,
    SWOT,
    ScoreBreakdown,
    TrendAnalysis,
    ValidationReport,
)
from app.services.ai_service import generate_full_ai_report
from app.services.analytics_engine import (
    compute_competition_score,
    compute_final_score,
    compute_market_strength,
    compute_risk_score,
    compute_trend_score,
)
from app.services.chart_service import (
    generate_competition_chart,
    generate_score_chart,
    generate_trend_chart,
)
from app.services.market_size_service import get_market_size
from app.services.osmnx_service import get_competitor_density
from app.services.search_service import get_competitor_search
from app.services.trend_service import get_trend_analysis

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPORTS_DIR = BACKEND_DIR / "reports"
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _chunk_list(values, size):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def _clamp_value(value, minimum, maximum):
    return min(max(float(value), minimum), maximum)


def _round_value(value):
    return round(float(value), 1)


def _hash_text(text):
    return sum(ord(char) for char in str(text or ""))


def _format_currency(value):
    return f"Rs. {float(value):,.2f}"


def _format_count(value):
    return f"{int(round(float(value or 0))):,}"


def _shorten_label(label, limit=18):
    text = str(label or "Unknown").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit - 1]}..."


def _extract_host(url):
    try:
        host = urlparse(str(url or "")).netloc.replace("www.", "")
        return host or "Link unavailable"
    except Exception:
        return "Link unavailable"


def _get_trend_series(report):
    labels = list(report.trend_analysis.monthly_labels or [])
    values = list(report.trend_analysis.monthly_interest or [])

    if len(labels) >= 6 and len(labels) == len(values):
        return {
            "labels": labels,
            "values": [_round_value(value) for value in values],
            "source": report.trend_analysis.source or "google_trends",
            "direction": report.trend_analysis.trend_direction or "Stable demand",
        }

    import math

    base_score = _clamp_value(report.trend_analysis.trend_score or 38, 20, 90)
    seed = _hash_text(f"{report.idea_name}{report.trend_analysis.trend_direction}")
    estimated_values = []

    for index, _label in enumerate(MONTH_LABELS):
        seasonal = math.sin(((index + (seed % 4)) / 12) * math.pi * 2) * 5.4
        momentum = ((index - 5.5) / 5.5) * ((seed % 5) + 1) * 0.7
        pulse = (((seed + index * 11) % 9) - 4) * 0.45
        estimated_values.append(
            _round_value(_clamp_value(base_score + seasonal + momentum + pulse, 18, 96))
        )

    return {
        "labels": MONTH_LABELS,
        "values": estimated_values,
        "source": "estimated",
        "direction": report.trend_analysis.trend_direction or "Baseline demand",
    }


def _get_average(values):
    if not values:
        return 0
    return _round_value(sum(values) / len(values))


def _get_trend_extremes(labels, values):
    if not labels or not values:
        return {
            "peak": {"label": "-", "value": 0},
            "low": {"label": "-", "value": 0},
        }

    peak_index = max(range(len(values)), key=lambda index: values[index])
    low_index = min(range(len(values)), key=lambda index: values[index])

    return {
        "peak": {"label": labels[peak_index], "value": values[peak_index]},
        "low": {"label": labels[low_index], "value": values[low_index]},
    }


def _get_trend_momentum(values):
    if len(values) < 2:
        return {"delta": 0, "label": "Demand remained steady"}

    delta = _round_value(values[-1] - values[0])

    if delta >= 6:
        return {"delta": delta, "label": "Strong upward momentum"}
    if delta >= 2:
        return {"delta": delta, "label": "Healthy upward momentum"}
    if delta <= -6:
        return {"delta": delta, "label": "Demand softened over time"}
    if delta <= -2:
        return {"delta": delta, "label": "Slight cooling trend"}

    return {"delta": delta, "label": "Demand remained steady"}


def _build_competitor_signals(competitors):
    signals = []

    for index, competitor in enumerate((competitors or [])[:5]):
        snippet_word_count = len(str(competitor.snippet or "").split())
        visibility = _round_value(
            _clamp_value(94 - (index * 11.5) + min(snippet_word_count * 0.35, 6), 38, 96)
        )
        signals.append({
            "label": _shorten_label(competitor.name, 24),
            "host": _extract_host(competitor.url),
            "visibility": visibility,
        })

    return signals


def generate_pdf(report):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import (
            Image,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        print("reportlab is not installed; skipping PDF generation")
        return None

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = REPORTS_DIR / f"{report.report_id}.pdf"

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=42,
        bottomMargin=28,
    )

    palette = {
        "page": "#020617",
        "panel": "#0f172a",
        "panel_alt": "#111827",
        "border": "#1e293b",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "title": "#f8fafc",
        "indigo": "#818cf8",
        "cyan": "#38bdf8",
        "rose": "#fb7185",
        "orange": "#f97316",
        "amber": "#f59e0b",
        "green": "#22c55e",
        "purple": "#c084fc",
    }

    base_styles = getSampleStyleSheet()
    styles = {
        "eyebrow": ParagraphStyle(
            "PdfEyebrow",
            parent=base_styles["Normal"],
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor(palette["muted"]),
            fontName="Helvetica-Bold",
        ),
        "hero_title": ParagraphStyle(
            "PdfHeroTitle",
            parent=base_styles["Title"],
            fontSize=25,
            leading=30,
            textColor=colors.HexColor(palette["title"]),
        ),
        "section_title": ParagraphStyle(
            "PdfSectionTitle",
            parent=base_styles["Heading2"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor(palette["title"]),
            spaceAfter=8,
        ),
        "card_title": ParagraphStyle(
            "PdfCardTitle",
            parent=base_styles["Heading3"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor(palette["title"]),
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "PdfBody",
            parent=base_styles["BodyText"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor(palette["text"]),
        ),
        "muted": ParagraphStyle(
            "PdfMuted",
            parent=base_styles["BodyText"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor(palette["muted"]),
        ),
        "small": ParagraphStyle(
            "PdfSmall",
            parent=base_styles["BodyText"],
            fontSize=8.6,
            leading=11,
            textColor=colors.HexColor(palette["text"]),
        ),
        "metric": ParagraphStyle(
            "PdfMetric",
            parent=base_styles["Heading2"],
            fontSize=15,
            leading=18,
            textColor=colors.HexColor(palette["title"]),
        ),
        "bullet": ParagraphStyle(
            "PdfBullet",
            parent=base_styles["BodyText"],
            fontSize=8.9,
            leading=12,
            textColor=colors.HexColor(palette["text"]),
        ),
    }

    card_gap = 12
    two_col_width = (doc.width - card_gap) / 2
    three_col_width = (doc.width - (card_gap * 2)) / 3
    four_col_width = (doc.width - (card_gap * 3)) / 4

    trend_series = _get_trend_series(report)
    trend_labels = trend_series["labels"]
    trend_values = trend_series["values"]
    trend_average = _get_average(trend_values)
    trend_extremes = _get_trend_extremes(trend_labels, trend_values)
    trend_momentum = _get_trend_momentum(trend_values)
    competitor_signals = _build_competitor_signals(report.competitor_analysis)

    temp_assets = []
    trend_chart_path = generate_trend_chart(report.report_id, trend_labels, trend_values)
    if trend_chart_path:
        temp_assets.append(Path(trend_chart_path))

    competition_chart_path = generate_competition_chart(
        report.report_id,
        [signal["label"] for signal in competitor_signals],
        [signal["visibility"] for signal in competitor_signals],
    )
    if competition_chart_path:
        temp_assets.append(Path(competition_chart_path))

    score_chart_path = report.chart_url if report.chart_url and Path(report.chart_url).is_file() else None
    if not score_chart_path:
        score_chart_path = generate_score_chart(report.overall_score, report.score_components.trend_score)

    def page_theme(canvas, _doc):
        page_width, page_height = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(palette["page"]))
        canvas.rect(0, 0, page_width, page_height, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor(palette["muted"]))
        canvas.setFont("Helvetica", 9)
        canvas.drawString(_doc.leftMargin, 16, "TrendSpark AI Report")
        canvas.drawRightString(page_width - _doc.rightMargin, 16, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    def build_card(flowables, width, background=None, border=None, padding=12):
        table = Table([[flowables]], colWidths=[width])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(background or palette["panel"])),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(border or palette["border"])),
            ("LEFTPADDING", (0, 0), (-1, -1), padding),
            ("RIGHTPADDING", (0, 0), (-1, -1), padding),
            ("TOPPADDING", (0, 0), (-1, -1), padding),
            ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return table

    def build_row(items, widths):
        row = Table([items], colWidths=widths)
        row.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return row

    def build_stat_card(label, value, width, accent, note=""):
        body = [
            Paragraph(label.upper(), styles["eyebrow"]),
            Spacer(1, 4),
            Paragraph(f'<font color="{accent}">{value}</font>', styles["metric"]),
        ]
        if note:
            body.extend([Spacer(1, 4), Paragraph(note, styles["muted"])])
        return build_card(body, width)

    def build_text_card(title, paragraphs, width):
        body = [Paragraph(title, styles["card_title"])]
        for paragraph in paragraphs:
            if paragraph:
                body.extend([Spacer(1, 4), Paragraph(paragraph, styles["body"])])
        return build_card(body, width)

    def build_swot_card(title, items, width):
        body = [Paragraph(title, styles["card_title"])]
        for item in items:
            body.extend([Spacer(1, 5), Paragraph(f"- {item}", styles["bullet"])])
        return build_card(body, width)

    def build_month_card(label, value, delta_text, width):
        body = [
            Paragraph(label.upper(), styles["eyebrow"]),
            Spacer(1, 4),
            Paragraph(str(value), styles["metric"]),
            Spacer(1, 4),
            Paragraph(delta_text, styles["muted"]),
        ]
        return build_card(body, width, background=palette["panel_alt"])

    def build_competitor_card(competitor, index, width):
        body = [
            Paragraph(f"#{index + 1} {competitor.name}", styles["card_title"]),
            Spacer(1, 4),
            Paragraph(_extract_host(competitor.url), styles["muted"]),
            Spacer(1, 6),
            Paragraph(competitor.snippet or "No summary available for this competitor.", styles["body"]),
        ]
        if competitor.url:
            body.extend([Spacer(1, 6), Paragraph(competitor.url, styles["small"])])
        return build_card(body, width)

    content = []

    hero = build_card(
        [
            Paragraph("VALIDATION SNAPSHOT", styles["eyebrow"]),
            Spacer(1, 8),
            Paragraph(report.idea_name, styles["hero_title"]),
            Spacer(1, 8),
            Paragraph(
                f'<font color="{palette["indigo"]}">Overall Score: {report.overall_score} / 10</font>',
                styles["metric"],
            ),
            Spacer(1, 10),
            Paragraph(report.executive_summary, styles["body"]),
        ],
        doc.width,
        background="#111827",
        border="#312e81",
        padding=18,
    )
    content.extend([hero, Spacer(1, 12)])

    snapshot_cards = [
        build_stat_card("Trend direction", trend_series["direction"], two_col_width, palette["cyan"]),
        build_stat_card("Competition level", report.competition_analysis.competition_level, two_col_width, palette["orange"]),
        build_stat_card("Risk level", report.risk_analysis.risk_level, two_col_width, palette["rose"]),
        build_stat_card("Top competitors", str(len(report.competitor_analysis)), two_col_width, palette["green"]),
    ]
    content.append(build_row(snapshot_cards[:2], [two_col_width, two_col_width]))
    content.extend([Spacer(1, 12), build_row(snapshot_cards[2:], [two_col_width, two_col_width]), Spacer(1, 12)])

    audience_card = build_text_card("Audience Profile", [report.market_analysis.audience_profile], two_col_width)
    keyword_card = build_text_card(
        "Potential Keywords",
        [", ".join(report.market_analysis.potential_keywords)] if report.market_analysis.potential_keywords else ["No keywords generated"],
        two_col_width,
    )
    content.extend([build_row([audience_card, keyword_card], [two_col_width, two_col_width]), PageBreak()])

    content.extend([Paragraph("Score And Market Snapshot", styles["section_title"]), Spacer(1, 4)])
    if score_chart_path and Path(score_chart_path).is_file():
        content.extend([
            build_card(
                [
                    Image(str(score_chart_path), width=doc.width - 24, height=185),
                    Spacer(1, 6),
                    Paragraph("Overall viability and normalized demand snapshot.", styles["muted"]),
                ],
                doc.width,
            ),
            Spacer(1, 12),
        ])

    score_cards = [
        build_stat_card("AI score", f"{report.score_components.ai_score}", three_col_width, palette["indigo"]),
        build_stat_card("Demand score", f"{report.score_components.trend_score}", three_col_width, palette["cyan"]),
        build_stat_card("Market strength", f"{report.score_components.market_strength}", three_col_width, palette["green"]),
        build_stat_card("Competition score", f"{report.score_components.competition_score}", two_col_width, palette["amber"]),
        build_stat_card("Risk score", f"{report.score_components.risk_score}", two_col_width, palette["rose"]),
    ]
    content.append(build_row(score_cards[:3], [three_col_width, three_col_width, three_col_width]))
    content.extend([Spacer(1, 12), build_row(score_cards[3:], [two_col_width, two_col_width]), Spacer(1, 12)])

    market_cards = [
        build_stat_card("TAM", _format_currency(report.market_size.tam), three_col_width, palette["title"]),
        build_stat_card("SAM", _format_currency(report.market_size.sam), three_col_width, palette["title"]),
        build_stat_card("SOM", _format_currency(report.market_size.som), three_col_width, palette["title"]),
    ]
    content.extend([build_row(market_cards, [three_col_width, three_col_width, three_col_width]), PageBreak()])

    content.extend([Paragraph("Market Trend", styles["section_title"]), Spacer(1, 4)])
    if trend_chart_path and Path(trend_chart_path).is_file():
        content.extend([
            build_card(
                [
                    Paragraph(
                        "Live monthly demand history from Google Trends"
                        if trend_series["source"] == "google_trends"
                        else "Estimated month-by-month demand pattern for this report",
                        styles["muted"],
                    ),
                    Spacer(1, 8),
                    Image(str(trend_chart_path), width=doc.width - 24, height=220),
                ],
                doc.width,
            ),
            Spacer(1, 12),
        ])

    trend_story_cards = [
        build_stat_card("Peak month", f'{trend_extremes["peak"]["label"]} - {trend_extremes["peak"]["value"]}', two_col_width, palette["cyan"]),
        build_stat_card("Lowest month", f'{trend_extremes["low"]["label"]} - {trend_extremes["low"]["value"]}', two_col_width, palette["amber"]),
        build_stat_card("12-month average", f"{trend_average}", two_col_width, palette["purple"]),
        build_stat_card(
            "Momentum",
            f'{trend_momentum["delta"]:+}',
            two_col_width,
            palette["green"] if trend_momentum["delta"] >= 0 else palette["rose"],
            note=trend_momentum["label"],
        ),
    ]
    content.append(build_row(trend_story_cards[:2], [two_col_width, two_col_width]))
    content.extend([Spacer(1, 12), build_row(trend_story_cards[2:], [two_col_width, two_col_width]), Spacer(1, 12)])

    month_cards = []
    for index, label in enumerate(trend_labels):
        if index == 0:
            delta_text = "Starting point"
        else:
            delta_text = f'{_round_value(trend_values[index] - trend_values[index - 1]):+} vs prev'
        month_cards.append(build_month_card(label, trend_values[index], delta_text, four_col_width))

    for chunk in _chunk_list(month_cards, 4):
        content.append(build_row(chunk, [four_col_width] * len(chunk)))
        content.append(Spacer(1, 10))

    content.append(PageBreak())
    content.extend([Paragraph("Competition Snapshot", styles["section_title"]), Spacer(1, 4)])

    if competition_chart_path and Path(competition_chart_path).is_file():
        content.extend([
            build_card(
                [
                    Paragraph("Top search competitors ranked by visibility and result richness.", styles["muted"]),
                    Spacer(1, 8),
                    Image(str(competition_chart_path), width=doc.width - 24, height=210),
                ],
                doc.width,
            ),
            Spacer(1, 12),
        ])

    pressure_cards = [
        build_stat_card("Local entities scanned", _format_count(report.competition_analysis.competitor_count), two_col_width, palette["title"]),
        build_stat_card("Ranked competitors", str(len(competitor_signals)), two_col_width, palette["title"]),
    ]
    content.extend([build_row(pressure_cards, [two_col_width, two_col_width]), Spacer(1, 12)])

    pressure_text = (
        f"Local competition looks {str(report.competition_analysis.competition_level).lower()}. "
        "The chart compares search visibility, while the local count reflects how crowded the nearby category appears."
    )
    pressure_guidance = (
        "If visibility is concentrated among a few players, differentiation matters more than raw category size. "
        "If the field is broad, sharper positioning helps."
    )
    content.extend([
        build_text_card("Market Pressure", [pressure_text, pressure_guidance], doc.width),
        Spacer(1, 12),
    ])

    competitor_cards = [
        build_competitor_card(competitor, index, two_col_width)
        for index, competitor in enumerate(report.competitor_analysis)
    ]
    if competitor_cards:
        for chunk in _chunk_list(competitor_cards, 2):
            content.append(build_row(chunk, [two_col_width] * len(chunk)))
            content.append(Spacer(1, 10))
    else:
        content.extend([
            build_text_card("Top Competitors", ["No competitor entries were available for this report."], doc.width),
            Spacer(1, 12),
        ])

    content.append(PageBreak())
    content.extend([Paragraph("SWOT Analysis", styles["section_title"]), Spacer(1, 4)])

    swot_cards = [
        build_swot_card("Strengths", report.swot_analysis.strengths, two_col_width),
        build_swot_card("Weaknesses", report.swot_analysis.weaknesses, two_col_width),
        build_swot_card("Opportunities", report.swot_analysis.opportunities, two_col_width),
        build_swot_card("Threats", report.swot_analysis.threats, two_col_width),
    ]
    content.append(build_row(swot_cards[:2], [two_col_width, two_col_width]))
    content.extend([Spacer(1, 12), build_row(swot_cards[2:], [two_col_width, two_col_width]), Spacer(1, 12)])

    next_steps = [Paragraph("Recommended Next Steps", styles["card_title"])]
    for step in report.recommended_next_steps:
        next_steps.extend([Spacer(1, 6), Paragraph(f"- {step}", styles["body"])])
    content.append(build_card(next_steps, doc.width))

    try:
        doc.build(content, onFirstPage=page_theme, onLaterPages=page_theme)
    finally:
        for asset in temp_assets:
            try:
                if asset.exists():
                    asset.unlink()
            except OSError:
                pass

    print("INVESTOR PDF CREATED:", file_path)
    return str(file_path)


def log_step(step_name: str, status: str):
    print(f"[{step_name}] -> {status}")


async def run_with_timeout(task_name: str, awaitable, timeout_seconds: float, fallback):
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        print(f"{task_name} timed out after {timeout_seconds} sec; using fallback")
        return fallback
    except Exception as error:
        print(f"{task_name} failed: {error}; using fallback")
        return fallback


async def run_validation_pipeline(
    idea: IdeaInput,
    user_id: str,
) -> ValidationReport:
    pipeline_start = time.time()

    cache_key = generate_cache_key(idea.model_dump())
    cached_report = get_cache(cache_key)

    if cached_report:
        print("Returning cached validation result")
        return ValidationReport(**cached_report)

    idea_title = idea.title.strip() if idea.title else "Untitled Idea"

    print("\n" + "=" * 60)
    print(f"STARTING VALIDATION PIPELINE: {idea_title}")
    print("=" * 60)

    step_start = time.time()
    log_step("STEP 1 - AI ANALYSIS", "START")
    ai_data = generate_full_ai_report(idea)
    log_step("STEP 1 - AI ANALYSIS", "DONE")
    print(f"Duration: {round(time.time() - step_start, 2)} sec\n")

    swot_data = SWOT(**ai_data["swot_analysis"])
    market_analysis_data = MarketAnalysis(**ai_data["market_analysis"])
    ai_score = float(ai_data.get("overall_score", 5))
    executive_summary = ai_data.get("executive_summary", "")
    recommended_next_steps = ai_data.get("recommended_next_steps", [])

    step_start = time.time()
    log_step("STEP 2 - COMPETITOR SEARCH", "START")

    raw_competitors = get_competitor_search(
        market_analysis_data.potential_keywords,
        idea.location,
        idea.title,
        idea.industry or "",
        idea.target_audience or "",
    )
    print("COMPETITOR RAW:", raw_competitors)

    if not isinstance(raw_competitors, list):
        print("Competitor fallback used")
        raw_competitors = []

    competitor_data: List[Competitor] = [
        Competitor(**competitor)
        for competitor in raw_competitors
        if isinstance(competitor, dict)
    ]

    log_step("STEP 2 - COMPETITOR SEARCH", "DONE")
    print(f"Duration: {round(time.time() - step_start, 2)} sec\n")

    print("[STEP 3-5 - TREND | MARKET | COMPETITION] -> START")

    trend_raw, competition_raw, market_raw = await asyncio.gather(
        run_with_timeout(
            "Trend analysis",
            get_trend_analysis(
                market_analysis_data.potential_keywords,
                "IN-TN",
            ),
            14,
            {
                "trend_score": 38,
                "trend_direction": "Baseline demand (fallback)",
                "monthly_labels": [],
                "monthly_interest": [],
                "source": "estimated",
            },
        ),
        run_with_timeout(
            "Competition density",
            asyncio.to_thread(
                get_competitor_density,
                idea.industry or "business",
                idea.location,
            ),
            10,
            {
                "competitor_count": 0,
                "competition_level": "Unknown",
            },
        ),
        run_with_timeout(
            "Market size",
            get_market_size(
                idea.industry or "",
                idea.location,
            ),
            10,
            {
                "tam": 500_000_000,
                "sam": 150_000_000,
                "som": 15_000_000,
            },
        ),
    )

    print("[STEP 3-5 - TREND | MARKET | COMPETITION] -> DONE\n")

    step_start = time.time()
    log_step("STEP 6 - SCORING ENGINE", "START")

    raw_trend_value = (
        trend_raw.get("trend_score")
        if trend_raw and isinstance(trend_raw, dict)
        else None
    )

    if raw_trend_value is None:
        print("Trend fallback used")
        raw_trend_value = 35

    trend_score = compute_trend_score(raw_trend_value)
    market_strength = compute_market_strength(market_raw.get("tam", 0))
    competition_score = compute_competition_score(competition_raw.get("competitor_count", 0))
    risk_score = compute_risk_score(ai_score, trend_score, competition_score)

    risk_level = (
        "Low Risk" if risk_score < 4
        else "Medium Risk" if risk_score < 7
        else "High Risk"
    )
    risk_data = RiskAnalysis(risk_score=risk_score, risk_level=risk_level)

    final_score = compute_final_score(
        ai_score,
        trend_score,
        market_strength,
        competition_score,
        risk_score,
    )

    score_components = ScoreBreakdown(
        ai_score=round(ai_score, 2),
        trend_score=round(trend_score, 2),
        market_strength=round(market_strength, 2),
        competition_score=round(competition_score, 2),
        risk_score=round(risk_score, 2),
    )

    log_step("STEP 6 - SCORING ENGINE", "DONE")
    print(f"Duration: {round(time.time() - step_start, 2)} sec\n")

    step_start = time.time()
    log_step("STEP 7 - CHART GENERATION", "START")
    chart_path = generate_score_chart(final_score, trend_score)
    log_step("STEP 7 - CHART GENERATION", "DONE")
    print(f"Duration: {round(time.time() - step_start, 2)} sec\n")

    log_step("STEP 8 - BUILD REPORT", "START")

    report = ValidationReport(
        report_id=str(uuid.uuid4()),
        idea_name=idea_title,
        overall_score=final_score,
        executive_summary=executive_summary,
        swot_analysis=swot_data,
        market_analysis=market_analysis_data,
        competitor_analysis=competitor_data,
        trend_analysis=TrendAnalysis(
            trend_score=trend_score,
            trend_direction=(
                trend_raw.get("trend_direction", "stable")
                if isinstance(trend_raw, dict)
                else "stable"
            ),
            monthly_labels=(
                trend_raw.get("monthly_labels", [])
                if isinstance(trend_raw, dict)
                else []
            ),
            monthly_interest=(
                trend_raw.get("monthly_interest", [])
                if isinstance(trend_raw, dict)
                else []
            ),
            source=(
                trend_raw.get("source", "estimated")
                if isinstance(trend_raw, dict)
                else "estimated"
            ),
        ),
        market_size=MarketSize(**market_raw),
        risk_analysis=risk_data,
        competition_analysis=CompetitionAnalysis(**competition_raw),
        chart_url=chart_path,
        recommended_next_steps=recommended_next_steps,
        score_components=score_components,
    )

    generate_pdf(report)
    log_step("STEP 8 - BUILD REPORT", "DONE")

    log_step("STEP 9 - SAVE + CACHE", "START")
    save_report(report, user_id)
    set_cache(cache_key, report.model_dump())
    log_step("STEP 9 - SAVE + CACHE", "DONE")

    print("\n" + "=" * 60)
    print(f"PIPELINE COMPLETED in {round(time.time() - pipeline_start, 2)} sec")
    print("=" * 60 + "\n")

    return report
