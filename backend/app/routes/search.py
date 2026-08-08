from fastapi import APIRouter

from app.services.search_service import search_code


router = APIRouter(prefix="/api/search")


@router.get("/code")
def search(query: str, limit: int = 5):

    return search_code(
        query=query,
        limit=limit
    )