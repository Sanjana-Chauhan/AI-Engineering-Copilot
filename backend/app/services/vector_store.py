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

    chunk_ids = [
        f"{chunk.repository_id}:{chunk.file_path}:{chunk.start_line}"
        for chunk in chunks
    ]

    existing = collection.get(
        ids=chunk_ids,
        include=["metadatas"]
    )

    existing_content_hashes = {
        existing_id: existing_metadata.get("content_hash")
        for existing_id, existing_metadata in zip(
            existing["ids"], existing["metadatas"]
        )
    }

    add_ids, add_documents, add_metadatas = [], [], []
    update_ids, update_documents, update_metadatas = [], [], []
    skipped = 0

    for chunk_id, chunk in zip(chunk_ids, chunks):

        metadata = {
            "repository_id": chunk.repository_id,
            "file_path": chunk.file_path,
            "language": chunk.language,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content_hash": chunk.content_hash
        }

        if chunk_id not in existing_content_hashes:
            add_ids.append(chunk_id)
            add_documents.append(chunk.content)
            add_metadatas.append(metadata)
        elif existing_content_hashes[chunk_id] != chunk.content_hash:
            update_ids.append(chunk_id)
            update_documents.append(chunk.content)
            update_metadatas.append(metadata)
        else:
            skipped += 1

    if add_ids:
        collection.add(
            documents=add_documents,
            ids=add_ids,
            metadatas=add_metadatas
        )

    if update_ids:
        collection.update(
            ids=update_ids,
            documents=update_documents,
            metadatas=update_metadatas
        )

    return {
        "added": len(add_ids),
        "updated": len(update_ids),
        "skipped": skipped,
        "deleted": deleted
    }