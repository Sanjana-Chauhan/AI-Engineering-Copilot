from app.services.search_service import search_code
from app.services.llm_service import generate_response


def build_context(results) -> str:

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    context_parts = []

    for document, metadata in zip(documents, metadatas):

        context_parts.append(
            f"""
File: {metadata['file_path']}
Language: {metadata['language']}
Lines: {metadata['start_line']}-{metadata['end_line']}

Code:
{document}
"""
        )

    return "\n".join(context_parts)


def answer_repository_question(
    question: str,
    limit: int = 5
) -> str:

    results = search_code(
        query=question,
        limit=limit
    )

    context = build_context(results)

    prompt = f"""
You are an AI Engineering Copilot.

Answer the user's question using the repository context provided below.

Rules:
- Use the repository context as the primary source.
- Do not invent files or code that are not present.
- If the context does not contain enough information, say so.
- Mention relevant file paths and line numbers when possible.

Repository Context:
{context}

User Question:
{question}
"""

    return generate_response(prompt)