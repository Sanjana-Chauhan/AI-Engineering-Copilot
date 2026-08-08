from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.services.code_service import (
    chunk_code,
    read_file,
)
from app.services.repository_service import (
    scan_repository,
)


router = APIRouter(prefix="/api/repository")


@router.post("/ingest")
def ingest_repository(repository_path: str):

    try:
        files = scan_repository(repository_path)

        chunks = []

        repository = Path(repository_path)

        for file in files:

            full_path = repository / file

            content = read_file(str(full_path))

            file_chunks = chunk_code(
                content=content,
                file_path=file
            )

            chunks.extend(file_chunks)

        return {
            "repository": repository_path,
            "file_count": len(files),
            "chunk_count": len(chunks),
            "chunks": chunks
        }

    except (FileNotFoundError, ValueError) as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )