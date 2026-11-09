import os

import psycopg


def fresh_db() -> str:
    """Empty the test database, load the schema, seed demo data. Returns the test DB url."""
    url = os.environ["TEST_DATABASE_URL"]
    os.environ["DATABASE_URL"] = url
    with psycopg.connect(url) as c:
        c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        c.execute(open("backend/db/schema.sql").read())
    import seed
    seed.main()
    return url
