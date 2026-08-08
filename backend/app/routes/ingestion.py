from pathlib import Path
import hashlib

from fastapi import APIRouter, HTTPException
from app.services.vector_store import add_chunks

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
            repository_id = hashlib.sha256(repository_path.encode()).hexdigest()[:12] if repository_path else ""
            content = read_file(str(full_path))

            file_chunks = chunk_code(
                content=content,
                file_path=file,
                repository_id=repository_id
            )

            chunks.extend(file_chunks)
        added_chunks = add_chunks(chunks)

        return {
            "repository": repository_path,
            "repository_id": repository_id,
            "file_count": len(files),
            "chunk_count": len(chunks),
            "new_chunks_added": added_chunks
        }

    except (FileNotFoundError, ValueError) as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )