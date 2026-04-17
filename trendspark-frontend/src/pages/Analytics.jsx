import { useEffect, useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";
import { getReport, getReports } from "../services/api";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler,
);

function roundValue(value) {
  return Math.round(value * 100) / 100;
}

function shortenLabel(label, limit = 18) {
  const text = String(label || "Untitled").trim();
  if (text.length <= limit) {
    return text;
  }

  return `${text.slice(0, limit - 1)}...`;
}

function buildScoreBuckets(scores) {
  return [
    { label: "Low (<4)", value: scores.filter((score) => score < 4).length, color: "#f43f5e" },
    { label: "Medium (4-7)", value: scores.filter((score) => score >= 4 && score <= 7).length, color: "#f59e0b" },
    { label: "High (>7)", value: scores.filter((score) => score > 7).length, color: "#22c55e" },
  ];
}

function buildDriverScores(report) {
  if (!report?.score_components) {
    return [];
  }

  return [
    { label: "AI fit", value: roundValue(report.score_components.ai_score), color: "#818cf8" },
    { label: "Demand", value: roundValue(report.score_components.trend_score / 10), color: "#38bdf8" },
    { label: "Market size", value: roundValue(report.score_components.market_strength / 10), color: "#22c55e" },
    { label: "Competition room", value: roundValue(report.score_components.competition_score), color: "#f59e0b" },
    { label: "Execution safety", value: roundValue(Math.max(0, 10 - report.score_components.risk_score)), color: "#f97316" },
  ];
}

const lineOptions = {
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: "#cbd5e1",
      },
    },
    tooltip: {
      backgroundColor: "#020617",
      titleColor: "#f8fafc",
      bodyColor: "#cbd5e1",
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
      max: 10,
      ticks: {
        color: "#94a3b8",
      },
      grid: {
        color: "rgba(148, 163, 184, 0.08)",
      },
    },
  },
};

const barOptions = {
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: "#020617",
      titleColor: "#f8fafc",
      bodyColor: "#cbd5e1",
    },
  },
  scales: {
    x: {
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

export default function Analytics() {
  const [reports, setReports] = useState([]);
  const [reportDetails, setReportDetails] = useState([]);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const response = await getReports();
      const summaries = response.data;
      setReports(summaries);

      const detailResponses = await Promise.all(
        summaries.map(async (report) => {
          try {
            const detail = await getReport(report.report_id);
            return detail.data;
          } catch (error) {
            if (error?.response?.status === 401) {
              throw error;
            }

            return null;
          }
        }),
      );

      setReportDetails(detailResponses.filter(Boolean));
    } catch (err) {
      if (err?.response?.status === 401) {
        return;
      }

      console.log("Error fetching reports", err.response);
    }
  };

  const scores = reports.map((report) => Number(report.overall_score || 0));
  const averageScore =
    scores.length > 0 ? roundValue(scores.reduce((total, score) => total + score, 0) / scores.length) : 0;
  const bestScore = scores.length > 0 ? Math.max(...scores) : 0;
  const averageDemand =
    reportDetails.length > 0
      ? roundValue(
          reportDetails.reduce(
            (total, report) => total + Number(report?.score_components?.trend_score || 0),
            0,
          ) / reportDetails.length / 10,
        )
      : 0;

  const highlightedReport =
    reportDetails.length > 0
      ? reportDetails.reduce((best, report) =>
          Number(report.overall_score || 0) > Number(best.overall_score || 0) ? report : best,
        )
      : null;

  const scoreBuckets = buildScoreBuckets(scores);
  const driverScores = buildDriverScores(highlightedReport);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-2">Analytics Dashboard</h2>
        <p className="text-slate-400">
          Cleaner portfolio visuals that still make sense even when you only have one report.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <AnalyticsCard label="Total reports" value={String(reports.length)} tone="text-white" />
        <AnalyticsCard label="Average score" value={`${averageScore} / 10`} tone="text-cyan-300" />
        <AnalyticsCard label="Best score" value={`${bestScore} / 10`} tone="text-emerald-300" />
        <AnalyticsCard label="Avg demand" value={`${averageDemand} / 10`} tone="text-amber-300" />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
          <h3 className="text-xl font-semibold text-white">Report Score Comparison</h3>
          <p className="mt-2 text-sm text-slate-400">
            Compare idea scores side by side instead of forcing a time trend where there is no date history.
          </p>

          <div className="mt-6 h-80">
            <Line
              data={{
                labels: reports.map((report) => shortenLabel(report.idea_name)),
                datasets: [
                  {
                    label: "Overall score",
                    data: scores,
                    borderColor: "#818cf8",
                    backgroundColor: "rgba(129, 140, 248, 0.15)",
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                  },
                ],
              }}
              options={lineOptions}
            />
          </div>
        </section>

        <section className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
          <h3 className="text-xl font-semibold text-white">Portfolio Score Mix</h3>
          <p className="mt-2 text-sm text-slate-400">
            Count how many reports sit in low, medium, and high score bands.
          </p>

          <div className="mt-6 h-80">
            <Bar
              data={{
                labels: scoreBuckets.map((bucket) => bucket.label),
                datasets: [
                  {
                    data: scoreBuckets.map((bucket) => bucket.value),
                    backgroundColor: scoreBuckets.map((bucket) => bucket.color),
                    borderRadius: 14,
                    borderSkipped: false,
                  },
                ],
              }}
              options={{
                ...barOptions,
                scales: {
                  ...barOptions.scales,
                  y: {
                    ...barOptions.scales.y,
                    beginAtZero: true,
                    ticks: {
                      color: "#94a3b8",
                      precision: 0,
                    },
                  },
                },
              }}
            />
          </div>
        </section>
      </div>

      <section className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-xl font-semibold text-white">Viability Drivers</h3>
            <p className="mt-2 text-sm text-slate-400">
              Normalized driver view for the strongest report in the current portfolio.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Highlighted report</p>
            <p className="mt-2 text-sm font-semibold text-white">
              {highlightedReport ? highlightedReport.idea_name : "No reports yet"}
            </p>
          </div>
        </div>

        <div className="mt-6 h-80">
          <Bar
            data={{
              labels: driverScores.map((driver) => driver.label),
              datasets: [
                {
                  label: "Driver score",
                  data: driverScores.map((driver) => driver.value),
                  backgroundColor: driverScores.map((driver) => driver.color),
                  borderRadius: 14,
                  borderSkipped: false,
                },
              ],
            }}
            options={{
              ...barOptions,
              scales: {
                ...barOptions.scales,
                y: {
                  ...barOptions.scales.y,
                  beginAtZero: true,
                  max: 10,
                  ticks: {
                    color: "#94a3b8",
                  },
                  grid: {
                    color: "rgba(148, 163, 184, 0.08)",
                  },
                },
              },
            }}
          />
        </div>
      </section>
    </div>
  );
}

function AnalyticsCard({ label, value, tone }) {
  return (
    <div className="rounded-3xl bg-slate-900/95 p-6 shadow-lg shadow-slate-950/20">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className={`mt-3 text-3xl font-bold ${tone}`}>{value}</p>
    </div>
  );
}
