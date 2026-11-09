import re

import psycopg

SOURCES = {"property_portal", "social_ad", "website", "hoarding_call"}


def norm_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) < 10:
        raise ValueError("phone number must have at least 10 digits")
    return digits[-10:]            # drops +91 / 0 prefixes


def norm_email(raw):
    raw = (raw or "").strip().lower()
    if not raw:
        return None
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", raw):
        raise ValueError("invalid email")
    return raw


def _least_busy_executive(conn):
    return conn.execute(
        """SELECT u.id FROM users u LEFT JOIN leads l ON l.executive_id = u.id
           WHERE u.role = 'executive' GROUP BY u.id ORDER BY count(l.id), u.id LIMIT 1"""
    ).fetchone()[0]


def _find_existing(conn, phone, email):
    return conn.execute(
        """SELECT id FROM leads
           WHERE phone_norm = %s OR (%s::text IS NOT NULL AND email_norm = %s)
           ORDER BY id LIMIT 1""", (phone, email, email)).fetchone()


def upsert_lead(conn, *, name, phone, email=None, source, project_id=None,
                wants=None, budget_max_lakh=None, language="en"):
    """Returns (lead_id, created). A repeat phone or email merges into the existing lead."""
    if source not in SOURCES:
        raise ValueError(f"unknown source '{source}'")
    phone, email = norm_phone(phone), norm_email(email)
    existing = _find_existing(conn, phone, email)
    created = existing is None
    if created:
        try:
            with conn.transaction():          # savepoint, so a race falls through to merge
                lead_id = conn.execute(
                    """INSERT INTO leads (name, phone_norm, email_norm, project_id, wants,
                                          budget_max_lakh, language, executive_id)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (name.strip(), phone, email, project_id, wants, budget_max_lakh,
                     language, _least_busy_executive(conn))).fetchone()[0]
        except psycopg.errors.UniqueViolation:
            lead_id, created = _find_existing(conn, phone, email)[0], False
    else:
        lead_id = existing[0]
    if not created:                           # fill gaps only, never overwrite
        conn.execute(
            """UPDATE leads SET email_norm = COALESCE(email_norm, %s),
                                project_id = COALESCE(project_id, %s),
                                wants = COALESCE(wants, %s),
                                budget_max_lakh = COALESCE(budget_max_lakh, %s)
               WHERE id = %s""", (email, project_id, wants, budget_max_lakh, lead_id))
    conn.execute(
        """INSERT INTO lead_sources (lead_id, source)
           SELECT %s, %s WHERE NOT EXISTS
             (SELECT 1 FROM lead_sources WHERE lead_id = %s AND source = %s)""",
        (lead_id, source, lead_id, source))
    return lead_id, created
