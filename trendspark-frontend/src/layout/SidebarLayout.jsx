import { Link, useLocation } from "react-router-dom";
import { useContext } from "react";
import { ThemeContext } from "../context/ThemeContext";
import { clearSession } from "../services/api";

export default function SidebarLayout({ children }) {
  const location = useLocation();
  const { dark, setDark } = useContext(ThemeContext);

  return (
    <div className="flex min-h-screen bg-slate-950 text-white">

      {/* SIDEBAR */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 p-6 flex flex-col justify-between">

        {/* TOP SECTION */}
        <div>
          <h1 className="text-2xl font-bold text-indigo-400 mb-10">
            🚀 TrendSpark
          </h1>

          <nav className="space-y-4">
            <SidebarLink
              to="/"
              label="Dashboard"
              active={location.pathname === "/"}
            />

            <SidebarLink
              to="/analytics"
              label="Analytics"
              active={location.pathname === "/analytics"}
            />

            <SidebarLink
              to="/history"
              label="Report History"
              active={location.pathname === "/history"}
            />
          </nav>
        </div>

        {/* BOTTOM SECTION */}
        <div className="space-y-4">

          {/* LOGOUT */}
          <button
            onClick={() => {
              clearSession();
              window.location.reload();
            }}
            className="w-full bg-red-600 px-4 py-2 rounded-lg hover:bg-red-500 transition"
          >
            Logout
          </button>

        </div>

      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 p-10 overflow-y-auto">
        {children}
      </main>

    </div>
  );
}

function SidebarLink({ to, label, active }) {
  return (
    <Link
      to={to}
      className={`block px-4 py-2 rounded-lg transition ${
        active
          ? "bg-indigo-600"
          : "hover:bg-slate-800"
      }`}
    >
      {label}
    </Link>
  );
}
