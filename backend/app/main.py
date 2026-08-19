from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS
from app.routes.chat import router as chat_router
from app.routes.repository import router as repository_router, catalog_router as repository_catalog_router
from app.routes.ingestion import router as ingestion_router
from app.routes.search import router as search_router
from app.routes.rag import router as rag_router

app = FastAPI(title="Engineering Copilot API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)
app.include_router(repository_router)
app.include_router(repository_catalog_router)
app.include_router(ingestion_router)
app.include_router(search_router)
app.include_router(rag_router)


@app.get("/")
def root():
    return {
        "message": "Engineering Copilot API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }