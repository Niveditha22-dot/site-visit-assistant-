import { useOutletContext } from "react-router-dom";
import { useAsync } from "../../hooks.js";
import { Empty, ErrorBox, Spinner } from "../../ui.jsx";
import { SOURCE_LABELS, fmtDuration, fmtINR, fmtPct } from "../../util.js";

export default function Dashboard() {
  const { call } = useOutletContext();
  const d = useAsync(() => call("/api/dashboard"));

  if (d.loading) return <Spinner label="Loading dashboard" />;
  if (d.error) return <ErrorBox error={d.error} onRetry={d.reload} />;
  const rows = d.data.by_source;
  if (rows.length === 0) return <Empty title="No data yet" hint="Numbers appear once leads and visits come in." />;

  const totalLeads = rows.reduce((a, r) => a + r.leads, 0);
  const totalVisits = rows.reduce((a, r) => a + r.visits, 0);
  const noShows = rows.reduce((a, r) => a + r.no_shows, 0);
  const maxCost = Math.max(...rows.map((r) => r.cost_per_visit_inr || 0), 1);

  return (
    <>
      <h1 className="small">Dashboard</h1>
      <p className="muted">By lead source. Figures are demo data.</p>
      <div className="stats">
        <div className="card stat"><span>Median first response</span><strong>{fmtDuration(d.data.overall_median_response_seconds)}</strong></div>
        <div className="card stat"><span>Leads</span><strong>{totalLeads}</strong></div>
        <div className="card stat"><span>Visits done</span><strong>{totalVisits}</strong></div>
        <div className="card stat"><span>Show-up rate</span><strong>{fmtPct(totalVisits + noShows ? totalVisits / (totalVisits + noShows) : null)}</strong></div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Source</th><th>Leads</th><th>Median response</th><th>Visits</th><th>Upcoming</th><th>Show-up</th><th>Lead to visit</th><th>Cost per visit</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.source}>
                <td><strong>{SOURCE_LABELS[r.source] || r.source}</strong></td>
                <td>{r.leads}</td>
                <td>{fmtDuration(r.median_response_seconds)}</td>
                <td>{r.visits}</td>
                <td>{r.upcoming}</td>
                <td>{fmtPct(r.show_up_rate)}</td>
                <td>{fmtPct(r.lead_to_visit_rate)}</td>
                <td>{fmtINR(r.cost_per_visit_inr)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Cost per visit</h2>
      <div className="bars">
        {rows.map((r) => (
          <div key={r.source} className="bar-row">
            <span>{SOURCE_LABELS[r.source] || r.source}</span>
            <div className="bar"><i style={{ width: `${((r.cost_per_visit_inr || 0) / maxCost) * 100}%` }} /></div>
            <b>{fmtINR(r.cost_per_visit_inr)}</b>
          </div>
        ))}
      </div>
    </>
  );
}
