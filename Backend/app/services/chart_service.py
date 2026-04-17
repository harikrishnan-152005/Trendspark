# app/services/chart_service.py

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BACKEND_DIR / "static"


def _prepare_chart(figsize=(6.4, 3.8)):
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=figsize, facecolor="#0f172a")
    ax.set_facecolor("#0f172a")

    for spine in ax.spines.values():
        spine.set_color("#334155")

    ax.tick_params(colors="#cbd5e1")
    ax.grid(axis="y", color="#334155", alpha=0.25, linestyle="--", linewidth=0.8)
    ax.set_axisbelow(True)

    return fig, ax


def _save_chart(fig, path: Path):
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight", dpi=180)
    plt.close(fig)
    return str(path)


def generate_score_chart(final_score: float, trend_score: float):
    normalized_trend = max(min(float(trend_score) / 10, 10), 0)

    fig, ax = _prepare_chart((5.8, 3.4))
    labels = ["Overall", "Demand"]
    values = [float(final_score), normalized_trend]
    colors = ["#818cf8", "#38bdf8"]

    bars = ax.bar(labels, values, color=colors, width=0.52)
    ax.set_ylim(0, 10)
    ax.set_ylabel("Score", color="#cbd5e1")
    ax.set_title("Validation Snapshot", color="#f8fafc", fontsize=14, pad=14)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.18,
            f"{value:.1f}",
            ha="center",
            va="bottom",
            color="#e2e8f0",
            fontsize=10,
            fontweight="bold",
        )

    chart_path = STATIC_DIR / "chart.png"
    return _save_chart(fig, chart_path)


def generate_trend_chart(report_id: str, labels, values):
    if not labels or not values:
        return None

    fig, ax = _prepare_chart((7.8, 3.8))
    x_positions = list(range(len(labels)))
    average = sum(values) / len(values)

    ax.plot(x_positions, values, color="#38bdf8", linewidth=2.4, marker="o", markersize=4.5)
    ax.fill_between(x_positions, values, [0] * len(values), color="#38bdf8", alpha=0.18)
    ax.axhline(average, color="#f472b6", linestyle="--", linewidth=1.4)

    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, color="#cbd5e1")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Demand Index", color="#cbd5e1")
    ax.set_title("12-Month Market Trend", color="#f8fafc", fontsize=14, pad=14)

    chart_path = STATIC_DIR / f"{report_id}-trend.png"
    return _save_chart(fig, chart_path)


def generate_competition_chart(report_id: str, labels, values):
    if not labels or not values:
        return None

    fig, ax = _prepare_chart((7.8, 3.8))
    colors = ["#fb7185", "#f97316", "#f59e0b", "#22c55e", "#38bdf8"][: len(values)]
    ax.barh(labels, values, color=colors)

    ax.set_xlim(0, 100)
    ax.set_xlabel("Visibility Index", color="#cbd5e1")
    ax.set_title("Competition Snapshot", color="#f8fafc", fontsize=14, pad=14)

    for index, value in enumerate(values):
        ax.text(
            value + 1.2,
            index,
            f"{value:.1f}",
            va="center",
            color="#e2e8f0",
            fontsize=9,
            fontweight="bold",
        )

    chart_path = STATIC_DIR / f"{report_id}-competition.png"
    return _save_chart(fig, chart_path)
