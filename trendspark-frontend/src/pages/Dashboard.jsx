import { useEffect, useState } from "react";
import { downloadReportPdf, validateIdea } from "../services/api";
import { Line, Bar } from "react-chartjs-2";
import Chart from "react-apexcharts";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  Filler,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  Filler,
  Tooltip,
  Legend,
);

const MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function clampValue(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function roundValue(value) {
  return Math.round(value * 10) / 10;
}

function hashText(text) {
  return String(text || "").split("").reduce((total, char) => total + char.charCodeAt(0), 0);
}

function formatCompactNumber(value) {
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function shortenLabel(label, limit = 18) {
  const text = String(label || "Unknown").trim();
  if (text.length <= limit) {
    return text;
  }

  return `${text.slice(0, limit - 1)}...`;
}

function extractHost(url) {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    return host;
  } catch {
    return "Link unavailable";
  }
}

function getTrendSeries(result) {
  const trendAnalysis = result?.trend_analysis || {};
  const labels = Array.isArray(trendAnalysis.monthly_labels) ? trendAnalysis.monthly_labels : [];
  const values = Array.isArray(trendAnalysis.monthly_interest) ? trendAnalysis.monthly_interest : [];

  if (labels.length >= 6 && values.length === labels.length) {
    return {
      labels,
      values: values.map((value) => roundValue(Number(value || 0))),
      source: trendAnalysis.source || "google_trends",
      direction: trendAnalysis.trend_direction || "Stable demand",
    };
  }

  const baseScore = clampValue(Number(trendAnalysis.trend_score || 38), 20, 90);
  const seed = hashText(`${result?.idea_name || ""}${trendAnalysis.trend_direction || ""}`);
  const estimatedValues = MONTH_LABELS.map((label, index) => {
    const seasonal = Math.sin(((index + (seed % 4)) / 12) * Math.PI * 2) * 5.4;
    const momentum = ((index - 5.5) / 5.5) * ((seed % 5) + 1) * 0.7;
    const pulse = (((seed + index * 11) % 9) - 4) * 0.45;
    return roundValue(clampValue(baseScore + seasonal + momentum + pulse, 18, 96));
  });

  return {
    labels: MONTH_LABELS,
    values: estimatedValues,
    source: "estimated",
    direction: trendAnalysis.trend_direction || "Baseline demand",
  };
}

function getAverage(values) {
  if (!values.length) {
    return 0;
  }

  return roundValue(values.reduce((total, value) => total + value, 0) / values.length);
}

function getTrendExtremes(labels, values) {
  if (!labels.length || !values.length) {
    return {
      peak: { label: "-", value: 0 },
      low: { label: "-", value: 0 },
    };
  }

  let peakIndex = 0;
  let lowIndex = 0;

  values.forEach((value, index) => {
    if (value > values[peakIndex]) {
      peakIndex = index;
    }

    if (value < values[lowIndex]) {
      lowIndex = index;
    }
  });

  return {
    peak: {
      label: labels[peakIndex],
      value: values[peakIndex],
    },
    low: {
      label: labels[lowIndex],
      value: values[lowIndex],
    },
  };
}

function getMomentumMeta(values) {
  if (values.length < 2) {
    return {
      delta: 0,
      label: "Stable",
      tone: "text-slate-300",
    };
  }

  const delta = roundValue(values[values.length - 1] - values[0]);

  if (delta >= 6) {
    return { delta, label: "Strong upward momentum", tone: "text-emerald-300" };
  }

  if (delta >= 2) {
    return { delta, label: "Healthy upward momentum", tone: "text-cyan-300" };
  }

  if (delta <= -6) {
    return { delta, label: "Demand softened over time", tone: "text-rose-300" };
  }

  if (delta <= -2) {
    return { delta, label: "Slight cooling trend", tone: "text-amber-300" };
  }

  return { delta, label: "Demand remained steady", tone: "text-slate-300" };
}

function buildCompetitorSignals(competitors) {
  return (competitors || []).slice(0, 5).map((competitor, index) => {
    const snippetWordCount = String(competitor.snippet || "").split(/\s+/).filter(Boolean).length;
    const visibility = roundValue(clampValue(94 - (index * 11.5) + Math.min(snippetWordCount * 0.35, 6), 38, 96));

    return {
      ...competitor,
      label: shortenLabel(competitor.name, 24),
      host: extractHost(competitor.url),
      visibility,
    };
  });
}

function getCompetitionBadge(level) {
  const normalized = String(level || "").toLowerCase();

  if (normalized.includes("very high")) {
    return "bg-rose-500/15 text-rose-300 border border-rose-400/30";
  }

  if (normalized.includes("high")) {
    return "bg-orange-500/15 text-orange-300 border border-orange-400/30";
  }

  if (normalized.includes("medium")) {
    return "bg-amber-500/15 text-amber-300 border border-amber-400/30";
  }

  if (normalized.includes("low")) {
    return "bg-emerald-500/15 text-emerald-300 border border-emerald-400/30";
  }

  return "bg-slate-700/60 text-slate-200 border border-slate-600";
}

function buildTrendChartData(labels, values) {
  const average = getAverage(values);

  return {
    labels,
    datasets: [
      {
        label: "Demand index",
        data: values,
        borderColor: "#38bdf8",
        backgroundColor: "rgba(56, 189, 248, 0.18)",
        fill: true,
        tension: 0.35,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: "#7dd3fc",
        pointBorderColor: "#0f172a",
        pointBorderWidth: 2,
      },
      {
        label: "12-month average",
        data: labels.map(() => average),
        borderColor: "rgba(244, 114, 182, 0.8)",
        borderDash: [6, 6],
        pointRadius: 0,
        tension: 0,
      },
    ],
  };
}

function buildTrendChartOptions(source) {
  return {
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: "#cbd5e1",
          boxWidth: 14,
        },
      },
      tooltip: {
        backgroundColor: "#020617",
        titleColor: "#f8fafc",
        bodyColor: "#cbd5e1",
        callbacks: {
          label: (context) => `${context.dataset.label}: ${context.parsed.y}`,
          afterBody: () =>
            source === "google_trends"
              ? "Source: Live Google Trends history"
              : "Source: Estimated monthly pattern",
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: "#94a3b8",
        },
        grid: {
          display: false,
        },
      },
      y: {
        min: 0,
        max: 100,
        ticks: {
          color: "#94a3b8",
        },
        grid: {
          color: "rgba(148, 163, 184, 0.08)",
        },
      },
    },
  };
}

