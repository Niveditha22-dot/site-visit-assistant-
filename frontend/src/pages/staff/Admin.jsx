import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../../api.js";
import { useAsync } from "../../hooks.js";
import { Empty, ErrorBox, Spinner } from "../../ui.jsx";
import { fmtDateTime } from "../../util.js";

export default function Admin() {
  const { call } = useOutletContext();
  const projects = useAsync(() => api("/api/projects"));
  return (
    <>
      <h1 className="small">Admin</h1>
      <p className="muted">The assistant answers only from this fact sheet, and only offers these visit slots.</p>
      {projects.loading ? <Spinner /> : projects.error ? <ErrorBox error={projects.error} onRetry={projects.reload} /> : (
        <>
          <FactSheet call={call} projects={projects.data} />
          <Slots call={call} projects={projects.data} />
        </>
      )}
    </>
  );
}

function FactSheet({ call, projects }) {
  const facts = useAsync(() => call("/api/fact-sheet"));
  const [draft, setDraft] = useState({ project_id: projects[0]?.id || "", topic: "", value: "" });
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");

  async function run(fn) {
    setError("");
    try { await fn(); facts.reload(); } catch (e) { setError(e.message); }
  }
  const add = (e) => {
    e.preventDefault();
    run(async () => {
      await call("/api/fact-sheet", { method: "POST", body: { ...draft, project_id: Number(draft.project_id) } });
      setDraft({ ...draft, topic: "", value: "" });
    });
  };
  const save = () => run(async () => {
    await call(`/api/fact-sheet/${editing.id}`, { method: "PUT", body: { project_id: editing.project_id, topic: editing.topic, value: editing.value } });
    setEditing(null);
  });
  const remove = (f) => window.confirm(`Delete "${f.topic}" for ${f.project}?`) && run(() => call(`/api/fact-sheet/${f.id}`, { method: "DELETE" }));

  return (
    <section>
      <h2>Fact sheet</h2>
      {error && <p className="field-error" role="alert">{error}</p>}
      {facts.loading ? <Spinner label="Loading fact sheet" />
        : facts.error ? <ErrorBox error={facts.error} onRetry={facts.reload} />
        : facts.data.length === 0 ? <Empty title="No facts yet" hint="Add facts below. The assistant can't answer without them." />
        : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Project</th><th>Topic</th><th>Fact</th><th /></tr></thead>
              <tbody>
                {facts.data.map((f) => editing?.id === f.id ? (
                  <tr key={f.id}>
                    <td>{f.project}</td>
                    <td><input value={editing.topic} onChange={(e) => setEditing({ ...editing, topic: e.target.value })} /></td>
                    <td><input value={editing.value} onChange={(e) => setEditing({ ...editing, value: e.target.value })} /></td>
                    <td className="right">
                      <button className="btn primary" onClick={save}>Save</button>{" "}
                      <button className="btn ghost" onClick={() => setEditing(null)}>Cancel</button>
                    </td>
                  </tr>
                ) : (
                  <tr key={f.id}>
                    <td>{f.project}</td><td>{f.topic}</td><td>{f.value}</td>
                    <td className="right">
                      <button className="btn ghost" onClick={() => setEditing({ id: f.id, project_id: f.project_id, topic: f.topic, value: f.value })}>Edit</button>{" "}
                      <button className="btn ghost danger" onClick={() => remove(f)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      <form className="card form inline" onSubmit={add}>
        <select value={draft.project_id} onChange={(e) => setDraft({ ...draft, project_id: e.target.value })} aria-label="Project">
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <input placeholder="Topic, e.g. Possession" value={draft.topic} onChange={(e) => setDraft({ ...draft, topic: e.target.value })} required maxLength={80} />
        <input placeholder="Fact, e.g. December 2027" value={draft.value} onChange={(e) => setDraft({ ...draft, value: e.target.value })} required maxLength={500} />
        <button className="btn primary">Add fact</button>
      </form>
    </section>
  );
}

function Slots({ call, projects }) {
  const slots = useAsync(() => api("/api/slots"));
  const [draft, setDraft] = useState({ project_id: projects[0]?.id || "", starts_at: "" });
  const [error, setError] = useState("");

  async function run(fn) {
    setError("");
    try { await fn(); slots.reload(); } catch (e) { setError(e.message); }
  }
  const add = (e) => {
    e.preventDefault();
    run(async () => {
      await call("/api/slots", { method: "POST", body: { project_id: Number(draft.project_id), starts_at: draft.starts_at } });
      setDraft({ ...draft, starts_at: "" });
    });
  };

  return (
    <section>
      <h2>Visit slots</h2>
      <p className="muted small-print">Times are India time. Slots that already have a booking can't be deleted.</p>
      {error && <p className="field-error" role="alert">{error}</p>}
      <form className="card form inline" onSubmit={add}>
        <select value={draft.project_id} onChange={(e) => setDraft({ ...draft, project_id: e.target.value })} aria-label="Project">
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <input type="datetime-local" value={draft.starts_at} onChange={(e) => setDraft({ ...draft, starts_at: e.target.value })} required aria-label="Slot start" />
        <button className="btn primary">Add slot</button>
      </form>
      {slots.loading ? <Spinner label="Loading slots" />
        : slots.error ? <ErrorBox error={slots.error} onRetry={slots.reload} />
        : slots.data.length === 0 ? <Empty title="No free slots" hint="Add some above." />
        : (
          <div className="table-wrap short">
            <table>
              <thead><tr><th>Project</th><th>When</th><th /></tr></thead>
              <tbody>
                {slots.data.map((s) => (
                  <tr key={s.slot_id}>
                    <td>{s.project}</td><td>{fmtDateTime(s.starts_at)}</td>
                    <td className="right"><button className="btn ghost danger" onClick={() => run(() => call(`/api/slots/${s.slot_id}`, { method: "DELETE" }))}>Delete</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </section>
  );
}
