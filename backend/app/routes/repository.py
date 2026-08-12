from fastapi import APIRouter, HTTPException

from app.services.repository_service import clone_github_repository, scan_repository


router = APIRouter(prefix="/api/repository")


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