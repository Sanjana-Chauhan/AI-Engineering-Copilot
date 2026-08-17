import re

from app.services.vector_store import collection
from app.models.code import CodeChunk


DOC_LANGUAGE = "markdown"

# Docs are only worth surfacing alongside code when they're a strong match —
# empirically, genuine matches in this project score well under this, while
# unrelated filler sits at 0.75+.
DOC_BACKFILL_MAX_SCORE = 0.65

# When a question is scoped to one file, relevance ranking within that file
# doesn't matter as much as covering the whole thing — cap generously
# instead of the usual top-k, so a multi-chunk file doesn't get truncated.
FILE_SCOPE_CHUNK_LIMIT = 40

# Error/stack traces often reference several files (a raise site plus a few
# frames of call stack) — pull the full content of a few of them rather than
# just the top one.
MAX_DEBUG_FILE_MATCHES = 3

# Matches path-like tokens (e.g. "app/services/rag_service.py" or
# "src\\foo.ts" from a stack trace frame). Intentionally permissive — false
# positives are harmless since candidates are only kept if they actually
# match an indexed file path.
_PATH_TOKEN_PATTERN = re.compile(r"[\w.\-]+(?:[/\\][\w.\-]+)*\.[A-Za-z]+")


def _to_chunks(documents, metadatas, distances=None) -> list[CodeChunk]:
    if distances is None:
        distances = [None] * len(documents)

    return [
        CodeChunk(
            repository_id=metadata["repository_id"],
            content_hash=metadata["content_hash"],
            content=document,
            file_path=metadata["file_path"],
            language=metadata["language"],
            start_line=metadata["start_line"],
            end_line=metadata["end_line"],
            score=distance,
        )
        for document, metadata, distance in zip(documents, metadatas, distances)
    ]


def search_code(
    query: str,
    repository_id: str,
    limit: int = 5,
    file_path: str | None = None
) -> list[CodeChunk]:

    if file_path:
        # Match on a normalized path rather than the raw where-filter value —
        # callers (an LLM tool call, in particular) can't be expected to know
        # this repo's stored path uses OS-native separators (backslashes on
        # Windows) rather than forward slashes.
        normalized_target = file_path.replace("\\", "/")

        results = collection.get(where={"repository_id": repository_id})

        chunks = [
            chunk for chunk in _to_chunks(
                results.get("documents", []),
                results.get("metadatas", [])
            )
            if chunk.file_path.replace("\\", "/") == normalized_target
        ]
        chunks.sort(key=lambda chunk: chunk.start_line)

        return chunks[:FILE_SCOPE_CHUNK_LIMIT]

    code_results = collection.query(
        query_texts=[query],
        n_results=limit,
        where={
            "$and": [
                {"repository_id": repository_id},
                {"language": {"$ne": DOC_LANGUAGE}}
            ]
        }
    )

    chunks = _to_chunks(
        code_results.get("documents", [[]])[0],
        code_results.get("metadatas", [[]])[0],
        code_results.get("distances", [[]])[0]
    )

    doc_results = collection.query(
        query_texts=[query],
        n_results=1,
        where={
            "$and": [
                {"repository_id": repository_id},
                {"language": DOC_LANGUAGE}
            ]
        }
    )

    doc_documents = doc_results.get("documents", [[]])[0]
    doc_distances = doc_results.get("distances", [[]])[0]

    if doc_documents and doc_distances[0] <= DOC_BACKFILL_MAX_SCORE:
        chunks.extend(
            _to_chunks(
                doc_documents,
                doc_results.get("metadatas", [[]])[0],
                doc_distances
            )
        )

    return chunks


def get_file_content(file_path: str, repository_id: str) -> str:
    chunks = search_code(file_path, repository_id, file_path=file_path)
    return "\n".join(chunk.content for chunk in chunks)


def get_indexed_file_paths(repository_id: str) -> set[str]:
    results = collection.get(
        where={"repository_id": repository_id},
        include=["metadatas"]
    )

    return {metadata["file_path"] for metadata in results.get("metadatas", [])}


def _find_mentioned_files(error_text: str, indexed_paths: set[str]) -> list[str]:
    candidates = {
        token.replace("\\", "/") for token in _PATH_TOKEN_PATTERN.findall(error_text)
    }

    if not candidates:
        return []

    matches = []

    for indexed_path in indexed_paths:
        normalized_indexed = indexed_path.replace("\\", "/")

        if any(
            normalized_indexed.endswith(candidate) or candidate.endswith(normalized_indexed)
            for candidate in candidates
        ):
            matches.append(indexed_path)

    return matches


def search_for_debug(
    error_text: str,
    repository_id: str,
    limit: int = 5
) -> list[CodeChunk]:
    """Retrieval tuned for debugging: files named in the stack trace are
    pulled in full, then backed up with the usual semantic search over the
    error text so related-but-unmentioned code can still surface."""

    indexed_paths = get_indexed_file_paths(repository_id)
    mentioned_files = _find_mentioned_files(error_text, indexed_paths)

    chunks: list[CodeChunk] = []
    seen_keys = set()

    for file_path in mentioned_files[:MAX_DEBUG_FILE_MATCHES]:
        for chunk in search_code(error_text, repository_id, file_path=file_path):
            key = (chunk.file_path, chunk.start_line, chunk.end_line)
            if key not in seen_keys:
                seen_keys.add(key)
                chunks.append(chunk)

    for chunk in search_code(error_text, repository_id, limit=limit):
        key = (chunk.file_path, chunk.start_line, chunk.end_line)
        if key not in seen_keys:
            seen_keys.add(key)
            chunks.append(chunk)

    return chunks
