from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import psycopg

IST = ZoneInfo("Asia/Kolkata")


class SlotTaken(Exception):
    ...


class NotAllowed(Exception):
    ...


def book_slot(conn, lead_id: int, slot_id: int) -> int:
    """Book one slot. The database's partial unique index is the final guard."""
    try:
        with conn.transaction():
            lead = conn.execute(
                "SELECT consent_given, opted_out FROM leads WHERE id=%s", (lead_id,)).fetchone()
            if not lead or not lead[0] or lead[1]:
                raise NotAllowed("lead has no consent or has opted out")
            already = conn.execute(
                """SELECT 1 FROM bookings b JOIN visit_slots s ON s.id = b.slot_id
                   WHERE b.lead_id=%s AND b.status='booked' AND s.starts_at > now()""",
                (lead_id,)).fetchone()
            if already:
                raise NotAllowed("you already have an upcoming visit; cancel it first to pick another")
            slot = conn.execute(
                """SELECT s.starts_at, p.name, p.rera_number
                   FROM visit_slots s JOIN projects p ON p.id = s.project_id
                   WHERE s.id=%s AND s.starts_at > now()""", (slot_id,)).fetchone()
            if not slot:
                raise NotAllowed("slot does not exist or is in the past")
            booking_id = conn.execute(
                "INSERT INTO bookings (lead_id, slot_id) VALUES (%s,%s) RETURNING id",
                (lead_id, slot_id)).fetchone()[0]
            starts_at, project, rera = slot
            now = datetime.now(timezone.utc)
            for kind, delta in (("1_day", timedelta(days=1)), ("2_hours", timedelta(hours=2))):
                due = starts_at - delta
                if due > now:
                    when = starts_at.astimezone(IST).strftime("%d %b, %I:%M %p")
                    conn.execute(
                        "INSERT INTO reminders (booking_id,kind,due_at,message) VALUES (%s,%s,%s,%s)",
                        (booking_id, kind, due,
                         f"Reminder: your site visit at {project} is on {when}. RERA no. {rera}."))
            return booking_id
    except psycopg.errors.UniqueViolation:
        raise SlotTaken(f"slot {slot_id} was just booked by someone else")


def when_text(dt) -> str:
    return dt.astimezone(IST).strftime("%a %d %b, %I:%M %p")


def free_slots(conn, project_id=None, limit=8):
    """Future slots with no active booking. The only slots a buyer can ever be offered."""
    rows = conn.execute(
        """SELECT s.id, s.project_id, p.name, s.starts_at
           FROM visit_slots s JOIN projects p ON p.id = s.project_id
           WHERE s.starts_at > now()
             AND (%s::int IS NULL OR s.project_id = %s)
             AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.slot_id = s.id AND b.status = 'booked')
           ORDER BY s.starts_at, s.id LIMIT %s""", (project_id, project_id, limit)).fetchall()
    return [{"slot_id": r[0], "project_id": r[1], "project": r[2],
             "starts_at": r[3].astimezone(IST).isoformat(), "when": when_text(r[3])} for r in rows]


def booking_info(conn, booking_id: int) -> dict:
    r = conn.execute(
        """SELECT b.id, b.status, s.starts_at, p.name, p.address, p.rera_number, p.lat, p.lng
           FROM bookings b JOIN visit_slots s ON s.id = b.slot_id JOIN projects p ON p.id = s.project_id
           WHERE b.id = %s""", (booking_id,)).fetchone()
    pin = f"https://www.google.com/maps?q={r[6]},{r[7]}" if r[6] is not None else None
    return {"booking_id": r[0], "status": r[1], "when": when_text(r[2]), "starts_at": r[2].astimezone(IST).isoformat(),
            "project": r[3], "address": r[4], "rera": r[5], "map": pin}
