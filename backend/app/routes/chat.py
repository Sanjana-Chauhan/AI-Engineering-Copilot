import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    ConversationTurnResponse,
    DebugRequest,
    ExplainRequest,
    SourceReference,
)
from app.services import conversation_service
from app.services.rag_service import (
    answer_repository_question,
    answer_repository_question_stream,
    debug_error_stream,
    explain_file_stream,
)

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


def _friendly_stream_error_message(error: Exception) -> str:
    if "RESOURCE_EXHAUSTED" in str(error) or "429" in str(error):
        return (
            "The AI model has hit its rate limit for now. "
            "Please wait a bit and try again."
        )
    return "The AI service ran into an error while responding. Please try again."


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

    chunks, events = answer_repository_question_stream(
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

        try:
            for event in events:
                if event["type"] == "token":
                    answer_parts.append(event["text"])
                    yield _sse("token", event["text"])
                elif event["type"] == "tool_call":
                    yield _sse("tool_call", json.dumps({
                        "name": event["name"],
                        "args": event["args"]
                    }))
        except Exception as error:
            logger.exception("chat stream failed")
            yield _sse("error", _friendly_stream_error_message(error))

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

        try:
            for token in token_stream:
                answer_parts.append(token)
                yield _sse("token", token)
        except Exception as error:
            logger.exception("chat stream failed")
            yield _sse("error", _friendly_stream_error_message(error))

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

        try:
            for token in token_stream:
                answer_parts.append(token)
                yield _sse("token", token)
        except Exception as error:
            logger.exception("chat stream failed")
            yield _sse("error", _friendly_stream_error_message(error))

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


@router.get("/chat/{conversation_id}", response_model=ConversationHistoryResponse)
def get_conversation_history(conversation_id: str, repository_id: str):
    history = conversation_service.get_history(
        conversation_id=conversation_id,
        repository_id=repository_id
    )

    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        turns=[
            ConversationTurnResponse(role=turn.role, content=turn.content)
            for turn in history
        ]
    )


@router.delete("/chat/{conversation_id}")
def reset_conversation(conversation_id: str):
    conversation_service.clear_conversation(conversation_id)
    return {"conversation_id": conversation_id, "cleared": True}