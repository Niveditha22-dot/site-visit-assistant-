import os
import hashlib
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

import psycopg
from dotenv import load_dotenv

load_dotenv()

from app.booking import book_slot  # noqa: E402  (run as: python backend/seed.py)

IST = ZoneInfo("Asia/Kolkata")


def hash_pw(p: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(p.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + "$" + h.hex()


def ist(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=IST)


def main():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE users, projects, fact_sheet_items, leads, lead_sources, "
                    "visit_slots, bookings, chat_messages, handoffs, reminders, ad_spend "
                    "RESTART IDENTITY CASCADE")
        # demo users (demo logins go in deployment.md)
        users = [("Meera Desai", "head@demo.test", "sales_head"),
                 ("Rahul Mehta", "rahul@demo.test", "executive"),
                 ("Priya Nair", "priya@demo.test", "executive"),
                 ("Admin", "admin@demo.test", "admin")]
        for n, e, r in users:
            cur.execute("INSERT INTO users (name,email,password_hash,role) VALUES (%s,%s,%s,%s)",
                        (n, e, hash_pw("demo1234"), r))
        # projects (RERA numbers are placeholders, ASSUMPTION)
        cur.execute("INSERT INTO projects (name,rera_number,address,lat,lng) VALUES "
                    "('Project 1','DEMO-RERA-0001','Demo Road, Ahmedabad',23.0300,72.5800),"
                    "('Project 2','DEMO-RERA-0002','Sample Circle, Ahmedabad',23.0700,72.5200)")
        facts = [("Configurations", "2 BHK and 3 BHK apartments."),
                 ("Price range", "Indicative range across both projects is Rs 65 lakh to Rs 1.2 crore. "
                                 "Final price is confirmed by the sales team."),
                 ("Amenities", "Clubhouse, garden, covered parking, 24x7 security.")]  # ASSUMPTION
        # NOTE: possession date is left out on purpose, so the assistant must say
        # "a person will confirm" and hand off.
        for pid in (1, 2):
            for t, v in facts:
                cur.execute("INSERT INTO fact_sheet_items (project_id,topic,value) VALUES (%s,%s,%s)",
                            (pid, t, v))
        # ad spend per source (ASSUMPTION: split of Rs 30 lakh a month)
        for src, amt in [("property_portal", 1200000), ("social_ad", 1000000),
                         ("website", 300000), ("hoarding_call", 500000)]:
            for m in (date(2026, 10, 1), date(2026, 11, 1)):
                cur.execute("INSERT INTO ad_spend (source,month,amount_inr) VALUES (%s,%s,%s)",
                            (src, m, amt))
        # leads: 3 from the brief + extras
        leads = [("Hardik Patel", "9000000001", "hardik@demo.test", "property_portal", 1, "3 BHK", 110, "en"),
                 ("Nidhi Shah", "9000000002", "nidhi@demo.test", "social_ad", 2, "2 BHK", 80, "gu"),
                 ("Kavita Joshi", "9000000003", "kavita@demo.test", "hoarding_call", 2, "2 BHK", 75, "hi"),
                 ("Amit Trivedi", "9000000004", "amit@demo.test", "website", 1, "3 BHK", 120, "en"),
                 ("Sneha Parmar", "9000000005", "sneha@demo.test", "property_portal", 2, "2 BHK", 70, "gu"),
                 ("Vikram Rana", "9000000006", None, "social_ad", 1, "2 BHK", 85, "hi"),
                 ("Pooja Bhatt", "9000000007", "pooja@demo.test", "website", 2, "3 BHK", 100, "en"),
                 ("Jayesh Modi", "9000000008", "jayesh@demo.test", "hoarding_call", 1, "2 BHK", 68, "gu")]
        for i, (n, ph, em, src, pid, wants, bud, lang) in enumerate(leads):
            cur.execute("""INSERT INTO leads (name,phone_norm,email_norm,project_id,wants,budget_max_lakh,
                           language,consent_given,consent_at,executive_id)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE,now(),%s) RETURNING id""",
                        (n, ph, em, pid, wants, bud, lang, 2 + (i % 2)))
            lead_id = cur.fetchone()[0]
            cur.execute("INSERT INTO lead_sources (lead_id,source) VALUES (%s,%s)", (lead_id, src))
        # future free slots: next 14 days, 6 per day per project
        base = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
        for d in range(1, 15):
            for pid in (1, 2):
                for hh in (10, 11, 12, 15, 16, 17):
                    cur.execute("INSERT INTO visit_slots (project_id,starts_at) VALUES (%s,%s)",
                                (pid, base + timedelta(days=d, hours=hh)))
        # first assistant replies, so the dashboard has response times (leads created 5-12 days ago)
        delays = [90, 45, 120, 60, 200, 75, 110, 50]
        for i, delay in enumerate(delays, start=1):
            cur.execute("UPDATE leads SET created_at = now() - make_interval(days => %s) WHERE id=%s", (i + 4, i))
            cur.execute("""INSERT INTO chat_messages (lead_id, sender, content, created_at)
                           SELECT id, 'buyer', 'Hi, I am interested in a flat.', created_at + interval '5 seconds'
                           FROM leads WHERE id=%s""", (i,))
            cur.execute("""INSERT INTO chat_messages (lead_id, sender, content, created_at)
                           SELECT id, 'assistant', 'Hello! I can answer your questions and book a site visit.',
                                  created_at + make_interval(secs => %s) FROM leads WHERE id=%s""", (delay, i))
        # past visits (ASSUMPTION: invented history so the dashboard shows show-up rate and cost per visit)
        past = {2: "visited", 3: "visited", 4: "no_show", 5: "visited", 6: "no_show", 7: "visited", 8: "visited"}
        for n, (lead_id, status) in enumerate(past.items(), start=1):
            cur.execute("SELECT project_id FROM leads WHERE id=%s", (lead_id,))
            pid = cur.fetchone()[0]
            cur.execute("INSERT INTO visit_slots (project_id, starts_at) VALUES (%s,%s) RETURNING id",
                        (pid, base - timedelta(days=n, hours=-11)))
            cur.execute("INSERT INTO bookings (lead_id, slot_id, status) VALUES (%s,%s,%s)",
                        (lead_id, cur.fetchone()[0], status))
        # the brief's sample lead Hardik has an upcoming booking (date shifted to stay in the future)
        cur.execute("SELECT id FROM visit_slots WHERE project_id=1 AND starts_at=%s", (base + timedelta(days=2, hours=11),))
        book_slot(conn, 1, cur.fetchone()[0])
    print("Seeded.")


if __name__ == "__main__":
    main()
