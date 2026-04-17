import axios from "axios";

export const clearSession = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("previewData");
};

const redirectToLogin = () => {
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
    return;
  }

  window.location.reload();
};

export const handleUnauthorized = () => {
  clearSession();
  redirectToLogin();
};

export const API = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
});

API.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      handleUnauthorized();
    }

    return Promise.reject(error);
  },
);

export const validateIdea = (data) => API.post("/validate", data);
export const getReports = () => API.get("/reports");
export const getReport = (reportId) => API.get(`/report/${reportId}`);
export const deleteReport = (reportId) => API.delete(`/report/${reportId}`);
export const downloadReportPdf = (reportId) =>
  API.get(`/report/${reportId}/pdf`, {
    responseType: "blob",
  });
