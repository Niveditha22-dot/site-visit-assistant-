import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, store } from "../api.js";
import { useAsync } from "../hooks.js";
import { ErrorBox, Spinner, Empty } from "../ui.jsx";
import { fmtDay, fmtTime, fmtDateTime } from "../util.js";

const GREETING = {
  en: "Hello, and welcome. I can answer questions about our projects and arrange a site visit. What are you looking for?",
  hi: "नमस्ते! मैं हमारे प्रोजेक्ट्स के बारे में आपके सवालों के जवाब दे सकता हूँ और साइट विज़िट बुक कर सकता हूँ। आप क्या ढूंढ रहे हैं?",
  gu: "નમસ્તે! હું અમારા પ્રોજેક્ટ્સ વિશે તમારા પ્રશ્નોના જવાબ આપી શકું છું અને સાઇટ વિઝિટ બુક કરી શકું છું. તમે શું શોધી રહ્યા છો?",
};
const CHIPS = {
  en: ["What amenities do you have?", "Show me free visit slots", "I want to talk to a person"],
  hi: ["सुविधाएँ क्या हैं?", "साइट विज़िट के स्लॉट दिखाएँ", "मुझे किसी व्यक्ति से बात करनी है"],
  gu: ["સુવિધાઓ શું છે?", "સાઇટ વિઝિટના સ્લોટ બતાવો", "મારે કોઈ સાથે વાત કરવી છે"],
};

export default function Chat() {
  const session = store.get("chat");
  if (!session?.token) return <Navigate to="/" replace />;
  return <ChatInner session={session} />;
}

function ChatInner({ session }) {
  const navigate = useNavigate();
  const [tab, setTab] = useState("chat");
  const [optedOut, setOptedOut] = useState(false);
  const projects = useAsync(() => api("/api/projects"));

  function expired() {
    store.del("chat");
    navigate("/");
  }

  async function optOut() {
    if (!window.confirm("Stop all messages from us? You can start a new chat later.")) return;
    try {
      await api("/api/chat/opt-out", { method: "POST", token: session.token });
      setOptedOut(true);
    } catch (e) {
      if (e.status === 401) expired();
    }
  }

  return (
    <main className="page chat-page">
      <header className="chat-head">
        <div>
          <h1 className="small">Hello, {session.name}</h1>
          <p className="muted">Ask about our homes or book a visit.</p>
        </div>
        <nav className="tabs" aria-label="Sections">
          <button className={tab === "chat" ? "on" : ""} onClick={() => setTab("chat")}>Chat</button>
          <button className={tab === "visit" ? "on" : ""} onClick={() => setTab("visit")}>Site visit</button>
        </nav>
      </header>

      {optedOut ? (
        <div className="card"><p>You have opted out. We won't message you again. Thank you for your time.</p></div>
      ) : tab === "chat" ? (
        <ChatPanel session={session} onExpired={expired} onOpenVisit={() => setTab("visit")} />
      ) : (
        <VisitPanel session={session} onExpired={expired} />
      )}

      <footer className="footnote">
        {(projects.data || []).map((p) => <span key={p.id}>{p.name}: RERA no. {p.rera_number}</span>)}
        {!optedOut && <button className="linklike" onClick={optOut}>Stop messages</button>}
      </footer>
    </main>
  );
}

