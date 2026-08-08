from fastapi import APIRouter

from app.services.llm_service import generate_response


router = APIRouter(prefix="/api")


@router.post("/chat")
def chat(message: str):
    response = generate_response(message)

    return {
        "message": response
    }