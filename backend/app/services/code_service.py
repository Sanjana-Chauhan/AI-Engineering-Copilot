from pathlib import Path

from tree_sitter_language_pack import get_parser

from app.models.code import CodeChunk
import hashlib

# Definition node types per language, verified against real parse trees
# (see INTERVIEW_PREP.md) rather than guessed from grammar docs. Only
# languages listed here get AST-aware chunking; every other currently
# supported language (java, cpp, c, csharp, go, rust) and non-code formats
# (html, css, json, md) still use the fixed-line chunker below -- adding
# a language here is the only change needed to extend AST chunking to it.
_AST_SUPPORTED_LANGUAGES = {
    "python": {
        "function_types": {"function_definition"},
        "class_types": {"class_definition"},
        "export_wrapper_types": set(),
    },
    "javascript": {
        "function_types": {"function_declaration"},
        "class_types": {"class_declaration"},
        "export_wrapper_types": {"export_statement"},
    },
    "typescript": {
        "function_types": {"function_declaration"},
        "class_types": {"class_declaration"},
        "export_wrapper_types": {"export_statement"},
    },
}

# Methods nested in a class body use the same node type as a top-level
# function in Python, but a distinct type in JS/TS -- checked at the one
# call site that needs it rather than threaded through the config above.
_METHOD_NODE_TYPES = {"function_definition", "method_definition"}

# A whole function/class/method kept as one chunk is the point of AST
# chunking -- but the embedding model (all-MiniLM-L6-v2, 256-token max
# sequence length, verified directly) silently truncates anything past
# that, so one giant chunk for an outlier-huge function buys nothing on
# the embedding side while still costing a lot of LLM context if it's
# retrieved. Past this many lines, fall back to bounded sub-chunks for
# just that one definition instead of either point.
MAX_AST_CHUNK_LINES = 150


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
    """Chunk by function/class/method boundary where we have a verified
    tree-sitter grammar for the language; fall back to fixed-line chunking
    for everything else, or if parsing this particular file finds no
    definitions to chunk on (e.g. a script with only top-level statements,
    where line-based chunking is just as good)."""

    language = get_language(file_path)

    ast_chunks = _try_ast_chunks(content, file_path, language, repository_id, chunk_size)
    if ast_chunks is not None:
        return ast_chunks

    return _chunk_fixed_lines(content, file_path, chunk_size, repository_id, language)


def _chunk_fixed_lines(
    content: str,
    file_path: str,
    chunk_size: int,
    repository_id: str,
    language: str
) -> list[CodeChunk]:
    lines = content.splitlines()
    chunks = []

    for start in range(0, len(lines), chunk_size):
        end = min(start + chunk_size, len(lines))
        chunk_content = "\n".join(lines[start:end])

        chunks.append(_build_chunk(
            chunk_content, file_path, language, start + 1, end, repository_id
        ))

    return chunks


def _build_chunk(
    content: str,
    file_path: str,
    language: str,
    start_line: int,
    end_line: int,
    repository_id: str
) -> CodeChunk:
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    return CodeChunk(
        repository_id=repository_id,
        content_hash=content_hash,
        content=content,
        file_path=file_path,
        language=language,
        start_line=start_line,
        end_line=end_line
    )


def _node_text(source_bytes: bytes, node) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")


def _definition_chunks(
    node,
    source_bytes: bytes,
    file_path: str,
    language: str,
    repository_id: str,
    chunk_size: int,
    prefix: str = ""
) -> list[CodeChunk]:
    """One chunk for the whole definition (the common case), or bounded
    sub-chunks if it's past MAX_AST_CHUNK_LINES -- see that constant."""
    start_line = node.start_point[0] + 1
    end_line = node.end_point[0] + 1

    if end_line - start_line + 1 <= MAX_AST_CHUNK_LINES:
        content = prefix + _node_text(source_bytes, node)
        return [_build_chunk(content, file_path, language, start_line, end_line, repository_id)]

    lines = source_bytes.decode("utf-8", errors="ignore").splitlines()
    return _fixed_line_subchunks(
        lines, start_line, end_line, chunk_size, file_path, language, repository_id, prefix
    )


