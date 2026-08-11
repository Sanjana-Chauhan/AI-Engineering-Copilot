from fastapi import APIRouter

from app.services.search_service import search_code


router = APIRouter(prefix="/api/search")


@router.get("/code")
def search(
    query: str,
    repository_id: str,
    limit: int = 5
):
    return search_code(
        query=query,
        repository_id=repository_id,
        limit=limit
    )