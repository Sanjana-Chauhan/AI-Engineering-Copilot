from app.services.vector_store import collection
from app.models.code import CodeChunk


DOC_LANGUAGE = "markdown"

# Docs are only worth surfacing alongside code when they're a strong match —
# empirically, genuine matches in this project score well under this, while
# unrelated filler sits at 0.75+.
DOC_BACKFILL_MAX_SCORE = 0.65


def _to_chunks(documents, metadatas, distances) -> list[CodeChunk]:
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
    limit: int = 5
) -> list[CodeChunk]:

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
