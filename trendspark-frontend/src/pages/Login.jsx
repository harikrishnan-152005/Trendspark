import { useState } from "react";
import { clearSession } from "../services/api";

export default function Login() {

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = async () => {
    try {
      setError("");

      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", password);

      const res = await fetch("http://127.0.0.1:8000/api/v1/auth/login", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok || !data.access_token) {
        throw new Error(data.detail || "Login failed");
      }

      clearSession();
      localStorage.setItem("token", data.access_token);
      window.location.href = "/";
    } catch (err) {
      console.error("Login failed", err);
      setError(err.message || "Login failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-white">

      <div className="bg-slate-900 p-10 rounded-xl w-96">
        <h2 className="text-2xl mb-6">Login</h2>

        {error && (
          <p className="mb-4 rounded bg-red-950 px-3 py-2 text-sm text-red-300">
            {error}
          </p>
        )}

        <input
          className="w-full p-3 mb-4 rounded bg-slate-800"
          placeholder="Username"
          onChange={(e) => setUsername(e.target.value)}
        />

        <input
          type="password"
          className="w-full p-3 mb-4 rounded bg-slate-800"
          placeholder="Password"
          onChange={(e) => setPassword(e.target.value)}
        />

        <button
          onClick={handleLogin}
          className="w-full bg-indigo-600 p-3 rounded"
        >
          Login
        </button>

      </div>

    </div>
  );
}
