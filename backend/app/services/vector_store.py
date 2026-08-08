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


def add_chunks(chunks: list[CodeChunk]) -> None:

    if not chunks:
        return

    documents = [
        chunk.content
        for chunk in chunks
    ]

    ids = [
        f"{chunk.file_path}:{chunk.start_line}"
        for chunk in chunks
    ]

    metadatas = [
        {
            "file_path": chunk.file_path,
            "language": chunk.language,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line
        }
        for chunk in chunks
    ]

    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas
    )