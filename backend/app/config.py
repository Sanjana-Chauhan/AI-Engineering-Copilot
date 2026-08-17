import os

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


# CORS — which frontend origin(s) may call this API. Comma-separated for
# multiple environments (e.g. a deployed frontend URL alongside local dev).
ALLOWED_ORIGINS = _split_csv(
    os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

CONVERSATIONS_DB_PATH = os.getenv("CONVERSATIONS_DB_PATH", "./data/conversations.db")
