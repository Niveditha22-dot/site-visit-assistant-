# Deployment

## Run locally
1. Install Python 3.10+ and PostgreSQL. Create two empty databases: one for the app, one for tests.
2. `python -m venv venv`, then activate it (Windows: `venv\Scripts\activate`).
3. `pip install -r backend/requirements.txt`
4. Copy `.env.example` to `.env` and fill in the values (names listed below).
5. Load the schema: `psql "$DATABASE_URL" -f backend/db/schema.sql`
6. Seed demo data: `python backend/seed.py`
7. Start the API from the `backend` folder: `uvicorn app.main:app --reload` (docs at http://localhost:8000/docs)
8. Start the frontend in a second terminal: `cd frontend`, copy `.env.example` to `.env`, then `npm install` and `npm run dev`.
   Open http://localhost:5173 (buyer site). Staff sign-in is at http://localhost:5173/#/staff/login.
9. Run tests from the repo root: `pytest` (the tests wipe the database named in `TEST_DATABASE_URL`).

## Environment variables (names only)
Backend: `DATABASE_URL`, `TEST_DATABASE_URL`, `SECRET_KEY`, `FRONTEND_ORIGIN`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` (optional)

Frontend: `VITE_API_URL` (the backend's public URL; build-time).

Without `ANTHROPIC_API_KEY` the assistant runs in a rule-based mode with the same guardrails.

## Demo logins (seed data only)
| Role | Email | Password |
|---|---|---|
| Sales head | head@demo.test | demo1234 |
| Executive | rahul@demo.test | demo1234 |
| Executive | priya@demo.test | demo1234 |
| Admin | admin@demo.test | demo1234 |

## How it is deployed
To be filled in after the first deploy (host, database, build and start commands).