function buildCompetitionChartData(signals) {
  return {
    labels: signals.map((signal) => signal.label),
    datasets: [
      {
        label: "Search visibility index",
        data: signals.map((signal) => signal.visibility),
        backgroundColor: ["#fb7185", "#f97316", "#f59e0b", "#22c55e", "#38bdf8"],
        borderRadius: 10,
        borderSkipped: false,
      },
    ],
  };
}

const competitionChartOptions = {
  indexAxis: "y",
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: "#020617",
      titleColor: "#f8fafc",
      bodyColor: "#cbd5e1",
      callbacks: {
        label: (context) => `Visibility index: ${context.parsed.x}`,
      },
    },
  },
  scales: {
    x: {
      min: 0,
      max: 100,
      ticks: {
        color: "#94a3b8",
      },
      grid: {
        color: "rgba(148, 163, 184, 0.08)",
      },
    },
    y: {
      ticks: {
        color: "#cbd5e1",
      },
      grid: {
        display: false,
      },
    },
  },
};

export default function Dashboard() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isPreview, setIsPreview] = useState(false);

  const exitPreviewMode = () => {
    localStorage.removeItem("previewData");
    setIsPreview(false);
    setResult(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    localStorage.removeItem("previewData");
    setIsPreview(false);

    const form = new FormData(e.target);

    const data = {
      title: form.get("title"),
      description: form.get("description"),
      industry: form.get("industry"),
      target_audience: form.get("target"),
      location: form.get("location") || "Chennai",
    };

    try {
      const response = await validateIdea(data);
      setResult(response.data);
    } catch (err) {
      if (err?.response?.status === 401) {
        return;
      }

      if (err?.code === "ERR_NETWORK") {
        alert("Backend not running");
      } else {
        alert(err?.response?.data?.detail || "Validation failed");
      }
    }

    setLoading(false);
  };

  const downloadPDF = async () => {
    try {
      if (!result?.report_id) {
        alert("Report is not ready yet.");
        return;
      }

      const response = await downloadReportPdf(result.report_id);
      const blob = response.data;
      const url = window.URL.createObjectURL(blob);

      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${result.report_id}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    } catch (err) {
      if (err?.response?.status === 401) {
        return;
      }

      console.error(err);
      alert("PDF download failed");
    }
  };

  useEffect(() => {
    const previewData = localStorage.getItem("previewData");

    if (previewData && !result) {
      try {
        const data = JSON.parse(previewData);
        setResult(data);
        setIsPreview(true);
        localStorage.removeItem("previewData");
      } catch (err) {
        console.error("Invalid preview data");
      }
    }
  }, [result]);

  const trendSeries = result ? getTrendSeries(result) : null;
  const trendValues = trendSeries?.values || [];
  const trendLabels = trendSeries?.labels || MONTH_LABELS;
  const trendExtremes = getTrendExtremes(trendLabels, trendValues);
  const trendAverage = getAverage(trendValues);
  const trendMomentum = getMomentumMeta(trendValues);
  const competitorSignals = buildCompetitorSignals(result?.competitor_analysis || []);
  const competitionLevel = result?.competition_analysis?.competition_level || "Unknown";
  const competitionCount = Number(result?.competition_analysis?.competitor_count || 0);

  return (
    <div className="min-h-screen p-6 md:p-10 max-w-7xl mx-auto">
      <h1 className="text-4xl font-bold mb-8 text-indigo-400">
        TrendSpark AI Dashboard
      </h1>

      {isPreview && (
        <div className="flex items-center gap-4 mb-4">
          <p className="text-yellow-400">Viewing saved report (Preview Mode)</p>
          <button
            type="button"
            onClick={exitPreviewMode}
            className="bg-slate-800 px-3 py-1 rounded text-sm"
          >
            Exit Preview
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 mb-10">
        <input
          name="title"
          placeholder="Startup Title"
          className="w-full p-3 rounded bg-slate-800"
          required
        />

        <textarea
          name="description"
          placeholder="Startup Description"
          className="w-full p-3 rounded bg-slate-800"
          required
        />

        <input
          name="industry"
          placeholder="Industry (EdTech, Health, Fintech...)"
          className="w-full p-3 rounded bg-slate-800"
        />

        <input
          name="target"
          placeholder="Target Audience"
          className="w-full p-3 rounded bg-slate-800"
        />

        <input
          name="location"
          placeholder="Location (e.g. Chennai, Bangalore, Mumbai)"
          className="w-full p-3 rounded bg-slate-800"
        />

        <button className="bg-indigo-600 px-6 py-3 rounded">
          {loading ? "Analyzing..." : "Validate"}
        </button>
      </form>

      {result && (
        <div className="space-y-8">
          <section className="rounded-3xl border border-indigo-500/20 bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/70 p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-400">
                  Validation snapshot
                </p>
                <h2 className="mt-2 text-3xl font-bold">
                  Overall Score: {result.overall_score} / 10
                </h2>
                <p className="mt-2 max-w-2xl text-slate-300">
                  {result.executive_summary}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 lg:w-[360px]">
                <SummaryCard
                  label="Trend direction"
                  value={trendSeries?.direction || "Stable"}
                  tone="text-cyan-300"
                />
                <SummaryCard
                  label="Competition level"
                  value={competitionLevel}
                  tone="text-orange-300"
                />
                <SummaryCard
                  label="Risk level"
                  value={result.risk_analysis.risk_level}
                  tone="text-rose-300"
                />
                <SummaryCard
                  label="Top competitors"
                  value={String(result.competitor_analysis.length)}
                  tone="text-emerald-300"
                />
              </div>
            </div>
          </section>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_320px]">
            <section className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-2xl font-semibold text-white">Market Trend</h3>
                  <p className="text-sm text-slate-400">
                    {trendSeries?.source === "google_trends"
                      ? "Live monthly demand history from Google Trends"
                      : "Estimated month-by-month demand pattern for this report"}
                  </p>
                </div>
                <span className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-sm text-cyan-200">
                  12-month demand index
                </span>
              </div>

              <div className="mt-6 h-80">
                <Line
                  data={buildTrendChartData(trendLabels, trendValues)}
                  options={buildTrendChartOptions(trendSeries?.source)}
                />
              </div>

              <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
                {trendLabels.map((label, index) => (
                  <div
                    key={`${label}-${index}`}
                    className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3"
                  >
                    <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
                    <p className="mt-2 text-lg font-semibold text-white">{trendValues[index]}</p>
                    <p className="text-xs text-slate-400">
                      {index === 0
                        ? "Starting point"
                        : `${trendValues[index] >= trendValues[index - 1] ? "+" : ""}${roundValue(trendValues[index] - trendValues[index - 1])} vs prev`}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
              <h3 className="text-xl font-semibold text-white">Trend Story</h3>
              <p className="mt-2 text-sm text-slate-400">
                A quick read on the strongest month, weakest month, and the direction of demand.
              </p>

              <div className="mt-6 space-y-4">
                <InsightCard
                  label="Peak month"
                  value={`${trendExtremes.peak.label} - ${trendExtremes.peak.value}`}
                  accent="text-cyan-300"
                />
                <InsightCard
                  label="Lowest month"
                  value={`${trendExtremes.low.label} - ${trendExtremes.low.value}`}
                  accent="text-amber-300"
                />
                <InsightCard
                  label="12-month average"
                  value={String(trendAverage)}
                  accent="text-fuchsia-300"
                />
                <InsightCard
                  label="Momentum"
                  value={`${trendMomentum.delta >= 0 ? "+" : ""}${trendMomentum.delta}`}
                  accent={trendMomentum.tone}
                />
              </div>

              <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Readout</p>
                <p className={`mt-2 text-sm font-medium ${trendMomentum.tone}`}>
                  {trendMomentum.label}
                </p>
                <p className="mt-3 text-sm text-slate-400">
                  {trendSeries?.source === "google_trends"
                    ? "This curve is built from live monthly interest history."
                    : "Live history was unavailable for this run, so the monthly view uses a stable demand estimate."}
                </p>
              </div>
            </section>
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_360px]">
            <section className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-2xl font-semibold text-white">Competition Snapshot</h3>
                  <p className="text-sm text-slate-400">
                    Top search competitors ranked by visibility and result richness.
                  </p>
                </div>
                <span className="rounded-full border border-orange-400/20 bg-orange-500/10 px-3 py-1 text-sm text-orange-200">
                  Top {competitorSignals.length || 0} players
                </span>
              </div>

              {competitorSignals.length > 0 ? (
                <div className="mt-6 h-80">
                  <Bar
                    data={buildCompetitionChartData(competitorSignals)}
                    options={competitionChartOptions}
                  />
                </div>
              ) : (
                <div className="mt-6 rounded-2xl border border-dashed border-slate-700 bg-slate-950/60 p-6 text-slate-400">
                  No competitor visibility data is available for this report yet.
                </div>
              )}
            </section>

            <section className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold text-white">Market Pressure</h3>
                <span className={`rounded-full px-3 py-1 text-sm ${getCompetitionBadge(competitionLevel)}`}>
                  {competitionLevel}
                </span>
              </div>

              <div className="mt-6 grid grid-cols-2 gap-3">
                <StatCard label="Local entities scanned" value={formatCompactNumber(competitionCount)} />
                <StatCard label="Ranked competitors" value={String(competitorSignals.length)} />
              </div>

              <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Interpretation</p>
                <p className="mt-2 text-sm text-slate-300">
                  Local competition looks <span className="font-semibold text-white">{competitionLevel.toLowerCase()}</span>.
                  The bar chart compares search visibility, while the local count reflects how crowded the nearby category appears.
                </p>
              </div>

              <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">What this means</p>
                <p className="mt-2 text-sm text-slate-400">
                  If visibility is concentrated among a few players, differentiation matters more than raw category size. If the field is broad, sharper positioning helps.
                </p>
              </div>
            </section>
          </div>

          <div className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
            <h3 className="text-xl font-semibold text-white">Risk Level</h3>
            <div className="mt-4 grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)] lg:items-center">
              <div>
                <Chart
                  type="radialBar"
                  height={300}
                  series={[result.risk_analysis.risk_score * 10]}
                  options={{
                    chart: {
                      sparkline: {
                        enabled: true,
                      },
                    },
                    colors: ["#f97316"],
                    plotOptions: {
                      radialBar: {
                        hollow: {
                          size: "62%",
                        },
                        track: {
                          background: "#1e293b",
                        },
                        dataLabels: {
                          name: {
                            color: "#94a3b8",
                          },
                          value: {
                            color: "#f8fafc",
                            formatter: (value) => `${Math.round(value)}%`,
                          },
                        },
                      },
                    },
                    labels: ["Risk score"],
                  }}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <SummaryCard label="Risk level" value={result.risk_analysis.risk_level} tone="text-orange-300" />
                <SummaryCard label="Risk score" value={String(result.risk_analysis.risk_score)} tone="text-rose-300" />
                <SummaryCard label="Demand score" value={String(result.score_components.trend_score)} tone="text-cyan-300" />
              </div>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <MarketCard title="TAM" value={result.market_size.tam} />
            <MarketCard title="SAM" value={result.market_size.sam} />
            <MarketCard title="SOM" value={result.market_size.som} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <SwotCard title="Strengths" items={result.swot_analysis.strengths} />
            <SwotCard title="Weaknesses" items={result.swot_analysis.weaknesses} />
            <SwotCard title="Opportunities" items={result.swot_analysis.opportunities} />
            <SwotCard title="Threats" items={result.swot_analysis.threats} />
          </div>

          <section className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
            <h3 className="text-2xl font-semibold text-white">Top Competitors</h3>
            <p className="mt-2 text-sm text-slate-400">
              Quick scan of the strongest visible players from the market search.
            </p>

            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              {result.competitor_analysis.map((competitor, index) => (
                <article
                  key={`${competitor.url || competitor.name}-${index}`}
                  className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">
                        #{index + 1}
                      </p>
                      <h4 className="mt-2 text-lg font-semibold text-white">
                        {competitor.name}
                      </h4>
                    </div>

                    <span className="rounded-full bg-indigo-500/15 px-3 py-1 text-xs text-indigo-200">
                      {extractHost(competitor.url)}
                    </span>
                  </div>

                  <p className="mt-3 text-sm text-slate-300">
                    {competitor.snippet || "No summary available for this competitor."}
                  </p>

                  <a
                    href={competitor.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 inline-flex text-sm text-cyan-300 transition hover:text-cyan-200"
                  >
                    Visit competitor site
                  </a>
                </article>
              ))}
            </div>
          </section>

          <button
            onClick={downloadPDF}
            className="w-fit rounded-2xl bg-green-600 px-6 py-3 font-medium transition hover:bg-green-500"
          >
            Download PDF Report
          </button>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, tone }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className={`mt-2 text-lg font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}

function InsightCard({ label, value, accent }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className={`mt-2 text-lg font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function MarketCard({ title, value }) {
  return (
    <div className="rounded-3xl bg-slate-900/95 p-6 text-center shadow-lg shadow-slate-950/20">
      <p className="text-sm uppercase tracking-[0.24em] text-slate-400">{title}</p>
      <h2 className="mt-3 text-3xl font-bold text-white">
        Rs. {Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
      </h2>
    </div>
  );
}

function SwotCard({ title, items }) {
  return (
    <div className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
      <h3 className="text-2xl font-semibold text-white">{title}</h3>
      <ul className="mt-4 space-y-3">
        {items.map((item, index) => (
          <li
            key={`${title}-${index}`}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-slate-200"
          >
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