def _residual_line_ranges(
    total_start: int,
    total_end: int,
    covered: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """The line ranges within [total_start, total_end] not covered by any
    (start, end) span already turned into its own chunk -- e.g. imports and
    top-level statements outside any function/class, or a class's own
    docstring/fields outside any method."""
    gaps = []
    cursor = total_start

    for start, end in sorted(covered):
        if start > cursor:
            gaps.append((cursor, start - 1))
        cursor = max(cursor, end + 1)

    if cursor <= total_end:
        gaps.append((cursor, total_end))

    return gaps


def _fixed_line_subchunks(
    lines: list[str],
    start_line: int,
    end_line: int,
    chunk_size: int,
    file_path: str,
    language: str,
    repository_id: str,
    prefix: str = ""
) -> list[CodeChunk]:
    chunks = []
    current = start_line

    while current <= end_line:
        sub_end = min(current + chunk_size - 1, end_line)
        content = "\n".join(lines[current - 1:sub_end])

        if content.strip():
            chunks.append(_build_chunk(prefix + content, file_path, language, current, sub_end, repository_id))

        current = sub_end + 1

    return chunks


def _classify_top_level_node(node, config: dict):
    """Returns (definition_node, kind) for a node this chunker knows how to
    handle -- kind is "function" or "class". definition_node is the node
    itself, or, for an exported declaration (`export default function`,
    `export class`), the inner declaration node unwrapped from the
    export_statement -- callers still use the OUTER node for chunk
    boundaries, so "export"/"export default" stays part of the chunk."""
    if node.type in config["class_types"]:
        return node, "class"

    if node.type in config["function_types"]:
        return node, "function"

    if node.type in config["export_wrapper_types"]:
        for child in node.children:
            if child.type in config["class_types"]:
                return child, "class"
            if child.type in config["function_types"]:
                return child, "function"

    return None, None


def _chunk_class(
    outer_node,
    class_node,
    source_bytes: bytes,
    file_path: str,
    language: str,
    repository_id: str,
    chunk_size: int
) -> list[CodeChunk]:
    class_name_node = class_node.child_by_field_name("name")
    class_name = _node_text(source_bytes, class_name_node) if class_name_node else "unknown"

    body = class_node.child_by_field_name("body")
    method_nodes = (
        [child for child in body.children if child.type in _METHOD_NODE_TYPES]
        if body is not None else []
    )

    if not method_nodes:
        # No methods to split on (e.g. a plain data class) -- there's no
        # finer real structure to chunk against, so index it as one unit
        # (still subject to the MAX_AST_CHUNK_LINES cap below).
        return _definition_chunks(outer_node, source_bytes, file_path, language, repository_id, chunk_size)

    chunks = []

    for method_node in method_nodes:
        # A method's own text has no idea which class it belongs to --
        # without this, a chunk like "def save(self): self.x.write(...)"
        # is embedded and shown to the model with no way to know what
        # `self` even is.
        chunks.extend(_definition_chunks(
            method_node, source_bytes, file_path, language, repository_id, chunk_size,
            prefix=f"# Method of class {class_name}\n"
        ))

    class_start = outer_node.start_point[0] + 1
    class_end = outer_node.end_point[0] + 1
    method_ranges = [(m.start_point[0] + 1, m.end_point[0] + 1) for m in method_nodes]

    lines = source_bytes.decode("utf-8", errors="ignore").splitlines()
    for start, end in _residual_line_ranges(class_start, class_end, method_ranges):
        chunks.extend(_fixed_line_subchunks(
            lines, start, end, chunk_size, file_path, language, repository_id
        ))

    return chunks


def _tree_sitter_grammar_name(file_path: str, language: str) -> str:
    # TypeScript's plain grammar errors on JSX syntax -- .tsx needs the
    # dedicated "tsx" grammar (verified: same node types, just JSX-aware).
    # .jsx is fine as-is since the plain "javascript" grammar already
    # parses JSX without a separate grammar.
    if language == "typescript" and Path(file_path).suffix.lower() == ".tsx":
        return "tsx"
    return language


def _try_ast_chunks(
    content: str,
    file_path: str,
    language: str,
    repository_id: str,
    chunk_size: int
) -> list[CodeChunk] | None:
    config = _AST_SUPPORTED_LANGUAGES.get(language)
    if config is None:
        return None

    lines = content.splitlines()
    if not lines:
        return None

    source_bytes = content.encode("utf-8")
    parser = get_parser(_tree_sitter_grammar_name(file_path, language))
    root = parser.parse(source_bytes).root_node

    chunks = []
    covered_ranges = []

    for node in root.children:
        definition_node, kind = _classify_top_level_node(node, config)
        if definition_node is None:
            continue

        covered_ranges.append((node.start_point[0] + 1, node.end_point[0] + 1))

        if kind == "class":
            chunks.extend(_chunk_class(
                node, definition_node, source_bytes, file_path, language, repository_id, chunk_size
            ))
        else:
            chunks.extend(_definition_chunks(node, source_bytes, file_path, language, repository_id, chunk_size))

    if not covered_ranges:
        # Nothing AST-chunkable found at all (e.g. a script with only
        # top-level statements and no functions/classes) -- fixed-line
        # chunking is just as good here and this avoids ever returning a
        # single giant "whole file" chunk from this path.
        return None

    for start, end in _residual_line_ranges(1, len(lines), covered_ranges):
        chunks.extend(_fixed_line_subchunks(
            lines, start, end, chunk_size, file_path, language, repository_id
        ))

    return chunks