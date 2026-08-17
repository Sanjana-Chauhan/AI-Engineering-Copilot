from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = GEMINI_MODEL

# Safety valve against a runaway tool-call loop — most questions resolve in
# 1-2 calls, but exploring several files in one answer can take more.
TOOL_CALL_MAX_ITERATIONS = 8

TOOL_LIMIT_MESSAGE = (
    "I wasn't able to finish gathering information within the tool-call "
    "limit. Here's what I found so far, but it may be incomplete."
)


def generate_response(message: str) -> str:

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=message
    )

    return response.text


def generate_response_stream(message: str):

    stream = client.models.generate_content_stream(
        model=MODEL_NAME,
        contents=message
    )

    for chunk in stream:
        if chunk.text:
            yield chunk.text


def _run_tool_calls(tool_executor, function_calls) -> list[types.Part]:
    return [
        types.Part.from_function_response(
            name=call.name,
            response={"result": tool_executor(call.name, call.args or {})}
        )
        for call in function_calls
    ]


def generate_with_tools(prompt: str, tools: list[types.Tool], tool_executor) -> str:
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    config = types.GenerateContentConfig(tools=tools)

    for _ in range(TOOL_CALL_MAX_ITERATIONS):
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config
        )

        if not response.function_calls:
            return response.text

        contents.append(response.candidates[0].content)
        contents.append(
            types.Content(
                role="user",
                parts=_run_tool_calls(tool_executor, response.function_calls)
            )
        )

    return TOOL_LIMIT_MESSAGE


def generate_with_tools_stream(prompt: str, tools: list[types.Tool], tool_executor):
    """Yields {"type": "token", "text": ...} for answer text and
    {"type": "tool_call", "name": ..., "args": ...} whenever the model
    invokes a tool, in the order they occur."""

    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    config = types.GenerateContentConfig(tools=tools)

    for _ in range(TOOL_CALL_MAX_ITERATIONS):
        stream = client.models.generate_content_stream(
            model=MODEL_NAME,
            contents=contents,
            config=config
        )

        turn_parts = []
        function_calls = []

        for chunk in stream:
            candidate = chunk.candidates[0] if chunk.candidates else None
            parts = candidate.content.parts if candidate and candidate.content else []

            for part in parts or []:
                turn_parts.append(part)

                if part.function_call:
                    function_calls.append(part.function_call)
                elif part.text:
                    yield {"type": "token", "text": part.text}

        if not function_calls:
            return

        contents.append(types.Content(role="model", parts=turn_parts))

        for call in function_calls:
            yield {"type": "tool_call", "name": call.name, "args": call.args or {}}

        contents.append(
            types.Content(
                role="user",
                parts=_run_tool_calls(tool_executor, function_calls)
            )
        )

    yield {"type": "token", "text": "\n\n" + TOOL_LIMIT_MESSAGE}