from app.models.code import CodeChunk
from app.services.conversation_service import ConversationTurn
from app.services.search_service import DOC_LANGUAGE, search_code, search_for_debug
from app.services.llm_service import generate_response, generate_response_stream


NO_CONTEXT_MESSAGE = (
    "I couldn't find any relevant code in this repository for that question. "
    "Make sure the repository has been ingested, or try rephrasing your question."
)


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

        source_label = "DOCUMENTATION" if chunk.language == DOC_LANGUAGE else "CODE"

        context_parts.append(
            f"""
[{source_label}]
File: {chunk.file_path}
Language: {chunk.language}
Lines: {chunk.start_line}-{chunk.end_line}

Content:
{chunk.content}
"""
        )

    return "\n".join(context_parts)


def build_prompt(
    question: str,
    chunks: list[CodeChunk],
    history: list[ConversationTurn],
    file_path: str | None = None
) -> str:

    context = build_context(chunks)
    history_block = build_history_block(history)

    scope_rule = (
        f'- The user has scoped this question to a single file: "{file_path}". '
        "Focus your answer on that file; only bring in other files if directly relevant."
        if file_path else
        "- Use the repository context as the primary source."
    )

    return f"""
You are an AI Engineering Copilot.

Answer the user's question using the repository context provided below.

Rules:
{scope_rule}
- [CODE] snippets are the authoritative source of truth about how the system actually works.
- [DOCUMENTATION] snippets may be outdated. Use them only for high-level framing, and defer to [CODE] whenever the two disagree.
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


def _no_context_message(file_path: str | None) -> str:
    if file_path:
        return (
            f'I couldn\'t find any indexed content for "{file_path}". '
            "Make sure the repository has been ingested and that file was included."
        )
    return NO_CONTEXT_MESSAGE


def build_explain_prompt(
    chunks: list[CodeChunk],
    file_path: str,
    history: list[ConversationTurn]
) -> str:

    context = build_context(chunks)
    history_block = build_history_block(history)

    return f"""
You are an AI Engineering Copilot performing a code explanation task.

Explain the file below to a developer who has never seen it before. Structure
your answer with exactly these sections:

1. **Purpose** — what this file is responsible for, in one or two sentences.
2. **Key components** — the main functions/classes, each with a one-line
   description and its line range.
3. **How it fits in** — how this file is used by or connects to the rest of
   the codebase, based only on what's visible in the context below.
4. **Notable details** — non-obvious logic, edge cases, assumptions, or
   anything that looks fragile or worth a reviewer's attention.

Rules:
- Base the explanation only on the code shown below. Do not invent functions,
  files, or behavior that isn't present in the context.
- [CODE] snippets are authoritative. [DOCUMENTATION] snippets may be outdated
  and should only be used for high-level framing.
- Use exact file paths and line numbers when referencing code.
- If the user's prior questions in the conversation history give useful
  context (e.g. a specific angle they care about), take that into account.

Conversation History:
{history_block}

File: {file_path}

Repository Context:
{context}
"""


def build_debug_prompt(
    chunks: list[CodeChunk],
    error_text: str,
    history: list[ConversationTurn],
    file_path: str | None = None
) -> str:

    context = build_context(chunks)
    history_block = build_history_block(history)

    scope_rule = (
        f'- The user scoped this to a single file: "{file_path}". Focus your '
        "diagnosis there unless the error clearly originates elsewhere."
        if file_path else
        "- Chunks from files named in the stack trace (if any) are listed "
        "first and are the most likely location of the bug; the rest are "
        "semantically related context."
    )

    return f"""
You are an AI Engineering Copilot performing a debugging task.

A developer hit the error or stack trace below. Diagnose it using the
repository context provided. Structure your answer with exactly these
sections:

1. **Root Cause** — the specific line(s)/logic most likely causing this,
   with file path and line numbers.
