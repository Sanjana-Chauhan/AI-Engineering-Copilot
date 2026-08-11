from app.models.code import CodeChunk
from app.services.vector_store import collection


def search_code(
    query: str,
    repository_id: str,
    limit: int = 5
) -> list[CodeChunk]:

    results = collection.query(
        query_texts=[query],
        n_results=limit,
        where={
            "repository_id": repository_id
        }
    )

    search_results = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):

        search_results.append(
            CodeSearchResult(
                content=document,
                file_path=metadata["file_path"],
                language=metadata["language"],
                start_line=metadata["start_line"],
                end_line=metadata["end_line"],
                score=distance
            )
        )

    return search_results