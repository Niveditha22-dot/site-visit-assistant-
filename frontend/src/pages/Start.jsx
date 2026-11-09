import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, store } from "../api.js";
import { useAsync } from "../hooks.js";
import { LANGUAGES } from "../util.js";

export default function Start() {
  const navigate = useNavigate();
  const projects = useAsync(() => api("/api/projects"));
  const [form, setForm] = useState({ name: "", phone: "", language: "en", project_id: "", consent: false });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (form.name.trim().length < 2) return setError("Please enter your name.");
    if (form.phone.replace(/\D/g, "").length < 10) return setError("Please enter a 10-digit mobile number.");
    if (!form.consent) return setError("Please tick the box to continue. We only contact you with your consent.");
    setBusy(true);
    try {
      const res = await api("/api/intake", {
        method: "POST",
        body: {
          name: form.name.trim(), phone: form.phone, language: form.language, consent: true,
          project_id: form.project_id ? Number(form.project_id) : null,
        },
      });
      store.set("chat", { token: res.chat_token, language: form.language, name: form.name.trim() });
      navigate("/chat");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page narrow">
      <p className="eyebrow">Ahmedabad homes · 2 and 3 BHK</p>
      <h1>Find your home. See it in person.</h1>
      <p className="lead">Ask us anything about our projects, and book a site visit at a time that suits you. We reply within minutes, in English, Hindi or Gujarati.</p>

      <form className="card form" onSubmit={submit} noValidate>
        <label>Your name
          <input value={form.name} onChange={set("name")} autoComplete="name" />
        </label>
        <label>Mobile number
          <input value={form.phone} onChange={set("phone")} inputMode="tel" autoComplete="tel" placeholder="98765 43210" />
        </label>
        <div className="row">
          <label>Language
            <select value={form.language} onChange={set("language")}>
              {LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </label>
          <label>Project (optional)
            <select value={form.project_id} onChange={set("project_id")}>
              <option value="">No preference</option>
              {(projects.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
        </div>
        <label className="check">
          <input type="checkbox" checked={form.consent} onChange={set("consent")} />
          <span>I agree to be contacted about this enquiry by chat and message. I can opt out at any time.</span>
        </label>
        {error && <p className="field-error" role="alert">{error}</p>}
        <button className="btn primary" disabled={busy}>{busy ? "Starting…" : "Start chat"}</button>
      </form>

      <footer className="footnote">
        {(projects.data || []).map((p) => <span key={p.id}>{p.name}: RERA no. {p.rera_number}</span>)}
        <Link to="/staff/login">Staff sign in</Link>
      </footer>
    </main>
  );
}
