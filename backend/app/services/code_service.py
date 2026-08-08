from pathlib import Path

from app.models.code import CodeChunk


def get_language(file_path: str) -> str:
    extension = Path(file_path).suffix.lower()

    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".md": "markdown",
    }

    return language_map.get(extension, "unknown")


def read_file(file_path: str) -> str:
    path = Path(file_path)

    return path.read_text(
        encoding="utf-8",
        errors="ignore"
    )


def chunk_code(
    content: str,
    file_path: str,
    chunk_size: int = 50,
    repository_id: str = ""
) -> list[CodeChunk]:

    lines = content.splitlines()
    chunks = []

    for start in range(0, len(lines), chunk_size):

        end = min(
            start + chunk_size,
            len(lines)
        )

        chunk = CodeChunk(
            repository_id=repository_id,
            content="\n".join(lines[start:end]),
            file_path=file_path,
            language=get_language(file_path),
            start_line=start + 1,
            end_line=end
        )

        chunks.append(chunk)

    return chunks