from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chat import router as chat_router
from app.routes.repository import router as repository_router
from app.routes.ingestion import router as ingestion_router

app = FastAPI(title="Engineering Copilot API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)
app.include_router(repository_router)
app.include_router(ingestion_router)


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