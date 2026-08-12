from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse, SourceReference
from app.services.rag_service import answer_repository_question

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = answer_repository_question(request.message, request.repository_id)

    sources = [
        SourceReference(
            file_path=chunk.file_path,
            language=chunk.language,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            score=chunk.score,
        )
        for chunk in result["sources"]
    ]

    return ChatResponse(
        message=result["answer"],
        sources=sources
    )