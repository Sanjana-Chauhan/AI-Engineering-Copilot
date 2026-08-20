from app.services.db import connect as _connect

with _connect() as _connection:
    _connection.execute(
        """
        CREATE TABLE IF NOT EXISTS repositories (
            repository_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            path_or_url TEXT NOT NULL,
            label TEXT NOT NULL,
            first_ingested_at TEXT NOT NULL,
            last_ingested_at TEXT NOT NULL
        )
        """
    )


def upsert_repository(
    repository_id: str,
    source_type: str,
    path_or_url: str,
    label: str
) -> None:
    with _connect() as connection:
        existing = connection.execute(
            "SELECT repository_id FROM repositories WHERE repository_id = ?",
            (repository_id,)
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO repositories
                    (repository_id, source_type, path_or_url, label, first_ingested_at, last_ingested_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                (repository_id, source_type, path_or_url, label)
            )
        else:
            connection.execute(
                """
                UPDATE repositories
                SET source_type = ?, path_or_url = ?, label = ?, last_ingested_at = datetime('now')
                WHERE repository_id = ?
                """,
                (source_type, path_or_url, label, repository_id)
            )


def delete_repository(repository_id: str) -> None:
    with _connect() as connection:
        connection.execute(
            "DELETE FROM repositories WHERE repository_id = ?",
            (repository_id,)
        )


def list_repositories() -> list[dict]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT repository_id, source_type, path_or_url, label, first_ingested_at, last_ingested_at
            FROM repositories
            ORDER BY last_ingested_at DESC
            """
        ).fetchall()

    return [
        {
            "repository_id": repository_id,
            "source_type": source_type,
            "path_or_url": path_or_url,
            "label": label,
            "first_ingested_at": first_ingested_at,
            "last_ingested_at": last_ingested_at
        }
        for (
            repository_id, source_type, path_or_url, label,
            first_ingested_at, last_ingested_at
        ) in rows
    ]
