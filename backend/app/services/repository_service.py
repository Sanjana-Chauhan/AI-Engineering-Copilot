from pathlib import Path


IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    "venv",
    "__pycache__",
    ".next",
    "dist",
    "build"
}


ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".cs",
    ".go",
    ".rs",
    ".html",
    ".css",
    ".json",
    ".md"
}


def scan_repository(repository_path: str) -> list[str]:
    path = Path(repository_path)

    if not path.exists():
        raise FileNotFoundError("Repository path does not exist.")

    if not path.is_dir():
        raise ValueError("Repository path must be a directory.")

    files = []

    for file_path in path.rglob("*"):

        if not file_path.is_file():
            continue

        if any(
            directory in IGNORED_DIRECTORIES
            for directory in file_path.parts
        ):
            continue

        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        relative_path = file_path.relative_to(path)

        files.append(str(relative_path))

    return files