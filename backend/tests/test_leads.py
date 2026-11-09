import os

import psycopg
import pytest

from app.leads import norm_phone, norm_email, upsert_lead

DB = os.environ["TEST_DATABASE_URL"]


def test_phone_normalisation():
    assert norm_phone("+91 98765-43210") == "9876543210"
    assert norm_phone("09876543210") == "9876543210"
    with pytest.raises(ValueError):
        norm_phone("12345")


def test_email_normalisation():
    assert norm_email("  Amit@Demo.TEST ") == "amit@demo.test"
    assert norm_email("") is None


@pytest.fixture
def conn():
    with psycopg.connect(DB) as c:
        c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        c.execute(open("backend/db/schema.sql").read())
        c.execute("INSERT INTO users (name,email,password_hash,role) "
                  "VALUES ('Ex','ex@demo.test','x','executive')")
        yield c


def test_same_phone_from_two_sources_merges(conn):
    a, created_a = upsert_lead(conn, name="Hardik", phone="+91 90000 00001", source="property_portal")
    b, created_b = upsert_lead(conn, name="Hardik P", phone="9000000001", source="social_ad")
    assert created_a and not created_b and a == b
    assert conn.execute("SELECT count(*) FROM leads").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM lead_sources WHERE lead_id=%s", (a,)).fetchone()[0] == 2


def test_same_email_different_phone_merges(conn):
    a, _ = upsert_lead(conn, name="N", phone="9000000002", email="n@demo.test", source="website")
    b, created = upsert_lead(conn, name="N", phone="9000000099", email="N@demo.test", source="hoarding_call")
    assert a == b and not created
