from app.services.vector_store import collection


def search_code(
    query: str,
    repository_id: str,
    limit: int = 5
):
    results = collection.query(
    query_texts=[query],
    n_results=limit,
    where={
        "repository_id": repository_id
    }
)
    return results

def get_language(file_path: str) -> str:
    return file_path.split(".")[-1]