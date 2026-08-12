from app.models.code import CodeChunk
from app.services.conversation_service import ConversationTurn
from app.services.search_service import search_code
from app.services.llm_service import generate_response


def build_history_block(history: list[ConversationTurn]) -> str:

    if not history:
        return "(no previous turns)"

    lines = []

    for turn in history:
        speaker = "User" if turn.role == "user" else "Assistant"
        lines.append(f"{speaker}: {turn.content}")

    return "\n".join(lines)


def build_context(chunks: list[CodeChunk]) -> str:

    context_parts = []

    for chunk in chunks:

        context_parts.append(
            f"""
File: {chunk.file_path}
Language: {chunk.language}
Lines: {chunk.start_line}-{chunk.end_line}

Code:
{chunk.content}
"""
        )

    return "\n".join(context_parts)


def answer_repository_question(
    question: str,
    repository_id: str,
    history: list[ConversationTurn] | None = None,
    limit: int = 5
):
    chunks = search_code(
        query=question,
        limit=limit,
        repository_id=repository_id
    )

    if not chunks:
        return {
            "answer": (
                "I couldn't find any relevant code in this repository for that question. "
                "Make sure the repository has been ingested, or try rephrasing your question."
            ),
            "sources": []
        }

    context = build_context(chunks)
    history_block = build_history_block(history or [])

    prompt = f"""
You are an AI Engineering Copilot.

Answer the user's question using the repository context provided below.

Rules:
- Use the repository context as the primary source.
- Do not invent files or code that are not present.
- If the context does not contain enough information, say so.
- Mention relevant file paths and line numbers when possible.
- Use the conversation history to resolve follow-up references (e.g. "it", "that file", "the previous one").

Conversation History:
{history_block}

Repository Context:
{context}

User Question:
{question}
"""

    answer = generate_response(prompt)

    return {
        "answer": answer,
        "sources": chunks
    }