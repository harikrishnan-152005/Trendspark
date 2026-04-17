import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { deleteReport, getReport, getReports } from "../services/api";

export default function History() {
  const [reports, setReports] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const response = await getReports();
      setReports(response.data);
    } catch (error) {
      if (error?.response?.status === 401) {
        return;
      }

      console.error("Error fetching reports", error);
    }
  };

  const handleDelete = async (id) => {
    const confirmDelete = window.confirm("Delete this report?");

    if (!confirmDelete) {
      return;
    }

    try {
      await deleteReport(id);
      setReports((prev) => prev.filter((report) => report.report_id !== id));
    } catch (error) {
      if (error?.response?.status === 401) {
        return;
      }

      console.error("Error deleting report", error);
      alert("Delete failed");
    }
  };

  const previewReport = async (id) => {
    try {
      const response = await getReport(id);
      localStorage.setItem("previewData", JSON.stringify(response.data));
      navigate("/");
    } catch (error) {
      if (error?.response?.status === 401) {
        return;
      }

      console.error("Error previewing report", error);
      alert("Preview failed");
    }
  };

  return (
    <div>
      <h2 className="text-3xl font-bold mb-8">Report History</h2>

      <div className="space-y-4">
        {reports.length === 0 && (
          <p className="text-gray-400">No reports found.</p>
        )}

        {reports.map((report) => (
          <div
            key={report.report_id}
            className="bg-slate-900 p-6 rounded-xl border border-slate-800"
          >
            <h3 className="text-xl font-semibold">{report.idea_name}</h3>

            <p className="text-gray-400">Score: {report.overall_score} / 10</p>

            <div className="flex gap-4 mt-2">
              <button
                onClick={() => handleDelete(report.report_id)}
                className="bg-red-600 px-4 py-2 rounded"
              >
                Delete
              </button>

              <button
                onClick={() => previewReport(report.report_id)}
                className="bg-indigo-600 px-4 py-2 rounded"
              >
                Preview
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
