import { useEffect } from "react";

export function Spinner({ label = "Loading" }) {
  return (
    <div className="state" role="status">
      <span className="spinner" aria-hidden="true" /> {label}…
    </div>
  );
}

export function ErrorBox({ error, onRetry }) {
  return (
    <div className="state error" role="alert">
      <p>{error?.message || "Something went wrong."}</p>
      {onRetry && <button className="btn ghost" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function Empty({ title, hint }) {
  return (
    <div className="state empty">
      <strong>{title}</strong>
      {hint && <p>{hint}</p>}
    </div>
  );
}

export function Badge({ tone = "neutral", children }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Drawer({ title, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="overlay" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <header>
          <h2>{title}</h2>
          <button className="btn ghost" onClick={onClose} aria-label="Close">Close</button>
        </header>
        <div className="drawer-body">{children}</div>
      </aside>
    </div>
  );
}

export function visitTone(status) {
  return { visited: "good", booked: "info", no_show: "warn", cancelled: "neutral" }[status] || "neutral";
}
