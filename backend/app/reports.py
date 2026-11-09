def dashboard(conn):
    rows = conn.execute("""
        WITH first_src AS (SELECT DISTINCT ON (lead_id) lead_id, source FROM lead_sources ORDER BY lead_id, id),
        first_reply AS (SELECT lead_id, min(created_at) AS t FROM chat_messages WHERE sender='assistant' GROUP BY lead_id),
        per_lead AS (
          SELECT l.id, fs.source, extract(epoch FROM fr.t - l.created_at)::float8 AS secs,
                 count(b.id) FILTER (WHERE b.status='visited') AS v,
                 count(b.id) FILTER (WHERE b.status='no_show') AS ns,
                 count(b.id) FILTER (WHERE b.status='booked') AS up
          FROM leads l JOIN first_src fs ON fs.lead_id = l.id
          LEFT JOIN first_reply fr ON fr.lead_id = l.id
          LEFT JOIN bookings b ON b.lead_id = l.id
          GROUP BY l.id, fs.source, fr.t)
        SELECT source, count(*) AS leads,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY secs) AS median_secs,
               sum(v)::int AS visits, sum(ns)::int AS no_shows, sum(up)::int AS upcoming
        FROM per_lead GROUP BY source ORDER BY source""").fetchall()
    spend = dict(conn.execute("SELECT source, sum(amount_inr)::int FROM ad_spend GROUP BY source").fetchall())
    overall = conn.execute("""SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM fr.t - l.created_at)::float8)
                              FROM leads l JOIN (SELECT lead_id, min(created_at) t FROM chat_messages
                                                 WHERE sender='assistant' GROUP BY lead_id) fr ON fr.lead_id = l.id""").fetchone()[0]
    out = []
    for source, leads, med, visits, no_shows, upcoming in rows:
        done = visits + no_shows
        out.append({"source": source, "leads": leads,
                    "median_response_seconds": round(med) if med is not None else None,
                    "visits": visits, "no_shows": no_shows, "upcoming": upcoming,
                    "lead_to_visit_rate": round(visits / leads, 2) if leads else None,
                    "show_up_rate": round(visits / done, 2) if done else None,
                    "ad_spend_inr": spend.get(source, 0),
                    "cost_per_visit_inr": round(spend.get(source, 0) / visits) if visits else None})
    return {"overall_median_response_seconds": round(overall) if overall is not None else None, "by_source": out}
