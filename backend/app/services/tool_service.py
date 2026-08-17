from google.genai import types

from app.services.search_service import get_file_content, get_indexed_file_paths, search_code


TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="search_code",
        description=(
            "Semantically search this repository's code and documentation for "
            "snippets relevant to a concept, feature, or behavior. Use this "
            "when the context already provided doesn't cover what you need."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for."
                }
            },
            "required": ["query"]
        }
    ),
    types.FunctionDeclaration(
        name="get_file_content",
        description=(
            "Fetch the full content of one specific file by its exact indexed "
            "path. Use this when you need to see an entire file rather than a "
            "partial snippet, e.g. after finding it via search_code or "
            "list_repository_files."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Exact indexed file path, e.g. \"app/services/rag_service.py\"."
                }
            },
            "required": ["file_path"]
        }
    ),
    types.FunctionDeclaration(
        name="list_repository_files",
        description=(
            "List indexed file paths in this repository, optionally filtered "
            "to a directory prefix. Use this to discover relevant files by "
            "name before fetching their content."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "directory_prefix": {
                    "type": "string",
                    "description": "Optional path prefix to filter results, e.g. \"app/services\"."
                }
            }
        }
    ),
]


def build_tools() -> list[types.Tool]:
    return [types.Tool(function_declarations=TOOL_DECLARATIONS)]


def _run_search_code(repository_id: str, query: str) -> str:
    chunks = search_code(query, repository_id, limit=5)

    if not chunks:
        return "No matching code found."

    return "\n\n".join(
        f"File: {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})\n{chunk.content}"
        for chunk in chunks
    )


def _run_get_file_content(repository_id: str, file_path: str) -> str:
    content = get_file_content(file_path, repository_id)
    return content or f'No indexed content found for "{file_path}".'


def _run_list_repository_files(repository_id: str, directory_prefix: str = "") -> str:
    paths = sorted(get_indexed_file_paths(repository_id))

    if directory_prefix:
        normalized_prefix = directory_prefix.replace("\\", "/")
        paths = [
            path for path in paths
            if path.replace("\\", "/").startswith(normalized_prefix)
        ]

    return "\n".join(paths) if paths else "No files found."


def build_tool_executor(repository_id: str):
    handlers = {
        "search_code": lambda args: _run_search_code(repository_id, **args),
        "get_file_content": lambda args: _run_get_file_content(repository_id, **args),
        "list_repository_files": lambda args: _run_list_repository_files(repository_id, **args),
    }

    def execute(name: str, args: dict) -> str:
        handler = handlers.get(name)

        if handler is None:
            return f'Unknown tool "{name}".'

        return handler(args)

    return execute
