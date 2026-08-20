from fastapi import APIRouter, HTTPException

from app.services import conversation_service
from app.services.repository_catalog_service import delete_repository, list_repositories
from app.services.repository_service import clone_github_repository, scan_repository
from app.services.vector_store import delete_repository_chunks


router = APIRouter(prefix="/api/repository")
catalog_router = APIRouter(prefix="/api/repositories")


@router.get("/scan")
def scan(repository_path: str):

    try:
        files = scan_repository(repository_path)

        return {
            "repository": repository_path,
            "file_count": len(files),
            "files": files
        }

    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@router.post("/clone")
def clone(repository_url: str):

    try:
        repository_path = clone_github_repository(repository_url)

        return {
            "repository_url": repository_url,
            "repository_path": repository_path
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@catalog_router.get("")
def list_previously_ingested_repositories():
    return {"repositories": list_repositories()}


@catalog_router.get("/{repository_id}/conversations")
def list_conversations_for_repository(repository_id: str):
    return {"conversations": conversation_service.list_conversations(repository_id)}


@catalog_router.delete("/{repository_id}")
def delete_repository_and_its_data(repository_id: str):
    conversation_service.delete_conversations_for_repository(repository_id)
    delete_repository_chunks(repository_id)
    delete_repository(repository_id)
    return {"repository_id": repository_id, "deleted": True}