function ChatPanel({ session, onExpired, onOpenVisit }) {
  const history = useAsync(() => api("/api/chat/messages", { token: session.token }));
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [handoff, setHandoff] = useState(false);
  const endRef = useRef(null);
  const lang = session.language || "en";

  useEffect(() => { if (history.data) setMessages(history.data); }, [history.data]);
  useEffect(() => { endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" }); }, [messages, sending]);
  useEffect(() => { if (history.error?.status === 401) onExpired(); }, [history.error]);

  async function send(msg) {
    const content = (msg ?? text).trim();
    if (!content || sending) return;
    setError("");
    setText("");
    setSending(true);
    setMessages((m) => [...m, { id: "tmp" + Date.now(), sender: "buyer", content }]);
    try {
      const res = await api("/api/chat", { method: "POST", token: session.token, body: { message: content } });
      setMessages((m) => [...m, { id: "r" + Date.now(), sender: "assistant", content: res.reply }]);
      if (res.handoff) setHandoff(true);
    } catch (e) {
      if (e.status === 401) return onExpired();
      setError(e.message);
      setText(content);
      setMessages((m) => m.slice(0, -1));
    } finally {
      setSending(false);
    }
  }

  if (history.loading) return <Spinner label="Opening your chat" />;
  if (history.error && history.error.status !== 401) return <ErrorBox error={history.error} onRetry={history.reload} />;

  return (
    <section className="chat card">
      <div className="messages" aria-live="polite">
        <div className="bubble assistant">{GREETING[lang]}</div>
        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.sender === "buyer" ? "buyer" : "assistant"}`}>{m.content}</div>
        ))}
        {sending && <div className="bubble assistant typing" aria-label="Typing"><span /><span /><span /></div>}
        {handoff && <p className="notice">A member of our team has been given this chat and will contact you.</p>}
        <div ref={endRef} />
      </div>
      {messages.length === 0 && (
        <div className="chips">
          {CHIPS[lang].map((c, i) => (
            <button key={c} className="chip" onClick={() => (i === 1 ? onOpenVisit() : send(c))}>{c}</button>
          ))}
        </div>
      )}
      {error && <p className="field-error" role="alert">{error}</p>}
      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input value={text} onChange={(e) => setText(e.target.value)} maxLength={1000}
               placeholder="Type your message" aria-label="Message" disabled={sending} />
        <button className="btn primary" disabled={sending || !text.trim()}>Send</button>
      </form>
    </section>
  );
}

function VisitPanel({ session, onExpired }) {
  const mine = useAsync(() => api("/api/bookings/mine", { token: session.token }));
  const slots = useAsync(() => api("/api/slots"));
  const [picked, setPicked] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [projectFilter, setProjectFilter] = useState("");

  useEffect(() => { if (mine.error?.status === 401) onExpired(); }, [mine.error]);

  if (mine.loading || slots.loading) return <Spinner label="Loading visit options" />;
  if (mine.error) return <ErrorBox error={mine.error} onRetry={mine.reload} />;
  if (slots.error) return <ErrorBox error={slots.error} onRetry={slots.reload} />;

  const active = (mine.data || []).find((b) => b.status === "booked" && new Date(b.starts_at) > new Date());

  async function confirm() {
    setBusy(true);
    setError("");
    try {
      await api("/api/bookings", { method: "POST", token: session.token, body: { slot_id: picked.slot_id } });
      setPicked(null);
      mine.reload();
      slots.reload();
    } catch (e) {
      if (e.status === 401) return onExpired();
      setError(e.message);
      if (e.status === 409) { setPicked(null); slots.reload(); }
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (!window.confirm("Cancel this site visit?")) return;
    setBusy(true);
    setError("");
    try {
      await api(`/api/bookings/${active.booking_id}/cancel`, { method: "POST", token: session.token });
      mine.reload();
      slots.reload();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (active) {
    return (
      <section className="card visit">
        <p className="eyebrow">Your site visit</p>
        <h2>{fmtDateTime(active.starts_at)}</h2>
        <p>{active.project}<br />{active.address}</p>
        {active.map && <p><a className="btn ghost" href={active.map} target="_blank" rel="noreferrer">Open location on map</a></p>}
        <p className="muted">RERA no. {active.rera}. We will remind you 1 day and 2 hours before.</p>
        {error && <p className="field-error" role="alert">{error}</p>}
        <button className="btn ghost danger" onClick={cancel} disabled={busy}>{busy ? "Cancelling…" : "Cancel this visit"}</button>
      </section>
    );
  }

  const list = (slots.data || []).filter((s) => !projectFilter || String(s.project_id) === projectFilter);
  const projectsInSlots = [...new Map((slots.data || []).map((s) => [s.project_id, s.project])).entries()];
  const byDay = list.reduce((acc, s) => {
    (acc[fmtDay(s.starts_at)] ||= []).push(s);
    return acc;
  }, {});

  return (
    <section className="card">
      <h2>Choose a time to visit</h2>
      <p className="muted">Only free slots are shown. Pick one and confirm.</p>
      {projectsInSlots.length > 1 && (
        <div className="chips">
          <button className={`chip ${projectFilter === "" ? "on" : ""}`} onClick={() => setProjectFilter("")}>All projects</button>
          {projectsInSlots.map(([id, name]) => (
            <button key={id} className={`chip ${projectFilter === String(id) ? "on" : ""}`} onClick={() => setProjectFilter(String(id))}>{name}</button>
          ))}
        </div>
      )}
      {error && <p className="field-error" role="alert">{error}</p>}
      {list.length === 0 ? (
        <Empty title="No free slots right now" hint="Ask in the chat and a team member will arrange a time." />
      ) : (
        Object.entries(byDay).slice(0, 5).map(([day, items]) => (
          <div key={day} className="day">
            <h3>{day}</h3>
            <div className="slot-grid">
              {items.map((s) => (
                <button key={s.slot_id} className={`slot ${picked?.slot_id === s.slot_id ? "on" : ""}`} onClick={() => setPicked(s)}>
                  {fmtTime(s.starts_at)}<small>{s.project}</small>
                </button>
              ))}
            </div>
          </div>
        ))
      )}
      {picked && (
        <div className="confirm-bar">
          <span>{picked.project}, {fmtDateTime(picked.starts_at)}</span>
          <button className="btn primary" onClick={confirm} disabled={busy}>{busy ? "Booking…" : "Confirm visit"}</button>
        </div>
      )}
    </section>
  );
}
