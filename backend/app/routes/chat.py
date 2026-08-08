from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.services.llm_service import generate_response


router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    response = generate_response(request.message)

    return ChatResponse(
        message=response
    )