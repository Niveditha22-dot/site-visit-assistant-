import csv
import io
import os
import time
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import psycopg
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from . import agent, booking, reports
from .auth import make_token, require_roles, verify_password
from .db import get_conn
from .leads import SOURCES, upsert_lead

IST = ZoneInfo("Asia/Kolkata")
app = FastAPI(title="Site visit assistant")
app.add_middleware(CORSMiddleware,
                   allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
                   allow_methods=["*"], allow_headers=["*"])

STAFF = require_roles("executive", "sales_head", "admin")
MANAGER = require_roles("sales_head", "admin")
BUYER = require_roles("buyer")


def rows(conn, sql, params=None):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params or {})
        return cur.fetchall()


def own_lead_or_404(conn, user, lead_id):
    """Executives may only touch their own leads; managers see all."""
    r = conn.execute("SELECT executive_id FROM leads WHERE id=%s", (lead_id,)).fetchone()
    if not r or (user["role"] == "executive" and r[0] != user["id"]):
        raise HTTPException(404, "Lead not found")


# ---------- auth ----------
class LoginIn(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def login(body: LoginIn, conn=Depends(get_conn)):
    row = conn.execute("SELECT id, name, role, password_hash FROM users WHERE email = %s",
                       (body.email.strip().lower(),)).fetchone()
    if not row or not verify_password(body.password, row[3]):
        raise HTTPException(401, "Wrong email or password")
    return {"token": make_token(row[0], row[2]), "name": row[1], "role": row[2]}


# ---------- public: projects, slots, intake ----------
@app.get("/api/projects")
def projects(conn=Depends(get_conn)):
    return rows(conn, "SELECT id, name, rera_number, address, lat, lng FROM projects ORDER BY id")


@app.get("/api/slots")
def slots(project_id: Optional[int] = None, conn=Depends(get_conn)):
    return booking.free_slots(conn, project_id, 60)


class IntakeIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str
    email: Optional[str] = None
    project_id: Optional[int] = None
    wants: Optional[str] = Field(default=None, max_length=40)
    budget_max_lakh: Optional[int] = Field(default=None, ge=1, le=1000)
    language: str = Field(default="en", pattern="^(en|hi|gu)$")
    consent: bool = False


@app.post("/api/intake")
def intake(body: IntakeIn, conn=Depends(get_conn)):
    """Public. Source is set by the server. Returns only a chat token, never whether the phone already existed,
    and a returning buyer starts a fresh chat (earlier chats stay visible to staff only)."""
    try:
        lead_id, _ = upsert_lead(conn, name=body.name, phone=body.phone, email=body.email, source="website",
                                 project_id=body.project_id, wants=body.wants,
                                 budget_max_lakh=body.budget_max_lakh, language=body.language)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if not body.consent:
        return {"chat_token": None, "needs_consent": True}
    conn.execute("UPDATE leads SET consent_given=TRUE, consent_at=COALESCE(consent_at, now()), opted_out=FALSE "
                 "WHERE id=%s", (lead_id,))
    return {"chat_token": make_token(lead_id, "buyer", since=int(time.time())), "needs_consent": False}


# ---------- buyer: chat and bookings ----------
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


def _since(user):
    return datetime.fromtimestamp(user["since"], timezone.utc) if user.get("since") else None


def _chat_allowed(conn, lead_id):
    r = conn.execute("SELECT consent_given, opted_out FROM leads WHERE id=%s", (lead_id,)).fetchone()
    if not r or not r[0] or r[1]:
        raise HTTPException(403, "Chat is off: consent is missing or you have opted out")


@app.post("/api/chat")
def chat(body: ChatIn, user=Depends(BUYER), conn=Depends(get_conn)):
    _chat_allowed(conn, user["id"])
    recent = conn.execute("""SELECT count(*) FROM chat_messages WHERE lead_id=%s AND sender='buyer'
                             AND created_at > now() - interval '1 hour'""", (user["id"],)).fetchone()[0]
    if recent >= 60:
        raise HTTPException(429, "Too many messages. Please try again later.")
    return agent.respond(conn, user["id"], body.message, since=_since(user))


@app.get("/api/chat/messages")
def chat_messages(user=Depends(BUYER), conn=Depends(get_conn)):
    return rows(conn, """SELECT id, sender, content, created_at FROM chat_messages
                         WHERE lead_id=%(l)s AND (%(s)s::timestamptz IS NULL OR created_at >= %(s)s)
                         ORDER BY id""", {"l": user["id"], "s": _since(user)})


@app.post("/api/chat/opt-out")
def opt_out(user=Depends(BUYER), conn=Depends(get_conn)):
    conn.execute("UPDATE leads SET opted_out=TRUE WHERE id=%s", (user["id"],))
    return {"opted_out": True}


class BookIn(BaseModel):
    slot_id: int


@app.post("/api/bookings")
def book(body: BookIn, user=Depends(BUYER), conn=Depends(get_conn)):
    try:
        bid = booking.book_slot(conn, user["id"], body.slot_id)
    except booking.SlotTaken:
        raise HTTPException(409, "That slot was just taken. Please pick another.")
    except booking.NotAllowed as e:
        raise HTTPException(400, str(e))
    return booking.booking_info(conn, bid)


@app.get("/api/bookings")
def list_bookings(user=Depends(STAFF), conn=Depends(get_conn)):
    return rows(conn, """
        SELECT b.id, b.status, s.starts_at, p.name AS project, l.id AS lead_id, l.name AS lead_name, l.phone_norm AS phone
        FROM bookings b JOIN visit_slots s ON s.id = b.slot_id JOIN projects p ON p.id = s.project_id
        JOIN leads l ON l.id = b.lead_id
        WHERE (NOT %(mine)s OR l.executive_id = %(uid)s)
        ORDER BY s.starts_at DESC LIMIT 100""", {"mine": user["role"] == "executive", "uid": user["id"]})


@app.get("/api/bookings/mine")
def my_bookings(user=Depends(BUYER), conn=Depends(get_conn)):
    ids = conn.execute("SELECT id FROM bookings WHERE lead_id=%s ORDER BY id DESC", (user["id"],)).fetchall()
    return [booking.booking_info(conn, r[0]) for r in ids]


@app.post("/api/bookings/{booking_id}/cancel")
def cancel(booking_id: int, user=Depends(BUYER), conn=Depends(get_conn)):
    done = conn.execute("UPDATE bookings SET status='cancelled' WHERE id=%s AND lead_id=%s AND status='booked' "
                        "RETURNING id", (booking_id, user["id"])).fetchone()
    if not done:
        raise HTTPException(404, "No active booking found")
    conn.execute("DELETE FROM reminders WHERE booking_id=%s AND sent_at IS NULL", (booking_id,))
    return {"cancelled": True}


# ---------- staff: leads ----------
@app.post("/api/leads/import")
async def import_leads(file: UploadFile = File(...), user=Depends(STAFF), conn=Depends(get_conn)):
    """CSV columns: name, phone, email, source, project, wants"""
    if file.size and file.size > 1_000_000:
        raise HTTPException(413, "File too large")
    text = (await file.read()).decode("utf-8-sig")
    projects_by_name = {r[1].lower(): r[0] for r in conn.execute("SELECT id, name FROM projects").fetchall()}
    created = merged = 0
    errors = []
    for i, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        try:
            _, was_new = upsert_lead(conn, name=row["name"], phone=row["phone"], email=row.get("email"),
                                     source=(row.get("source") or "").strip(),
                                     project_id=projects_by_name.get((row.get("project") or "").strip().lower()),
                                     wants=(row.get("wants") or None))
            created += was_new
            merged += not was_new
        except (ValueError, KeyError) as e:
            errors.append({"row": i, "reason": str(e)})
    return {"created": created, "merged": merged, "errors": errors}


@app.get("/api/leads")
def list_leads(source: Optional[str] = None, user=Depends(STAFF), conn=Depends(get_conn)):
    if source and source not in SOURCES:
        raise HTTPException(422, "unknown source")
    return rows(conn, """
        SELECT l.id, l.name, l.phone_norm AS phone, l.wants, l.budget_max_lakh, l.language,
               l.consent_given, p.name AS project, u.name AS executive,
               COALESCE(array_agg(DISTINCT s.source) FILTER (WHERE s.source IS NOT NULL), '{}') AS sources,
               (SELECT b.status FROM bookings b WHERE b.lead_id = l.id ORDER BY b.id DESC LIMIT 1) AS visit_status
        FROM leads l
        LEFT JOIN projects p ON p.id = l.project_id
        LEFT JOIN users u ON u.id = l.executive_id
        LEFT JOIN lead_sources s ON s.lead_id = l.id
        WHERE (%(src)s::text IS NULL OR EXISTS
                 (SELECT 1 FROM lead_sources x WHERE x.lead_id = l.id AND x.source = %(src)s))
          AND (NOT %(mine)s OR l.executive_id = %(uid)s)
        GROUP BY l.id, p.name, u.name
        ORDER BY l.created_at DESC, l.id DESC""",
        {"src": source, "mine": user["role"] == "executive", "uid": user["id"]})


@app.get("/api/leads/{lead_id}/messages")
def lead_messages(lead_id: int, user=Depends(STAFF), conn=Depends(get_conn)):
    own_lead_or_404(conn, user, lead_id)
    return rows(conn, "SELECT id, sender, content, flagged, created_at FROM chat_messages WHERE lead_id=%s ORDER BY id",
                (lead_id,))


# ---------- staff: handoffs, flagged chats, visit status, reminders ----------
@app.get("/api/handoffs")
def handoffs(user=Depends(STAFF), conn=Depends(get_conn)):
    return rows(conn, """
        SELECT h.id, h.lead_id, l.name AS lead_name, l.phone_norm AS phone, h.reason, h.summary,
               u.name AS executive, h.created_at
        FROM handoffs h JOIN leads l ON l.id = h.lead_id LEFT JOIN users u ON u.id = h.executive_id
        WHERE (NOT %(mine)s OR h.executive_id = %(uid)s)
        ORDER BY h.created_at DESC LIMIT 100""", {"mine": user["role"] == "executive", "uid": user["id"]})


@app.get("/api/flagged")
def flagged(user=Depends(MANAGER), conn=Depends(get_conn)):
    return rows(conn, """
        SELECT m.id, m.lead_id, l.name AS lead_name, m.content, m.flag_reason, m.created_at
        FROM chat_messages m JOIN leads l ON l.id = m.lead_id
        WHERE m.flagged AND m.reviewed_at IS NULL ORDER BY m.id DESC LIMIT 100""")


@app.post("/api/flagged/{message_id}/review")
def review(message_id: int, user=Depends(MANAGER), conn=Depends(get_conn)):
    r = conn.execute("UPDATE chat_messages SET reviewed_at=now() WHERE id=%s AND flagged RETURNING id",
                     (message_id,)).fetchone()
    if not r:
        raise HTTPException(404, "Not found")
    return {"reviewed": True}


class StatusIn(BaseModel):
    status: str = Field(pattern="^(visited|no_show|cancelled)$")


@app.patch("/api/bookings/{booking_id}/status")
def set_status(booking_id: int, body: StatusIn, user=Depends(STAFF), conn=Depends(get_conn)):
    r = conn.execute("SELECT lead_id FROM bookings WHERE id=%s", (booking_id,)).fetchone()
    if not r:
        raise HTTPException(404, "Booking not found")
    own_lead_or_404(conn, user, r[0])
    conn.execute("UPDATE bookings SET status=%s WHERE id=%s", (body.status, booking_id))
    if body.status == "cancelled":
        conn.execute("DELETE FROM reminders WHERE booking_id=%s AND sent_at IS NULL", (booking_id,))
    return {"status": body.status}


@app.get("/api/reminders")
def list_reminders(user=Depends(STAFF), conn=Depends(get_conn)):
    return rows(conn, """
        SELECT r.id, r.kind, r.due_at, r.sent_at, r.message, l.name AS lead_name
        FROM reminders r JOIN bookings b ON b.id = r.booking_id JOIN leads l ON l.id = b.lead_id
        WHERE (NOT %(mine)s OR l.executive_id = %(uid)s) ORDER BY r.due_at LIMIT 200""",
        {"mine": user["role"] == "executive", "uid": user["id"]})


@app.post("/api/reminders/run")
def run_reminders(user=Depends(MANAGER), conn=Depends(get_conn)):
    """Mock sender: marks due reminders as sent. Skips cancelled bookings and opted-out buyers."""
    done = conn.execute("""UPDATE reminders r SET sent_at = now()
                           FROM bookings b JOIN leads l ON l.id = b.lead_id
                           WHERE r.booking_id = b.id AND r.sent_at IS NULL AND r.due_at <= now()
                             AND b.status = 'booked' AND NOT l.opted_out RETURNING r.id""").fetchall()
    return {"sent": len(done)}


@app.get("/api/dashboard")
def dashboard(user=Depends(MANAGER), conn=Depends(get_conn)):
    return reports.dashboard(conn)


# ---------- admin: fact sheet and slots ----------
class FactIn(BaseModel):
    project_id: int
    topic: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=500)


