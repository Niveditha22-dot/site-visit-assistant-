import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    # commits when the request succeeds, rolls back if it raises
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        yield conn
