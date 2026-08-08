from fastapi import APIRouter

from app.services.rag_service import (
    answer_repository_question
)


router = APIRouter(prefix="/api/rag")


@router.get("/ask")
def ask_repository(question: str):

    answer = answer_repository_question(
        question=question
    )

    return {
        "question": question,
        "answer": answer
    }