import { useRef, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useAsync } from "../../hooks.js";
import { Badge, Drawer, Empty, ErrorBox, Spinner, visitTone } from "../../ui.jsx";
import { SOURCE_LABELS, fmtDateTime } from "../../util.js";

export default function Leads() {
  const { call } = useOutletContext();
  const [source, setSource] = useState("");
  const leads = useAsync(() => call(`/api/leads${source ? `?source=${source}` : ""}`), [source]);
  const [open, setOpen] = useState(null);
  const [result, setResult] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const fileRef = useRef(null);

  async function upload(e) {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    setUploadError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      setResult(await call("/api/leads/import", { method: "POST", form }));
      leads.reload();
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="small">Leads</h1>
          <p className="muted">One list from every source. Repeat enquiries are merged by phone or email.</p>
        </div>
        <div className="actions">
          <select value={source} onChange={(e) => setSource(e.target.value)} aria-label="Filter by source">
            <option value="">All sources</option>
            {Object.entries(SOURCE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <input ref={fileRef} type="file" accept=".csv,text/csv" hidden onChange={upload} />
          <button className="btn ghost" onClick={() => fileRef.current.click()} disabled={uploading}>
            {uploading ? "Importing…" : "Import CSV"}
          </button>
        </div>
      </div>

      {uploadError && <p className="field-error" role="alert">{uploadError}</p>}
      {result && (
        <div className="card note">
          <strong>Import finished:</strong> {result.created} new, {result.merged} merged as duplicates
          {result.errors.length > 0 && (
            <ul>{result.errors.map((e) => <li key={e.row}>Row {e.row}: {e.reason}</li>)}</ul>
          )}
        </div>
      )}
      <p className="muted small-print">CSV columns: name, phone, email, source, project, wants. <a href="/sample-leads.csv" download>Download a sample</a>.</p>

      {leads.loading ? <Spinner label="Loading leads" />
        : leads.error ? <ErrorBox error={leads.error} onRetry={leads.reload} />
        : leads.data.length === 0 ? <Empty title="No leads yet" hint="Import a CSV or wait for new enquiries." />
        : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Project</th><th>Wants</th><th>Sources</th><th>Executive</th><th>Visit</th></tr></thead>
              <tbody>
                {leads.data.map((l) => (
                  <tr key={l.id} className="click" onClick={() => setOpen(l)} tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && setOpen(l)}>
                    <td><strong>{l.name}</strong><br /><span className="muted">{l.phone}</span></td>
                    <td>{l.project || "n/a"}</td>
                    <td>{l.wants || "n/a"}{l.budget_max_lakh ? ` · up to ₹${l.budget_max_lakh} L` : ""}</td>
                    <td>{l.sources.map((s) => <Badge key={s}>{SOURCE_LABELS[s] || s}</Badge>)}</td>
                    <td>{l.executive || "n/a"}</td>
                    <td>{l.visit_status ? <Badge tone={visitTone(l.visit_status)}>{l.visit_status.replace("_", " ")}</Badge> : <span className="muted">none</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      {open && (
        <Drawer title={`${open.name}'s chat`} onClose={() => setOpen(null)}>
          <Transcript leadId={open.id} call={call} />
        </Drawer>
      )}
    </>
  );
}

export function Transcript({ leadId, call }) {
  const msgs = useAsync(() => call(`/api/leads/${leadId}/messages`), [leadId]);
  if (msgs.loading) return <Spinner label="Loading chat" />;
  if (msgs.error) return <ErrorBox error={msgs.error} onRetry={msgs.reload} />;
  if (msgs.data.length === 0) return <Empty title="No messages yet" />;
  return (
    <div className="messages">
      {msgs.data.map((m) => (
        <div key={m.id} className={`bubble ${m.sender === "buyer" ? "buyer" : "assistant"}`}>
          {m.content}
          <small>{fmtDateTime(m.created_at)}{m.flagged ? " · flagged" : ""}</small>
        </div>
      ))}
    </div>
  );
}
