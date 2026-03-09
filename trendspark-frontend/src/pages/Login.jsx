import { useState } from "react";
import axios from "axios";

export default function Login() {

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = async () => {
    try {
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);

      const res = await axios.post(
        "http://127.0.0.1:8000/api/v1/auth/login",
        params,
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );

      localStorage.setItem("token", res.data.access_token);
      window.location.reload();

    } catch (err) {
      console.log("LOGIN ERROR:", err.response?.data);
      alert("Login failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-white">

      <div className="bg-slate-900 p-10 rounded-xl w-96">
        <h2 className="text-2xl mb-6">Login</h2>

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