from fastapi import APIRouter, HTTPException

from app.services.repository_service import scan_repository


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