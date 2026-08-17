from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    repository_id: str
    conversation_id: str | None = None
    file_path: str | None = None


class SourceReference(BaseModel):
    file_path: str
    language: str
    start_line: int
    end_line: int
    score: float | None = None


class ChatResponse(BaseModel):
    message: str
    conversation_id: str
    sources: list[SourceReference] = []