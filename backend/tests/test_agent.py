import psycopg
import pytest

from app import agent
from app.booking import free_slots
from .helpers import fresh_db


@pytest.fixture
def conn(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    url = fresh_db()
    with psycopg.connect(url) as c:
        yield c


def count(conn, sql, *p):
    return conn.execute(sql, p).fetchone()[0]


def test_price_request_gets_no_price_and_a_handoff(conn):
    r = agent.respond(conn, 4, "What is your best price? Can I get a discount?")
    assert "can't quote" in r["reply"] and r["handoff"]
    assert count(conn, "SELECT count(*) FROM handoffs WHERE lead_id=4") == 1
    assert count(conn, "SELECT count(*) FROM chat_messages WHERE lead_id=4 AND sender='buyer' AND flagged") == 1


def test_asking_for_a_person_hands_off_immediately(conn):
    r = agent.respond(conn, 4, "I want to talk to a real person")
    assert "contact you" in r["reply"]
    assert conn.execute("SELECT reason FROM handoffs WHERE lead_id=4").fetchone()[0] == "buyer asked for a person"


def test_missing_fact_says_a_person_will_confirm(conn):
    r = agent.respond(conn, 4, "When is possession?")
    assert "confirm" in r["reply"] and r["handoff"]
    assert count(conn, "SELECT count(*) FROM handoffs WHERE lead_id=4") == 1


def test_known_fact_is_answered_from_fact_sheet(conn):
    r = agent.respond(conn, 2, "What amenities do you have?")
    assert "Clubhouse" in r["reply"] and "RERA" in r["reply"] and not r["handoff"]


def test_bad_model_output_is_blocked(conn, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(agent, "claude_reply", lambda *a, **k: "Sure, I can give you a special discount of 5 percent.")
    r = agent.respond(conn, 4, "Tell me about the project")
    assert "can't quote" in r["reply"]


def test_model_failure_falls_back_to_rules(conn, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")

    def boom(*a, **k):
        raise RuntimeError("api down")
    monkeypatch.setattr(agent, "claude_reply", boom)
    assert "Clubhouse" in agent.respond(conn, 2, "amenities?")["reply"]


def test_chat_booking_takes_a_real_free_slot_once(conn):
    sid = free_slots(conn)[0]["slot_id"]
    lead = agent._lead(conn, 2)
    assert agent.run_tool(conn, lead, "book_slot", {"slot_id": sid}, {})["ok"]
    other = agent._lead(conn, 3)
    assert agent.run_tool(conn, other, "book_slot", {"slot_id": sid}, {}) == {"ok": False, "error": "slot_taken"}
    assert sid not in [s["slot_id"] for s in free_slots(conn, limit=500)]


def test_rule_mode_books_with_reply_text(conn):
    sid = free_slots(conn, 2)[0]["slot_id"]
    r = agent.respond(conn, 2, f"book {sid}")
    assert "booked" in r["reply"] and "RERA" in r["reply"]


def test_tool_rejects_bad_details(conn):
    lead = agent._lead(conn, 2)
    assert not agent.run_tool(conn, lead, "save_lead_details", {"budget_max_lakh": 5000}, {})["ok"]
    assert not agent.run_tool(conn, lead, "book_slot", {"slot_id": "1; DROP TABLE leads"}, {})["ok"]
    assert not agent.run_tool(conn, lead, "delete_everything", {}, {})["ok"]


def test_replies_follow_the_buyers_language(conn):
    # lead 2 (Nidhi) prefers Gujarati, lead 3 (Kavita) Hindi; lead 4 (Amit) English
    assert "ડિસ્કાઉન્ટ" in agent.respond(conn, 2, "Give me a discount")["reply"]
    assert "छूट" in agent.respond(conn, 3, "Give me a discount")["reply"]


def test_claude_tool_loop_runs_tools_then_answers(conn, monkeypatch):
    """Drives claude_reply with a fake SDK client: tool call first, then a text answer."""
    class Block:
        def __init__(self, **k):
            self.__dict__.update(k)

    class Resp:
        def __init__(self, stop, content):
            self.stop_reason, self.content = stop, content

    class FakeMessages:
        calls = 0

        def create(self, **kw):
            FakeMessages.calls += 1
            if FakeMessages.calls == 1:
                return Resp("tool_use", [Block(type="tool_use", id="t1", name="get_free_slots", input={})])
            assert kw["messages"][-1]["content"][0]["type"] == "tool_result"
            return Resp("end_turn", [Block(type="text", text="Here are some free slots.")])

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr("anthropic.Anthropic", lambda: FakeClient())
    r = agent.respond(conn, 4, "I would like to see the site")
    assert r["reply"] == "Here are some free slots." and FakeMessages.calls == 2


def test_rule_mode_understands_a_hindi_amenities_question(conn):
    assert "Clubhouse" in agent.respond(conn, 3, "सुविधाएँ क्या हैं?")["reply"]
