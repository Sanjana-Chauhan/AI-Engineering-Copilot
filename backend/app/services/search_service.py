from app.services.vector_store import collection


def search_code(
    query: str,
    limit: int = 5
):
    results = collection.query(
        query_texts=[query],
        n_results=limit
    )

    return results