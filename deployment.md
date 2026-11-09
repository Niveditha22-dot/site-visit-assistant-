# Deployment guide
 
This guide covers three things: running the app on your own computer, the environment variables it needs, and putting it online (backend and database on Render, frontend on Vercel). Demo logins for the reviewer are in section 4.
 
**What runs where**
 
| Part | Local | Online (suggested) |
|---|---|---|
| Frontend (React + Vite) | http://localhost:5173 | Vercel |
| Backend (FastAPI) | http://localhost:8000 | Render web service |
| Database (PostgreSQL) | your own PostgreSQL | Render PostgreSQL |
| AI | Claude API (optional key) | Claude API (optional key) |
 
---
 
## 1. Run it locally
 
You need **Python 3.10 or newer**, **Node.js 18 or newer** (the LTS version from nodejs.org), **PostgreSQL**, and **Git**. Use two terminals, one for the backend and one for the frontend.
 
### Step 1. Get the code
```
git clone https://github.com/Niveditha22-dot/site-visit-assistant-.git
cd site-visit-assistant-
```
 
### Step 2. Create two empty databases
Open a terminal and connect to PostgreSQL. Enter your `postgres` password when asked:
```
psql -U postgres -h localhost
```
At the `postgres=#` prompt, run:
```
CREATE DATABASE sv;
CREATE DATABASE sv_test;
\q
```
`sv` is the app database. `sv_test` is used by the tests, which **erase it on every run**, so never point it at data you care about.
 
### Step 3. Create the Python environment and install packages
Windows:
```
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt
```
macOS or Linux:
```
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```
Your prompt should now start with `(venv)`. Use this terminal for everything on the backend side.
 
### Step 4. Create your `.env` file
Copy the example file (Windows: `copy .env.example .env`, macOS or Linux: `cp .env.example .env`) and fill it in:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/sv
TEST_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/sv_test
SECRET_KEY=<a long random string>
FRONTEND_ORIGIN=http://localhost:5173
ANTHROPIC_API_KEY=
```
- Make a secret key with: `python -c "import secrets; print(secrets.token_hex(32))"`
- If your password contains `@`, `#`, `:` or `/`, use a simpler password, because it breaks the connection string.
- `ANTHROPIC_API_KEY` is optional. Leave it empty and the assistant runs in its rule-based mode. Add a key from console.anthropic.com to get Claude's replies.
- Never commit `.env`. It is already listed in `.gitignore`.
### Step 5. Create the tables and load demo data
```
psql -U postgres -h localhost -d sv -f backend/db/schema.sql
python backend/seed.py
```
You should see a list of `CREATE TABLE` lines, then `Seeded.`
 
### Step 6. Run the tests (optional but recommended)
From the repo root, with `(venv)` active:
```
pytest
```
You should see `30 passed`.
 
### Step 7. Start the backend
```
cd backend
python -m uvicorn app.main:app --reload
```
Wait for `Uvicorn running on http://127.0.0.1:8000`. Check it by opening http://localhost:8000/api/projects, which should show a page of JSON. Leave this terminal running.
 
### Step 8. Start the frontend
Open a **second** terminal:
```
cd frontend
copy .env.example .env
npm install
npm run dev
```
(macOS or Linux: use `cp` instead of `copy`.) The file `frontend/.env` should contain `VITE_API_URL=http://localhost:8000`. Open **http://localhost:5173**.
 
### Step 9. Try it
1. **As a buyer:** enter a name and a 10-digit number, tick the consent box and click Start chat. Ask "What amenities do you have?". Ask for a discount and see the safe reply and the handoff notice. Open the Site visit tab, pick a time and confirm.
2. **As staff:** open http://localhost:5173/#/staff/login and sign in as `head@demo.test` / `demo1234`. Look at Leads, Inbox, Dashboard, Review and Admin.
---
 
## 2. Environment variables (names only)
 
| Variable | Where | Required | What it is |
|---|---|---|---|
| `DATABASE_URL` | backend | yes | PostgreSQL connection string for the app database |
| `TEST_DATABASE_URL` | backend (tests only) | for tests | A separate, disposable database. The tests erase it |
| `SECRET_KEY` | backend | yes | Long random string used to sign login tokens |
| `FRONTEND_ORIGIN` | backend | yes | The exact address of the frontend, for example `http://localhost:5173`. No trailing slash |
| `ANTHROPIC_API_KEY` | backend | no | Enables Claude replies. Without it a rule-based mode answers |
| `CLAUDE_MODEL` | backend | no | Overrides the default Claude model |
| `VITE_API_URL` | frontend (build time) | yes | The backend's address, for example `http://localhost:8000`. No trailing slash |
 
Values are never stored in this repository. `.env.example` files list the names only.
 
---
 
## 3. Put it online
 
Do the steps in order. The free tiers are enough for a demo. Allow about an hour.
 
### Part A. Database and backend on Render
 
**Step A1. Sign in.** Go to render.com and sign in with GitHub.
 
**Step A2. Create the database.** Click **New**, then **PostgreSQL**. Give it a name, pick a region near you (for example Singapore), choose the free plan, and click **Create Database**. Wait until it shows as available.
 
**Step A3. Copy the two database addresses.** On the database page, copy both of these:
 
- the **Internal Database URL**. The backend will use this one.
- the **External Database URL**. You will use this one from your laptop in the next step.
**Step A4. Load the tables and demo data from your laptop.** Open a terminal in the project folder with `(venv)` active, and run the commands for your system.
 
Windows (Command Prompt):
 
```
psql "PASTE_EXTERNAL_DATABASE_URL" -f backend/db/schema.sql
set DATABASE_URL=PASTE_EXTERNAL_DATABASE_URL
python backend/seed.py
```
 
macOS or Linux:
 
```
psql "PASTE_EXTERNAL_DATABASE_URL" -f backend/db/schema.sql
DATABASE_URL="PASTE_EXTERNAL_DATABASE_URL" python backend/seed.py
```
 
You should see the `CREATE TABLE` lines, then `Seeded.`
 
**Step A5. Create the web service.** In Render, click **New**, then **Web Service**. Choose **Build and deploy from a Git repository**, and select this repository.
 
**Step A6. Fill in the settings.** Enter these values:
 
| Setting | Value |
|---|---|
| Language | Python 3 |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance type | Free |
 
**Step A7. Add the environment variables.** Under **Environment Variables**, add these:
 
| Name | Value |
|---|---|
| `DATABASE_URL` | The **Internal** Database URL from Step A3 |
| `SECRET_KEY` | A new long random string |
| `FRONTEND_ORIGIN` | `http://localhost:5173` for now. You will change it in Part C |
| `ANTHROPIC_API_KEY` | Your key (optional) |
| `PYTHON_VERSION` | `3.12.3` |
 
**Step A8. Deploy and check.** Click **Create Web Service** and wait for the deploy to finish. Then open `https://YOUR-SERVICE.onrender.com/api/projects`. You should see a page of JSON. Copy this backend address, because you need it in Part B.
 
### Part B. Frontend on Vercel
 
**Step B1. Sign in.** Go to vercel.com and sign in with GitHub.
 
**Step B2. Import the project.** Click **Add New**, then **Project**, and import this repository.
 
**Step B3. Set the root folder.** Set **Root Directory** to `frontend`. Vercel should detect **Vite**. The default build command (`npm run build`) and output directory (`dist`) are correct.
 
**Step B4. Add the backend address.** Under **Environment Variables**, add `VITE_API_URL` and set it to your Render backend address from Step A8 (no trailing slash).
 
**Step B5. Deploy.** Click **Deploy**. When it finishes, copy the Vercel address, for example `https://your-project.vercel.app`.
 
### Part C. Connect them
 
**Step C1. Update the backend.** In Render, open the web service and go to **Environment**. Change `FRONTEND_ORIGIN` to your Vercel address (no trailing slash, no path).
 
**Step C2. Wait for the redeploy.** Save the change. Render redeploys the backend by itself.
 
**Step C3. Test it.** Open the Vercel address and run the checks in section 1, Step 9.
 
### Notes for the free tiers
 
- The free Render web service sleeps when idle. The first request after a pause can take about a minute. Open the app once before showing it to anyone.
- Free Render databases can expire after a trial period. If the app stops working later, check the database in the Render dashboard.
- The frontend uses hash routing (`/#/staff/login`), so no extra Vercel rewrite rules are needed.
---
 
## 4. Demo logins for the reviewer
 
Staff sign in at `/#/staff/login`. Buyers need no account: start a chat from the home page.
 
| Role | Email | Password | Can see |
|---|---|---|---|
| Sales head | head@demo.test | demo1234 | Everything, including dashboard, review and admin |
| Admin | admin@demo.test | demo1234 | Same as sales head |
| Executive | rahul@demo.test | demo1234 | Own leads, handoffs and visits only |
| Executive | priya@demo.test | demo1234 | Own leads, handoffs and visits only |
 
These accounts exist only in the seed data and hold no real personal data.
 
---
 
## 5. Troubleshooting
 
| Problem | Likely cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'psycopg'` | The virtual environment is not active. Run `venv\Scripts\activate` and use `python -m uvicorn ...` |
| The page says "Can't reach the server" | The backend is not running, or `VITE_API_URL` is wrong. Open `/api/projects` on the backend address to check |
| Browser console shows a CORS error | `FRONTEND_ORIGIN` does not exactly match the frontend address. Fix it and restart the backend |
| `password authentication failed` | The PostgreSQL password in `DATABASE_URL` is wrong |
| `pytest` says a database does not exist | Create `sv_test`, and check `TEST_DATABASE_URL` |
| Chat replies look basic | No `ANTHROPIC_API_KEY` is set, so the rule-based mode is answering |
| `npm install` shows network errors | Run it again. If it persists, check your connection or use `--legacy-peer-deps` |
| The first online load takes a minute | The free Render service was asleep. Wait and retry |
 
## 6. Security notes
 
- No secrets are stored in this repository. Never commit a `.env` file.
- If a key is ever exposed, delete it in the provider's dashboard and create a new one.
- Use a different `SECRET_KEY` online than the one you use locally.
 
