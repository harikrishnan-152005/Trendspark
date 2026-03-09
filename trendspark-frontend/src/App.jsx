import { Routes, Route, Navigate } from "react-router-dom";
import SidebarLayout from "./layout/SidebarLayout";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Analytics from "./pages/Analytics";
import Login from "./pages/Login";

export default function App() {

  const token = localStorage.getItem("token");
  if (!token) {
    return <Login />;
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/*"
        element={
          token ? (
            <SidebarLayout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/history" element={<History />} />
                <Route path="/analytics" element={<Analytics />} />
              </Routes>
            </SidebarLayout>
          ) : (
            <Navigate to="/login" />
          )
        }
      />
    </Routes>
  );
}