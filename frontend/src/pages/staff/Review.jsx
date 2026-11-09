import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useAsync } from "../../hooks.js";
import { Badge, Drawer, Empty, ErrorBox, Spinner } from "../../ui.jsx";
import { fmtDateTime } from "../../util.js";
import { Transcript } from "./Leads.jsx";

export default function Review() {
  const { call } = useOutletContext();
  const flagged = useAsync(() => call("/api/flagged"));
  const reminders = useAsync(() => call("/api/reminders"));
  const [open, setOpen] = useState(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  async function review(id) {
    setError("");
    try {
      await call(`/api/flagged/${id}/review`, { method: "POST" });
      flagged.reload();
    } catch (e) {
      setError(e.message);
    }
  }

  async function runReminders() {
    setError("");
    setMsg("");
    try {
      const r = await call("/api/reminders/run", { method: "POST" });
      setMsg(`${r.sent} reminder${r.sent === 1 ? "" : "s"} sent (mock).`);
      reminders.reload();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <>
      <h1 className="small">Review</h1>
      <p className="muted">Chats where the assistant was unsure or a buyer asked about price. Check them daily.</p>
      {error && <p className="field-error" role="alert">{error}</p>}

      <h2>Flagged chats</h2>
      {flagged.loading ? <Spinner label="Loading flagged chats" />
        : flagged.error ? <ErrorBox error={flagged.error} onRetry={flagged.reload} />
        : flagged.data.length === 0 ? <Empty title="All reviewed" hint="Nothing is waiting for review." />
        : flagged.data.map((f) => (
          <article key={f.id} className="card handoff">
            <header>
              <div><strong>{f.lead_name}</strong></div>
              <Badge tone="warn">{f.flag_reason}</Badge>
            </header>
            <p className="quote">“{f.content}”</p>
            <footer>
              <span className="muted">{fmtDateTime(f.created_at)}</span>
              <span>
                <button className="btn ghost" onClick={() => setOpen(f)}>View chat</button>{" "}
                <button className="btn primary" onClick={() => review(f.id)}>Mark reviewed</button>
              </span>
            </footer>
          </article>
        ))}

      <div className="page-head">
        <h2>Reminders</h2>
        <button className="btn ghost" onClick={runReminders}>Send due reminders (mock)</button>
      </div>
      {msg && <p className="notice">{msg}</p>}
      {reminders.loading ? <Spinner label="Loading reminders" />
        : reminders.error ? <ErrorBox error={reminders.error} onRetry={reminders.reload} />
        : reminders.data.length === 0 ? <Empty title="No reminders" hint="They are created when a visit is booked." />
        : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Buyer</th><th>Type</th><th>Due</th><th>Status</th><th>Message</th></tr></thead>
              <tbody>
                {reminders.data.map((r) => (
                  <tr key={r.id}>
                    <td>{r.lead_name}</td>
                    <td>{r.kind === "1_day" ? "1 day before" : "2 hours before"}</td>
                    <td>{fmtDateTime(r.due_at)}</td>
                    <td>{r.sent_at ? <Badge tone="good">sent</Badge> : <Badge>scheduled</Badge>}</td>
                    <td className="msg-cell">{r.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      {open && (
        <Drawer title={`${open.lead_name}'s chat`} onClose={() => setOpen(null)}>
          <Transcript leadId={open.lead_id} call={call} />
        </Drawer>
      )}
    </>
  );
}
