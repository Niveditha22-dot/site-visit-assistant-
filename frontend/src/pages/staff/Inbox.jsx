import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useAsync } from "../../hooks.js";
import { Badge, Drawer, Empty, ErrorBox, Spinner, visitTone } from "../../ui.jsx";
import { fmtDateTime } from "../../util.js";
import { Transcript } from "./Leads.jsx";

export default function Inbox() {
  const { call } = useOutletContext();
  const handoffs = useAsync(() => call("/api/handoffs"));
  const visits = useAsync(() => call("/api/bookings"));
  const [open, setOpen] = useState(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  async function mark(id, status) {
    setBusyId(id);
    setError("");
    try {
      await call(`/api/bookings/${id}/status`, { method: "PATCH", body: { status } });
      visits.reload();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <h1 className="small">Inbox</h1>
      <p className="muted">Serious buyers handed to you by the assistant, and your site visits.</p>

      <h2>Handoffs</h2>
      {handoffs.loading ? <Spinner label="Loading handoffs" />
        : handoffs.error ? <ErrorBox error={handoffs.error} onRetry={handoffs.reload} />
        : handoffs.data.length === 0 ? <Empty title="Nothing waiting" hint="New handoffs appear here with the chat summary." />
        : handoffs.data.map((h) => (
          <article key={h.id} className="card handoff">
            <header>
              <div><strong>{h.lead_name}</strong> <a href={`tel:${h.phone}`}>{h.phone}</a></div>
              <Badge tone="info">{h.reason}</Badge>
            </header>
            <pre>{h.summary}</pre>
            <footer>
              <span className="muted">To {h.executive || "unassigned"} · {fmtDateTime(h.created_at)}</span>
              <button className="btn ghost" onClick={() => setOpen(h)}>View full chat</button>
            </footer>
          </article>
        ))}

      <h2>Site visits</h2>
      {error && <p className="field-error" role="alert">{error}</p>}
      {visits.loading ? <Spinner label="Loading visits" />
        : visits.error ? <ErrorBox error={visits.error} onRetry={visits.reload} />
        : visits.data.length === 0 ? <Empty title="No visits yet" />
        : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>When</th><th>Buyer</th><th>Project</th><th>Status</th><th /></tr></thead>
              <tbody>
                {visits.data.map((v) => (
                  <tr key={v.id}>
                    <td>{fmtDateTime(v.starts_at)}</td>
                    <td>{v.lead_name}<br /><span className="muted">{v.phone}</span></td>
                    <td>{v.project}</td>
                    <td><Badge tone={visitTone(v.status)}>{v.status.replace("_", " ")}</Badge></td>
                    <td className="right">
                      {v.status === "booked" && (
                        <>
                          <button className="btn ghost" disabled={busyId === v.id} onClick={() => mark(v.id, "visited")}>Visited</button>{" "}
                          <button className="btn ghost" disabled={busyId === v.id} onClick={() => mark(v.id, "no_show")}>No-show</button>
                        </>
                      )}
                    </td>
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
