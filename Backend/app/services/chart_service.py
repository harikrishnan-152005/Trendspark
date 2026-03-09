# app/services/chart_service.py

import matplotlib
matplotlib.use("Agg")  # 🔥 Critical fix

import matplotlib.pyplot as plt
import os


def generate_score_chart(final_score: float, trend_score: float):

    plt.figure()

    labels = ["Final Score", "Trend Score"]
    values = [final_score, trend_score]

    plt.bar(labels, values)

    os.makedirs("static", exist_ok=True)

    chart_path = "static/chart.png"
    plt.savefig(chart_path)
    plt.close()

    return chart_path