2. **Explanation** — why that code produces this error, in plain terms.
3. **Suggested Fix** — a concrete code-level fix or next debugging step.
4. **Confidence & Caveats** — how confident you are given the visible
   context, and what you'd need to see to be sure (e.g. a file that wasn't
   retrieved).

Rules:
{scope_rule}
- [CODE] snippets are authoritative. [DOCUMENTATION] snippets may be
  outdated and are only for high-level framing.
- Do not invent files, functions, or behavior that isn't present in the
  context.
- If the context doesn't contain the actual failure point, say so
  explicitly in Confidence & Caveats rather than guessing.
- Use the conversation history to resolve follow-up references.

Conversation History:
{history_block}

Repository Context:
{context}

Error / Stack Trace:
{error_text}
"""


def debug_error(
    repository_id: str,
    error_text: str,
    file_path: str | None = None,
    history: list[ConversationTurn] | None = None
):
    chunks = (
        search_code(error_text, repository_id, file_path=file_path)
        if file_path else
        search_for_debug(error_text, repository_id)
    )

    if not chunks:
        return {
            "answer": _no_context_message(file_path),
            "sources": []
        }

    prompt = build_debug_prompt(chunks, error_text, history or [], file_path)
    answer = generate_response(prompt)

    return {
        "answer": answer,
        "sources": chunks
    }


def debug_error_stream(
    repository_id: str,
    error_text: str,
    file_path: str | None = None,
    history: list[ConversationTurn] | None = None
):
    chunks = (
        search_code(error_text, repository_id, file_path=file_path)
        if file_path else
        search_for_debug(error_text, repository_id)
    )

    if not chunks:
        message = _no_context_message(file_path)

        def no_context_stream():
            yield message

        return [], no_context_stream()

    prompt = build_debug_prompt(chunks, error_text, history or [], file_path)

    return chunks, generate_response_stream(prompt)


def explain_file(
    repository_id: str,
    file_path: str,
    history: list[ConversationTurn] | None = None
):
    chunks = search_code(
        query=f"Explain {file_path}",
        repository_id=repository_id,
        file_path=file_path
    )

    if not chunks:
        return {
            "answer": _no_context_message(file_path),
            "sources": []
        }

    prompt = build_explain_prompt(chunks, file_path, history or [])
    answer = generate_response(prompt)

    return {
        "answer": answer,
        "sources": chunks
    }


def explain_file_stream(
    repository_id: str,
    file_path: str,
    history: list[ConversationTurn] | None = None
):
    chunks = search_code(
        query=f"Explain {file_path}",
        repository_id=repository_id,
        file_path=file_path
    )

    if not chunks:
        message = _no_context_message(file_path)

        def no_context_stream():
            yield message

        return [], no_context_stream()

    prompt = build_explain_prompt(chunks, file_path, history or [])

    return chunks, generate_response_stream(prompt)


def answer_repository_question(
    question: str,
    repository_id: str,
    history: list[ConversationTurn] | None = None,
    limit: int = 5,
    file_path: str | None = None
):
    chunks = search_code(
        query=question,
        limit=limit,
        repository_id=repository_id,
        file_path=file_path
    )

    if not chunks:
        return {
            "answer": _no_context_message(file_path),
            "sources": []
        }

    prompt = build_prompt(question, chunks, history or [], file_path)
    answer = generate_response(prompt)

    return {
        "answer": answer,
        "sources": chunks
    }


def answer_repository_question_stream(
    question: str,
    repository_id: str,
    history: list[ConversationTurn] | None = None,
    limit: int = 5,
    file_path: str | None = None
):
    chunks = search_code(
        query=question,
        limit=limit,
        repository_id=repository_id,
        file_path=file_path
    )

    if not chunks:
        message = _no_context_message(file_path)

        def no_context_stream():
            yield message

        return [], no_context_stream()

    prompt = build_prompt(question, chunks, history or [], file_path)

    return chunks, generate_response_stream(prompt)