import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import CONVERSATIONS_DB_PATH

DB_PATH = Path(CONVERSATIONS_DB_PATH)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect():
    connection = sqlite3.connect(DB_PATH)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
