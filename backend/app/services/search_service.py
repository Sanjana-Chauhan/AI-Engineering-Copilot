import re

from rank_bm25 import BM25Okapi

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

# Hybrid search: fuse a keyword ranking (BM25) with the vector ranking via
# Reciprocal Rank Fusion, so an exact identifier match (getUserById,
# EMAMI_733) can surface even when it isn't the closest embedding — pure
# semantic search ranks by *meaning*, and a differently-named-but-related
# function can outrank the literal match. Each side contributes its own
# top-N candidates before fusion (wider than the final `limit`) so RRF has
# enough from each side to actually blend, rather than fusing two lists
# that were already truncated to the final answer.
HYBRID_CANDIDATE_POOL = 25

# Standard RRF damping constant from the literature — larger values flatten
# how much rank position matters (rank 1 vs. rank 10 differs less). Not
# sensitive enough here to be worth tuning further.
RRF_K = 60

# Splits "getUserById" at case-boundaries into ["get", "User", "By", "Id"].
# Two lookaheads: a lowercase/digit-to-uppercase transition (getUser ->
# get|User) and an uppercase-to-uppercase-then-lowercase transition
# (HTTPServer -> HTTP|Server), so acronyms don't get shredded letter by
# letter.
_CAMEL_BOUNDARY_PATTERN = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


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


def _split_identifier(identifier: str) -> list[str]:
    parts = re.split(r"[_\-]+", identifier)
    sub_tokens = []

    for part in parts:
        sub_tokens.extend(_CAMEL_BOUNDARY_PATTERN.split(part))

    return [token.lower() for token in sub_tokens if token]


def _tokenize(text: str) -> list[str]:
    """Whole identifiers plus their case/underscore-split sub-words, so a
    query for "getUserById" matches code written as "get_user_by_id" and
    vice versa — verified directly (see INTERVIEW_PREP.md): without the
    sub-word split, BM25 sees those as two completely unrelated tokens and
    scores zero overlap, which defeats the entire point of adding keyword
    search in the first place."""
    tokens = []

    for identifier in _IDENTIFIER_PATTERN.findall(text):
        tokens.append(identifier.lower())
        tokens.extend(_split_identifier(identifier))

    return tokens


def _fetch_code_chunk_corpus(repository_id: str) -> tuple[list[str], list[CodeChunk]]:
    """Every non-doc chunk for this repository, as (chunk_ids, chunks) in
    matching order. BM25 needs the *whole* corpus to compute meaningful
    term-rarity weighting — scoring against an arbitrary subset would
    distort which terms look "rare"."""
    results = collection.get(
        where={
            "$and": [
                {"repository_id": repository_id},
                {"language": {"$ne": DOC_LANGUAGE}}
            ]
        },
        include=["documents", "metadatas"]
    )

    chunk_ids = results.get("ids", [])
    chunks = _to_chunks(results.get("documents", []), results.get("metadatas", []))

    return chunk_ids, chunks


def _bm25_rank(query: str, chunk_ids: list[str], chunks: list[CodeChunk]) -> list[str]:
    if not chunks:
        return []

    tokenized_corpus = [_tokenize(chunk.content) for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(_tokenize(query))

    ranked_indices = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)

    # A zero BM25 score means no shared terms at all — that's "not a match",
    # not "ranked last", so it shouldn't get a rank position to contribute
    # to the fused score at all.
    return [chunk_ids[i] for i in ranked_indices if scores[i] > 0]


def _vector_rank_ids(query: str, repository_id: str, pool_size: int) -> list[str]:
    results = collection.query(
        query_texts=[query],
        n_results=pool_size,
        where={
            "$and": [
                {"repository_id": repository_id},
                {"language": {"$ne": DOC_LANGUAGE}}
            ]
        },
        include=[]
    )

    return results.get("ids", [[]])[0]


def _reciprocal_rank_fusion(rankings: list[list[str]], k: int = RRF_K) -> list[str]:
    """Combines multiple ranked ID lists (best first) into one: each list
    contributes 1/(k+rank) to an id's total score (rank is 1-indexed),
    summed across every list it appears in. Ranking well in *either* list
    scores decently; ranking well in *both* scores best of all."""
    scores: dict[str, float] = {}

    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)

    return sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)


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

    chunk_ids, all_chunks = _fetch_code_chunk_corpus(repository_id)
    chunk_lookup = dict(zip(chunk_ids, all_chunks))

    vector_ranked_ids = _vector_rank_ids(query, repository_id, HYBRID_CANDIDATE_POOL)
    bm25_ranked_ids = _bm25_rank(query, chunk_ids, all_chunks)[:HYBRID_CANDIDATE_POOL]

    fused_ids = _reciprocal_rank_fusion([vector_ranked_ids, bm25_ranked_ids])

    # Fused ranking has no single meaningful "distance" left to show as a
    # match score — it blends two different ranking systems — so these
    # chunks carry score=None (via _to_chunks' default) rather than a
    # number that looks precise but no longer means what it used to.
    chunks = [
        chunk_lookup[chunk_id]
        for chunk_id in fused_ids[:limit]
        if chunk_id in chunk_lookup
    ]

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
