import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, store } from "../../api.js";

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api("/api/auth/login", { method: "POST", body: form });
      store.set("staff", res);
      navigate("/staff/leads");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page narrow">
      <p className="eyebrow">Sales team</p>
      <h1>Sign in</h1>
      <form className="card form" onSubmit={submit}>
        <label>Email
          <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="username" required />
        </label>
        <label>Password
          <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="current-password" required />
        </label>
        {error && <p className="field-error" role="alert">{error}</p>}
        <button className="btn primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
      <div className="card demo">
        <strong>Demo logins</strong>
        <p>Sales head: head@demo.test<br />Executive: rahul@demo.test or priya@demo.test<br />Password for all: demo1234</p>
      </div>
      <footer className="footnote"><Link to="/">Back to the buyer site</Link></footer>
    </main>
  );
}
