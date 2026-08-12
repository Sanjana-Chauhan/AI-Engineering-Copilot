from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse, SourceReference
from app.services import conversation_service
from app.services.rag_service import answer_repository_question

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    conversation_id = request.conversation_id or conversation_service.new_conversation_id()

    history = conversation_service.get_history(
        conversation_id=conversation_id,
        repository_id=request.repository_id
    )

    result = answer_repository_question(
        question=request.message,
        repository_id=request.repository_id,
        history=history
    )

    conversation_service.append_turn(
        conversation_id=conversation_id,
        repository_id=request.repository_id,
        role="user",
        content=request.message
    )
    conversation_service.append_turn(
        conversation_id=conversation_id,
        repository_id=request.repository_id,
        role="assistant",
        content=result["answer"]
    )

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
        conversation_id=conversation_id,
        sources=sources
    )


@router.delete("/chat/{conversation_id}")
def reset_conversation(conversation_id: str):
    conversation_service.clear_conversation(conversation_id)
    return {"conversation_id": conversation_id, "cleared": True}