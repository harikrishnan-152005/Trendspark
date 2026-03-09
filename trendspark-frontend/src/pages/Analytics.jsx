import { useEffect, useState } from "react";
import axios from "axios";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Tooltip,
  Legend
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Tooltip,
  Legend
);
import { Bar, Line, Doughnut } from "react-chartjs-2";


export default function Analytics() {
  const [reports, setReports] = useState([]);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const token = localStorage.getItem("token");

      const res = await axios.get(
        "http://127.0.0.1:8000/api/v1/reports",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      setReports(res.data);
    } catch (err) {
      console.log("Error fetching reports", err.response);
    }
  };

  const scores = reports.map(r => r.overall_score);

  const avgScore =
    scores.length > 0
      ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2)
      : 0;

  return (
    <div>

      <h2 className="text-3xl font-bold mb-8">📊 Analytics Dashboard</h2>

      <div className="grid md:grid-cols-2 gap-8">

        <div className="bg-slate-900 p-6 rounded-xl">
          <h3 className="mb-4">Score Trend</h3>
          <Line
            data={{
              labels: reports.map(r => r.idea_name),
              datasets: [
                {
                  label: "Overall Score",
                  data: scores,
                  borderColor: "#6366f1"
                }
              ]
            }}
          />
        </div>

        <div className="bg-slate-900 p-6 rounded-xl">
          <h3 className="mb-4">Score Distribution</h3>
          <Doughnut
            data={{
              labels: ["Low (<4)", "Medium (4-7)", "High (>7)"],
              datasets: [
                {
                  data: [
                    scores.filter(s => s < 4).length,
                    scores.filter(s => s >= 4 && s <= 7).length,
                    scores.filter(s => s > 7).length
                  ],
                  backgroundColor: ["#ef4444", "#f59e0b", "#22c55e"]
                }
              ]
            }}
          />
        </div>

      </div>

      <div className="mt-10 bg-slate-900 p-6 rounded-xl">
        <h3>Total Reports: {reports.length}</h3>
        <h3>Average Score: {avgScore}</h3>
      </div>

    </div>
  );
}