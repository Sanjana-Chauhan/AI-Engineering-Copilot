import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from app.config import CONVERSATIONS_DB_PATH

DB_PATH = Path(CONVERSATIONS_DB_PATH)

MAX_HISTORY_TURNS = 10


@dataclass
class ConversationTurn:
    role: str
    content: str


DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def _connect():
    connection = sqlite3.connect(DB_PATH)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


with _connect() as _connection:
    _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            repository_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
        """
    )
    _connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversation_turns_conversation_id
        ON conversation_turns (conversation_id)
        """
    )


def new_conversation_id() -> str:
    return str(uuid.uuid4())


def get_history(conversation_id: str, repository_id: str) -> list[ConversationTurn]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT role, content FROM conversation_turns
            WHERE conversation_id = ? AND repository_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (conversation_id, repository_id, MAX_HISTORY_TURNS * 2)
        ).fetchall()

    return [ConversationTurn(role=role, content=content) for role, content in reversed(rows)]


def append_turn(
    conversation_id: str,
    repository_id: str,
    role: str,
    content: str
) -> None:
    with _connect() as connection:
        # A conversation_id previously used against a different repository
        # is stale context, not a real history — drop it before adding to
        # this repository's history, same reset behavior as before.
        connection.execute(
            """
            DELETE FROM conversation_turns
            WHERE conversation_id = ? AND repository_id != ?
            """,
            (conversation_id, repository_id)
        )
        connection.execute(
            """
            INSERT INTO conversation_turns (conversation_id, repository_id, role, content)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, repository_id, role, content)
        )


def clear_conversation(conversation_id: str) -> None:
    with _connect() as connection:
        connection.execute(
            "DELETE FROM conversation_turns WHERE conversation_id = ?",
            (conversation_id,)
        )
