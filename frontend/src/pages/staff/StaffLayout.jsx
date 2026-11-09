import { useCallback } from "react";
import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { api, store } from "../../api.js";

export default function StaffLayout() {
  const session = store.get("staff");
  if (!session?.token) return <Navigate to="/staff/login" replace />;
  return <Inner session={session} />;
}

function Inner({ session }) {
  const navigate = useNavigate();
  const isManager = session.role === "sales_head" || session.role === "admin";

  const logout = useCallback(() => {
    store.del("staff");
    navigate("/staff/login");
  }, [navigate]);

  const call = useCallback(
    (path, opts = {}) =>
      api(path, { ...opts, token: session.token }).catch((e) => {
        if (e.status === 401) logout();
        throw e;
      }),
    [session.token, logout]
  );

  return (
    <div className="staff">
      <header className="staff-head">
        <strong className="brand">Site visits</strong>
        <nav aria-label="Staff sections">
          <NavLink to="/staff/leads">Leads</NavLink>
          <NavLink to="/staff/inbox">Inbox</NavLink>
          {isManager && <NavLink to="/staff/dashboard">Dashboard</NavLink>}
          {isManager && <NavLink to="/staff/review">Review</NavLink>}
          {isManager && <NavLink to="/staff/admin">Admin</NavLink>}
        </nav>
        <div className="who">
          <span>{session.name}</span>
          <button className="linklike" onClick={logout}>Sign out</button>
        </div>
      </header>
      <main className="page wide">
        {/* Managers-only pages are also protected on the server; this just hides them from executives. */}
        <Outlet context={{ call, session, isManager }} />
      </main>
    </div>
  );
}