@app.get("/api/fact-sheet")
def get_facts(user=Depends(MANAGER), conn=Depends(get_conn)):
    return rows(conn, """SELECT f.id, f.project_id, p.name AS project, f.topic, f.value
                         FROM fact_sheet_items f JOIN projects p ON p.id = f.project_id ORDER BY f.project_id, f.id""")


@app.post("/api/fact-sheet")
def add_fact(body: FactIn, user=Depends(MANAGER), conn=Depends(get_conn)):
    try:
        fid = conn.execute("INSERT INTO fact_sheet_items (project_id, topic, value) VALUES (%s,%s,%s) RETURNING id",
                           (body.project_id, body.topic, body.value)).fetchone()[0]
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(422, "Unknown project")
    return {"id": fid}


@app.put("/api/fact-sheet/{fact_id}")
def edit_fact(fact_id: int, body: FactIn, user=Depends(MANAGER), conn=Depends(get_conn)):
    r = conn.execute("UPDATE fact_sheet_items SET project_id=%s, topic=%s, value=%s WHERE id=%s RETURNING id",
                     (body.project_id, body.topic, body.value, fact_id)).fetchone()
    if not r:
        raise HTTPException(404, "Not found")
    return {"id": fact_id}


@app.delete("/api/fact-sheet/{fact_id}")
def delete_fact(fact_id: int, user=Depends(MANAGER), conn=Depends(get_conn)):
    if not conn.execute("DELETE FROM fact_sheet_items WHERE id=%s RETURNING id", (fact_id,)).fetchone():
        raise HTTPException(404, "Not found")
    return {"deleted": True}


class SlotIn(BaseModel):
    project_id: int
    starts_at: datetime


@app.post("/api/slots")
def add_slot(body: SlotIn, user=Depends(MANAGER), conn=Depends(get_conn)):
    when = body.starts_at if body.starts_at.tzinfo else body.starts_at.replace(tzinfo=IST)
    if when <= datetime.now(timezone.utc):
        raise HTTPException(422, "Slot must be in the future")
    try:
        sid = conn.execute("INSERT INTO visit_slots (project_id, starts_at) VALUES (%s,%s) RETURNING id",
                           (body.project_id, when)).fetchone()[0]
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "That slot already exists")
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(422, "Unknown project")
    return {"id": sid}


@app.delete("/api/slots/{slot_id}")
def delete_slot(slot_id: int, user=Depends(MANAGER), conn=Depends(get_conn)):
    if conn.execute("SELECT 1 FROM bookings WHERE slot_id=%s", (slot_id,)).fetchone():
        raise HTTPException(409, "This slot has bookings and cannot be deleted")
    if not conn.execute("DELETE FROM visit_slots WHERE id=%s RETURNING id", (slot_id,)).fetchone():
        raise HTTPException(404, "Not found")
    return {"deleted": True}
