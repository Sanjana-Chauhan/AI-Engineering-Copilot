import hashlib
import re
import subprocess
import tempfile
from pathlib import Path


GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?/?$"
)


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


def clone_github_repository(repository_url: str) -> str:
    if not GITHUB_URL_PATTERN.match(repository_url):
        raise ValueError(
            "Only GitHub URLs of the form https://github.com/<owner>/<repo> are supported."
        )

    destination = Path(tempfile.gettempdir()) / "ai-copilot-repos" / hashlib.sha256(
        repository_url.encode()
    ).hexdigest()[:16]

    try:
        if destination.exists():
            subprocess.run(
                ["git", "-C", str(destination), "pull", "--ff-only"],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--depth", "1", "--", repository_url, str(destination)],
                check=True,
                capture_output=True,
                text=True,
            )
    except subprocess.CalledProcessError as error:
        raise ValueError(f"Failed to clone repository: {error.stderr.strip()}")

    return str(destination)