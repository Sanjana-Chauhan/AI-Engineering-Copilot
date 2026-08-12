from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    repository_id: str


class SourceReference(BaseModel):
    file_path: str
    language: str
    start_line: int
    end_line: int
    score: float | None = None


class ChatResponse(BaseModel):
    message: str
    sources: list[SourceReference] = []