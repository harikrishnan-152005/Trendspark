import { useEffect, useState } from "react";
import axios from "axios";

export default function History() {

  const [reports, setReports] = useState([]);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const token = localStorage.getItem("token");  // or access_token

      const response = await axios.get(
        "http://127.0.0.1:8000/api/v1/reports",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      setReports(response.data);
    } catch (error) {
      console.error("Error fetching reports", error);
    }
  };

  return (
    <div>

      <h2 className="text-3xl font-bold mb-8">
        📄 Report History
      </h2>

      <div className="space-y-4">

        {reports.length === 0 && (
          <p className="text-gray-400">No reports found.</p>
        )}

        {reports.map((report) => (
          <div
            key={report.report_id}
            className="bg-slate-900 p-6 rounded-xl border border-slate-800"
          >
            <h3 className="text-xl font-semibold">
              {report.idea_name}
            </h3>

            <p className="text-gray-400">
              Score: {report.overall_score} / 10
            </p>

            <button
              onClick={() =>
                window.open(
                  `http://127.0.0.1:8000/api/v1/report/${report.report_id}/pdf`
                )
              }
              className="mt-4 bg-indigo-600 px-4 py-2 rounded"
            >
              Download PDF
            </button>
          </div>
        ))}

      </div>

    </div>
  );
}