import chromadb

from chromadb.utils import embedding_functions

from app.models.code import CodeChunk


embedding_function = (
    embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
)


client = chromadb.PersistentClient(
    path="./data/chroma"
)


collection = client.get_or_create_collection(
    name="repository_code",
    embedding_function=embedding_function
)


def _prune_orphaned_chunks(repository_id: str, current_ids: set[str]) -> int:

    existing = collection.get(
        where={"repository_id": repository_id},
        include=[]
    )

    orphaned_ids = [
        existing_id
        for existing_id in existing["ids"]
        if existing_id not in current_ids
    ]

    if orphaned_ids:
        collection.delete(ids=orphaned_ids)

    return len(orphaned_ids)


def add_chunks(chunks: list[CodeChunk], repository_id: str) -> dict:

    current_ids = {
        f"{chunk.repository_id}:{chunk.file_path}:{chunk.start_line}"
        for chunk in chunks
    }

    deleted = _prune_orphaned_chunks(repository_id, current_ids)

    if not chunks:
        return {
            "added": 0,
            "updated": 0,
            "skipped": 0,
            "deleted": deleted
        }

    added = 0
    updated = 0
    skipped = 0

    for chunk in chunks:

        chunk_id = (
            f"{chunk.repository_id}:"
            f"{chunk.file_path}:"
            f"{chunk.start_line}"
        )

        existing = collection.get(
            ids=[chunk_id],
            include=["metadatas"]
        )

        metadata = {
            "repository_id": chunk.repository_id,
            "file_path": chunk.file_path,
            "language": chunk.language,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content_hash": chunk.content_hash
        }

        if not existing["ids"]:

            collection.add(
                documents=[chunk.content],
                ids=[chunk_id],
                metadatas=[metadata]
            )

            added += 1
            continue

        existing_metadata = existing["metadatas"][0]

        if (
            existing_metadata.get("content_hash")
            == chunk.content_hash
        ):
            skipped += 1
            continue

        collection.update(
            ids=[chunk_id],
            documents=[chunk.content],
            metadatas=[metadata]
        )

        updated += 1

    return {
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "deleted": deleted
    }