import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse, DebugRequest, ExplainRequest, SourceReference
from app.services import conversation_service
from app.services.rag_service import (
    answer_repository_question,
    answer_repository_question_stream,
    debug_error_stream,
    explain_file_stream,
)

router = APIRouter(prefix="/api")


def _serialize_sources(chunks) -> list[dict]:
    return [
        {
            "file_path": chunk.file_path,
            "language": chunk.language,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "score": chunk.score,
        }
        for chunk in chunks
    ]


def _sse(event: str, data: str) -> str:
    data_lines = "\n".join(f"data: {line}" for line in data.split("\n"))
    return f"event: {event}\n{data_lines}\n\n"


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
        history=history,
        file_path=request.file_path
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

    sources = [SourceReference(**source) for source in _serialize_sources(result["sources"])]

    return ChatResponse(
        message=result["answer"],
        conversation_id=conversation_id,
        sources=sources
    )


@router.post("/chat/stream")
def chat_stream(request: ChatRequest):
    conversation_id = request.conversation_id or conversation_service.new_conversation_id()

    history = conversation_service.get_history(
        conversation_id=conversation_id,
        repository_id=request.repository_id
    )

    chunks, token_stream = answer_repository_question_stream(
        question=request.message,
        repository_id=request.repository_id,
        history=history,
        file_path=request.file_path
    )

    sources = _serialize_sources(chunks)

    def event_stream():
        yield _sse("meta", json.dumps({
            "conversation_id": conversation_id,
            "sources": sources
        }))

        answer_parts = []

        for token in token_stream:
            answer_parts.append(token)
            yield _sse("token", token)

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
            content="".join(answer_parts)
        )

        yield _sse("done", "{}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/explain/stream")
def explain_stream(request: ExplainRequest):
    conversation_id = request.conversation_id or conversation_service.new_conversation_id()

    history = conversation_service.get_history(
        conversation_id=conversation_id,
        repository_id=request.repository_id
    )

    chunks, token_stream = explain_file_stream(
        repository_id=request.repository_id,
        file_path=request.file_path,
        history=history
    )

    sources = _serialize_sources(chunks)
    user_turn = f"Explain {request.file_path}"

    def event_stream():
        yield _sse("meta", json.dumps({
            "conversation_id": conversation_id,
            "sources": sources
        }))

        answer_parts = []

        for token in token_stream:
            answer_parts.append(token)
            yield _sse("token", token)

        conversation_service.append_turn(
            conversation_id=conversation_id,
            repository_id=request.repository_id,
            role="user",
            content=user_turn
        )
        conversation_service.append_turn(
            conversation_id=conversation_id,
            repository_id=request.repository_id,
            role="assistant",
            content="".join(answer_parts)
        )

        yield _sse("done", "{}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat/debug/stream")
def debug_stream(request: DebugRequest):
    conversation_id = request.conversation_id or conversation_service.new_conversation_id()

    history = conversation_service.get_history(
        conversation_id=conversation_id,
        repository_id=request.repository_id
    )

    chunks, token_stream = debug_error_stream(
        repository_id=request.repository_id,
        error_text=request.error_text,
        file_path=request.file_path,
        history=history
    )

    sources = _serialize_sources(chunks)
    user_turn = f"Debug this error:\n{request.error_text}"

    def event_stream():
        yield _sse("meta", json.dumps({
            "conversation_id": conversation_id,
            "sources": sources
        }))

        answer_parts = []

        for token in token_stream:
            answer_parts.append(token)
            yield _sse("token", token)

        conversation_service.append_turn(
            conversation_id=conversation_id,
            repository_id=request.repository_id,
            role="user",
            content=user_turn
        )
        conversation_service.append_turn(
            conversation_id=conversation_id,
            repository_id=request.repository_id,
            role="assistant",
            content="".join(answer_parts)
        )

        yield _sse("done", "{}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.delete("/chat/{conversation_id}")
def reset_conversation(conversation_id: str):
    conversation_service.clear_conversation(conversation_id)
    return {"conversation_id": conversation_id, "cleared": True}