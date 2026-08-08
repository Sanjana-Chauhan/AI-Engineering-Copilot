from pydantic import BaseModel


class CodeChunk(BaseModel):
    content: str
    file_path: str
    language: str
    start_line: int
    end_line: int