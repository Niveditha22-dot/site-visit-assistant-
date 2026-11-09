import os
import threading

import psycopg
import pytest

from app.booking import book_slot, SlotTaken, NotAllowed

DB = os.environ["TEST_DATABASE_URL"]


@pytest.fixture
def setup():
    with psycopg.connect(DB) as c:
        c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        c.execute(open("backend/db/schema.sql").read())
        c.execute("INSERT INTO projects (name,rera_number,address) VALUES ('P','R-1','addr')")
        c.execute("INSERT INTO visit_slots (project_id,starts_at) VALUES (1, now() + interval '3 days')")
        for i in range(5):
            c.execute("INSERT INTO leads (name,phone_norm,consent_given) VALUES (%s,%s,TRUE)",
                      (f"L{i}", f"900000000{i}"))
    return [1, 2, 3, 4, 5]


def test_only_one_booking_wins(setup):
    results, barrier = [], threading.Barrier(len(setup))

    def worker(lead_id):
        with psycopg.connect(DB) as conn:
            barrier.wait()
            try:
                book_slot(conn, lead_id, 1)
                results.append("ok")
            except SlotTaken:
                results.append("taken")

    threads = [threading.Thread(target=worker, args=(i,)) for i in setup]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count("ok") == 1
    assert results.count("taken") == len(setup) - 1


def test_no_consent_cannot_book(setup):
    with psycopg.connect(DB) as c:
        c.execute("UPDATE leads SET consent_given=FALSE WHERE id=1")
        with pytest.raises(NotAllowed):
            book_slot(c, 1, 1)


def test_reminders_created_with_rera_number(setup):
    with psycopg.connect(DB) as c:
        booking_id = book_slot(c, 1, 1)
        rows = c.execute("SELECT kind, message FROM reminders WHERE booking_id=%s ORDER BY kind",
                         (booking_id,)).fetchall()
    assert [r[0] for r in rows] == ["1_day", "2_hours"]
    assert all("RERA no. R-1" in r[1] for r in rows)
