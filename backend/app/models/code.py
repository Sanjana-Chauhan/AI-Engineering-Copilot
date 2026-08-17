from pydantic import BaseModel


class CodeChunk(BaseModel):
    repository_id: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    content: str
    content_hash: str
    score: float | None = None  
    