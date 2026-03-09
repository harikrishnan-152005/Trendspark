import { useState } from "react";
import { validateIdea } from "../services/api";
import { Line, Bar } from "react-chartjs-2";
import Chart from "react-apexcharts";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale
);

export default function Dashboard() {

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    const form = new FormData(e.target);

    const data = {
      title: form.get("title"),
      description: form.get("description"),
      industry: form.get("industry"),
      target_audience: form.get("target"),
      location: form.get("location") || "Chennai"
    };

    try {
      const res = await validateIdea(data);
      setResult(res.data);
    } catch (err) {
      alert("Backend not running");
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen p-10 max-w-6xl mx-auto">

      <h1 className="text-4xl font-bold mb-8 text-indigo-400">
        🚀 TrendSpark AI Dashboard
      </h1>

      {/* FORM */}
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

        {/* LOCATION FIELD ADDED */}
        <input
          name="location"
          placeholder="Location (e.g. Chennai, Bangalore, Mumbai)"
          className="w-full p-3 rounded bg-slate-800"
        />

        <button className="bg-indigo-600 px-6 py-3 rounded">
          {loading ? "Analyzing..." : "Validate"}
        </button>

      </form>

      {/* DASHBOARD */}
      {result && (
        <div className="space-y-12">

          {/* SCORE */}
          <div className="bg-slate-900 p-6 rounded-xl text-center">
            <h2 className="text-3xl font-bold">
              Overall Score: {result.overall_score} / 10
            </h2>
          </div>

          {/* TREND CHART */}
          <div className="bg-slate-900 p-6 rounded-xl">
            <h3 className="text-xl mb-4">Market Trend</h3>
            <Line
              data={{
                labels: ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
                datasets: [{
                  label: "Trend Score",
                  data: Array(12).fill(result.trend_analysis.trend_score),
                  borderColor: "#6366f1",
                  tension: 0.4
                }]
              }}
            />
          </div>

          {/* COMPETITION BAR */}
          <div className="bg-slate-900 p-6 rounded-xl">
            <h3 className="text-xl mb-4">Competition</h3>
            <Bar
              data={{
                labels: ["Competitors"],
                datasets: [{
                  label: "Count",
                  data: [result.competition_analysis.competitor_count],
                  backgroundColor: "#f97316"
                }]
              }}
            />
          </div>

          {/* RISK GAUGE */}
          <div className="bg-slate-900 p-6 rounded-xl">
            <h3 className="text-xl mb-4">Risk Level</h3>
            <Chart
              type="radialBar"
              height={300}
              series={[result.risk_analysis.risk_score * 10]}
              options={{
                plotOptions: {
                  radialBar: {
                    hollow: { size: "60%" }
                  }
                },
                labels: ["Risk Score"]
              }}
            />
          </div>

          {/* MARKET SIZE */}
          <div className="grid grid-cols-3 gap-6">
            <MarketCard title="TAM" value={result.market_size.tam} />
            <MarketCard title="SAM" value={result.market_size.sam} />
            <MarketCard title="SOM" value={result.market_size.som} />
          </div>

          {/* SWOT */}
          <div className="grid grid-cols-2 gap-6">
            <SwotCard title="Strengths" items={result.swot_analysis.strengths} />
            <SwotCard title="Weaknesses" items={result.swot_analysis.weaknesses} />
            <SwotCard title="Opportunities" items={result.swot_analysis.opportunities} />
            <SwotCard title="Threats" items={result.swot_analysis.threats} />
          </div>

          {/* COMPETITORS */}
          <div className="bg-slate-900 p-6 rounded-xl">
            <h3 className="text-xl mb-4">Top Competitors</h3>
            {result.competitor_analysis.map((c, i) => (
              <div key={i} className="mb-3">
                <p className="font-bold">{c.name}</p>
                <a href={c.url} target="_blank" rel="noreferrer" className="text-indigo-400">
                  {c.url}
                </a>
              </div>
            ))}
          </div>

          {/* PDF DOWNLOAD */}
          <button
            onClick={() =>
              window.open(
                `http://127.0.0.1:8000/api/v1/report/${result.report_id}/pdf`
              )
            }
            className="bg-green-600 px-6 py-3 rounded"
          >
            Download PDF Report
          </button>

        </div>
      )}

    </div>
  );
}

function MarketCard({ title, value }) {
  return (
    <div className="bg-slate-900 p-6 rounded-xl text-center">
      <p className="text-gray-400">{title}</p>
      <h2 className="text-2xl font-bold">
        ₹ {Number(value).toLocaleString()}
      </h2>
    </div>
  );
}

function SwotCard({ title, items }) {
  return (
    <div className="bg-slate-900 p-6 rounded-xl">
      <h3 className="text-xl mb-4">{title}</h3>
      <ul className="list-disc pl-5 space-y-1">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}