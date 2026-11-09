# Decisions and assumptions

## Decisions
- **Stack:** FastAPI + PostgreSQL (psycopg 3), React + Vite for the frontend, Claude API for the assistant.
- **No double booking:** a partial unique index on `bookings(slot_id) WHERE status = 'booked'`.
  The database is the final guard. Booking runs in one transaction; a lost race raises `SlotTaken`.
- **Duplicate check:** a lead matches on normalised phone (last 10 digits) or lowercase email.
  A duplicate merges into the existing lead, fills only empty fields, and keeps every source in `lead_sources`.
- **Source is set by the server** on web intake, so a client cannot fake it.
- **Roles:** `executive` sees only their own leads; `sales_head` and `admin` see all.
- **Assignment:** a new lead goes to the executive with the fewest leads.
- **Reminders:** created at booking time (1 day and 2 hours before) and mocked as database rows.
  Each message includes the project's RERA number.
- **Consent:** booking is refused if the lead has no consent or has opted out.

## Assistant and safety decisions
- **Guardrails live in code, not only in the prompt.** Requests for a final price or discount, and requests for a person,
  are caught before the model is called. Every model reply is also filtered for price or discount language and replaced with a
  safe message plus a handoff if it matches.
- **The model can only act through four tools** (free slots, book, save details, request a person). Each tool runs for the
  current buyer only, validates its inputs, and booking goes through the same database-guarded `book_slot` as the website.
- **If Claude fails or no API key is set,** a rule-based mode answers from the fact sheet with the same guardrails.
- **Missing fact:** the assistant says a person will confirm and hands off; the chat is flagged for the sales head's daily review.
- **Handoff summary is built by code** (details plus last six messages), not by the model, so it is predictable and free.
- **Buyer chat uses a signed token from intake.** Intake never reveals whether a phone number already existed, and a
  returning buyer starts a fresh chat; earlier chats are visible to staff only.
- **Limits:** 1,000 characters per message and 60 messages per buyer per hour (cost and abuse control).
- **One upcoming visit per buyer;** cancelling frees the slot and removes unsent reminders.
- **Opt-out** stops chat and reminders. Reminders are mocked: the sender marks due rows as sent.

## Frontend decisions
- React + Vite, plain CSS, hash routing (works on any static host without rewrite rules). 8 screens in two areas:
  buyer (start, chat, site visit) and staff (leads, inbox, dashboard, review, admin).
- Design: warm off-white, one deep green accent, serif headings, large type and tap targets, mobile-first. Every list has
  loading, empty and error states. Managers-only screens are hidden from executives and also blocked by the server.
- The chat token and staff token live in sessionStorage, so closing the tab signs the user out.
- Buyers see only free slots; a slot taken a moment ago returns a clear message and the list refreshes.

## Assumptions (label these in the TDD)
- One visit per slot (the brief gives no slot capacity).
- RERA numbers, amenities and project addresses are made-up demo data.
- Ad spend per source is made-up; the brief only gives the total of Rs 30 lakh a month.
- The fact sheet deliberately has no possession date, to exercise the "a person will confirm" path.
- Dashboard history (past visits, response times) is invented seed data. Hardik's sample booking is shifted to a future date.
- Demo logins use a shared demo password and exist only in seed data.
