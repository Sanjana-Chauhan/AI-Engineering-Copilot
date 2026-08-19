import uuid
from dataclasses import dataclass

from app.services.db import connect as _connect

MAX_HISTORY_TURNS = 10
TITLE_MAX_LENGTH = 80


@dataclass
class ConversationTurn:
    role: str
    content: str


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
    _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL UNIQUE,
            repository_id TEXT NOT NULL,
            title TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    _connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_repository_id
        ON conversations (repository_id)
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

    upsert_conversation(
        conversation_id=conversation_id,
        repository_id=repository_id,
        title=_derive_title(content) if role == "user" else None
    )


def _derive_title(content: str) -> str:
    single_line = " ".join(content.split())
    if len(single_line) <= TITLE_MAX_LENGTH:
        return single_line
    return single_line[:TITLE_MAX_LENGTH - 1].rstrip() + "…"


def upsert_conversation(
    conversation_id: str,
    repository_id: str,
    title: str | None = None
) -> None:
    with _connect() as connection:
        existing = connection.execute(
            "SELECT id FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO conversations
                    (conversation_id, repository_id, title, created_at, updated_at)
                VALUES (?, ?, ?, datetime('now'), datetime('now'))
                """,
                (conversation_id, repository_id, title)
            )
        else:
            connection.execute(
                "UPDATE conversations SET updated_at = datetime('now') WHERE conversation_id = ?",
                (conversation_id,)
            )


def list_conversations(repository_id: str) -> list[dict]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT conversation_id, title, created_at, updated_at
            FROM conversations
            WHERE repository_id = ?
            ORDER BY updated_at DESC
            """,
            (repository_id,)
        ).fetchall()

    return [
        {
            "conversation_id": conversation_id,
            "title": title,
            "created_at": created_at,
            "updated_at": updated_at
        }
        for conversation_id, title, created_at, updated_at in rows
    ]


def clear_conversation(conversation_id: str) -> None:
    with _connect() as connection:
        connection.execute(
            "DELETE FROM conversation_turns WHERE conversation_id = ?",
            (conversation_id,)
        )
        connection.execute(
            "DELETE FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        )
