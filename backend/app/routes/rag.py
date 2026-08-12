from fastapi import APIRouter

from app.services.rag_service import (
    answer_repository_question
)


router = APIRouter(prefix="/api/rag")


@router.get("/ask")
def ask_repository(question: str, repository_id: str):

    result = answer_repository_question(
        question=question,
        repository_id=repository_id
    )

    return {
        "question": question,
        "repository_id": repository_id,
        "answer": result["answer"],
        "sources": [
            {
                "file_path": chunk.file_path,
                "language": chunk.language,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "score": chunk.score,
            }
            for chunk in result["sources"]
        ]
    }