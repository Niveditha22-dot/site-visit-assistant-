CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('buyer','executive','sales_head','admin'))
);

CREATE TABLE projects (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  rera_number TEXT NOT NULL,
  address TEXT NOT NULL,
  lat NUMERIC(9,6),
  lng NUMERIC(9,6)
);

CREATE TABLE fact_sheet_items (
  id SERIAL PRIMARY KEY,
  project_id INT REFERENCES projects(id),
  topic TEXT NOT NULL,
  value TEXT NOT NULL
);

CREATE TABLE leads (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  phone_norm TEXT UNIQUE,           -- last 10 digits, used for duplicate check
  email_norm TEXT UNIQUE,           -- lowercased
  project_id INT REFERENCES projects(id),
  wants TEXT,                       -- e.g. '2 BHK'
  budget_max_lakh INT,
  language TEXT DEFAULT 'en' CHECK (language IN ('en','hi','gu')),
  consent_given BOOLEAN NOT NULL DEFAULT FALSE,
  consent_at TIMESTAMPTZ,
  opted_out BOOLEAN NOT NULL DEFAULT FALSE,
  executive_id INT REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- every source a lead came from, so merged duplicates keep their history
CREATE TABLE lead_sources (
  id SERIAL PRIMARY KEY,
  lead_id INT REFERENCES leads(id),
  source TEXT NOT NULL,             -- property_portal, social_ad, website, hoarding_call
  first_seen TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE visit_slots (
  id SERIAL PRIMARY KEY,
  project_id INT REFERENCES projects(id),
  starts_at TIMESTAMPTZ NOT NULL,
  UNIQUE (project_id, starts_at)
);

CREATE TABLE bookings (
  id SERIAL PRIMARY KEY,
  lead_id INT REFERENCES leads(id),
  slot_id INT REFERENCES visit_slots(id),
  status TEXT NOT NULL DEFAULT 'booked'
    CHECK (status IN ('booked','visited','no_show','cancelled')),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- the key line: one active booking per slot, enforced by the database
CREATE UNIQUE INDEX one_active_booking_per_slot
  ON bookings (slot_id) WHERE status = 'booked';

CREATE TABLE chat_messages (
  id SERIAL PRIMARY KEY,
  lead_id INT REFERENCES leads(id),
  sender TEXT NOT NULL CHECK (sender IN ('buyer','assistant','executive')),
  content TEXT NOT NULL,
  flagged BOOLEAN NOT NULL DEFAULT FALSE,   -- sales head reviews flagged chats daily
  flag_reason TEXT,
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE handoffs (
  id SERIAL PRIMARY KEY,
  lead_id INT REFERENCES leads(id),
  executive_id INT REFERENCES users(id),
  reason TEXT NOT NULL,                     -- e.g. 'buyer asked for a person', 'missing fact'
  summary TEXT NOT NULL,                    -- chat summary the executive sees
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE reminders (
  id SERIAL PRIMARY KEY,
  booking_id INT REFERENCES bookings(id),
  kind TEXT NOT NULL CHECK (kind IN ('1_day','2_hours')),
  due_at TIMESTAMPTZ NOT NULL,
  sent_at TIMESTAMPTZ,                      -- mocked: "sending" just fills this in
  message TEXT NOT NULL                     -- must include the project's RERA number
);

CREATE TABLE ad_spend (
  id SERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  month DATE NOT NULL,
  amount_inr INT NOT NULL,
  UNIQUE (source, month)
);
