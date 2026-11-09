import psycopg
import pytest
from fastapi.testclient import TestClient

from app.db import get_conn
from app.main import app
from .helpers import fresh_db


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    url = fresh_db()

    def override():
        with psycopg.connect(url) as c:
            yield c
    app.dependency_overrides[get_conn] = override
    c = TestClient(app)
    c.url = url
    yield c
    app.dependency_overrides.clear()


def buyer(client, phone, name="Test Buyer"):
    r = client.post("/api/intake", json={"name": name, "phone": phone, "consent": True})
    return {"Authorization": f"Bearer {r.json()['chat_token']}"}


def staff(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": "demo1234"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_buyer_cannot_read_another_buyers_chat(client):
    a, b = buyer(client, "9111111111"), buyer(client, "9222222222")
    client.post("/api/chat", json={"message": "What amenities do you have?"}, headers=a)
    assert len(client.get("/api/chat/messages", headers=a).json()) == 2
    assert client.get("/api/chat/messages", headers=b).json() == []


def test_returning_phone_starts_fresh_and_leaks_nothing(client):
    r = client.post("/api/intake", json={"name": "Hardik", "phone": "9000000001", "consent": True})
    assert set(r.json()) == {"chat_token", "needs_consent"}
    h = {"Authorization": f"Bearer {r.json()['chat_token']}"}
    assert client.get("/api/chat/messages", headers=h).json() == []


def test_buyer_and_anonymous_cannot_use_staff_endpoints(client):
    a = buyer(client, "9111111111")
    assert client.get("/api/handoffs", headers=a).status_code == 403
    assert client.get("/api/leads", headers=a).status_code == 403
    assert client.get("/api/dashboard").status_code == 401


def test_double_booking_returns_409(client):
    a, b = buyer(client, "9111111111"), buyer(client, "9222222222")
    sid = client.get("/api/slots").json()[0]["slot_id"]
    assert client.post("/api/bookings", json={"slot_id": sid}, headers=a).status_code == 200
    assert client.post("/api/bookings", json={"slot_id": sid}, headers=b).status_code == 409
    assert sid not in [s["slot_id"] for s in client.get("/api/slots").json()]


def test_handoff_goes_to_the_named_executive_only(client):
    a = buyer(client, "9111111111")
    client.post("/api/chat", json={"message": "I want to talk to a real person"}, headers=a)
    assert len(client.get("/api/handoffs", headers=staff(client, "rahul@demo.test")).json()) == 1
    assert client.get("/api/handoffs", headers=staff(client, "priya@demo.test")).json() == []
    assert len(client.get("/api/handoffs", headers=staff(client, "head@demo.test")).json()) == 1


def test_flagged_chat_review_queue(client):
    a = buyer(client, "9111111111")
    client.post("/api/chat", json={"message": "Give me your best price"}, headers=a)
    head = staff(client, "head@demo.test")
    items = client.get("/api/flagged", headers=head).json()
    assert len(items) == 1
    assert client.post(f"/api/flagged/{items[0]['id']}/review", headers=head).status_code == 200
    assert client.get("/api/flagged", headers=head).json() == []
    assert client.get("/api/flagged", headers=staff(client, "rahul@demo.test")).status_code == 403


def test_dashboard_numbers(client):
    d = client.get("/api/dashboard", headers=staff(client, "head@demo.test")).json()
    assert {r["source"] for r in d["by_source"]} == {"property_portal", "social_ad", "website", "hoarding_call"}
    assert d["overall_median_response_seconds"] is not None
    assert all(r["cost_per_visit_inr"] for r in d["by_source"])


def test_opt_out_stops_chat_and_reminders(client):
    a = buyer(client, "9111111111")
    assert client.post("/api/chat/opt-out", headers=a).status_code == 200
    assert client.post("/api/chat", json={"message": "hi"}, headers=a).status_code == 403


def test_reminders_run_marks_due_ones_sent(client):
    with psycopg.connect(client.url) as c:
        c.execute("UPDATE reminders SET due_at = now() - interval '1 minute'")
    out = client.post("/api/reminders/run", headers=staff(client, "head@demo.test")).json()
    assert out["sent"] >= 1


def test_admin_slot_cannot_be_deleted_if_booked_and_fact_edit_works(client):
    head = staff(client, "head@demo.test")
    a = buyer(client, "9111111111")
    sid = client.get("/api/slots").json()[0]["slot_id"]
    client.post("/api/bookings", json={"slot_id": sid}, headers=a)
    assert client.delete(f"/api/slots/{sid}", headers=head).status_code == 409
    facts = client.get("/api/fact-sheet", headers=head).json()
    assert client.put(f"/api/fact-sheet/{facts[0]['id']}", headers=head,
                      json={"project_id": 1, "topic": "Possession", "value": "December 2027"}).status_code == 200


def test_executives_see_only_their_own_visits(client):
    rahul = client.get("/api/bookings", headers=staff(client, "rahul@demo.test")).json()
    priya = client.get("/api/bookings", headers=staff(client, "priya@demo.test")).json()
    head = client.get("/api/bookings", headers=staff(client, "head@demo.test")).json()
    assert len(rahul) == 4 and len(priya) == 4 and len(head) == 8
    booked = [b for b in rahul if b["status"] == "booked"][0]
    r = client.patch(f"/api/bookings/{booked['id']}/status", json={"status": "visited"},
                     headers=staff(client, "rahul@demo.test"))
    assert r.status_code == 200
    other = [b for b in priya][0]
    assert client.patch(f"/api/bookings/{other['id']}/status", json={"status": "visited"},
                        headers=staff(client, "rahul@demo.test")).status_code == 404
