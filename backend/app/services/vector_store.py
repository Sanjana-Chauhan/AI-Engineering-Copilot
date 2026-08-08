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


def add_chunks(chunks: list[CodeChunk]) -> int:

    if not chunks:
        return 0

    documents = [
        chunk.content
        for chunk in chunks
    ]

    ids = [
        f"{chunk.repository_id}:{chunk.file_path}:{chunk.start_line}"
        for chunk in chunks
    ]

    metadatas = [
        {
            "repository_id": chunk.repository_id,
            "file_path": chunk.file_path,
            "language": chunk.language,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line
        }
        for chunk in chunks
    ]

    existing = collection.get(
        ids=ids
    )

    existing_ids = set(existing["ids"])

    new_documents = []
    new_ids = []
    new_metadatas = []

    for document, chunk_id, metadata in zip(
        documents,
        ids,
        metadatas
    ):

        if chunk_id in existing_ids:
            continue

        new_documents.append(document)
        new_ids.append(chunk_id)
        new_metadatas.append(metadata)

    if not new_ids:
        return 0

    collection.add(
        documents=new_documents,
        ids=new_ids,
        metadatas=new_metadatas
    )

    return len(new_ids)