from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.auth.services import get_current_user
from app.media.auth import require_admin_or_owner
from app.media.services import delete_media, get_media, list_user_media, process_media_upload, update_media
from database.models.base import User


router = APIRouter(prefix="/media")


@router.post("")
async def upload_media(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is required.",
        )

    content = await file.read()
    try:
        return await process_media_upload(
            user=user,
            content=content,
            filename=file.filename,
            content_type=file.content_type,
            name=name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/medias")
async def list_medias(user: User = Depends(get_current_user)) -> list[dict[str, Any]]:
    return await list_user_media(user)


@router.get("/{media_id}")
async def retrieve_media(
    media_id: str,
    _: None = Depends(require_admin_or_owner),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    media = await get_media(user, media_id)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found.",
        )
    return media


@router.get("/{media_id}/file")
async def retrieve_media_file(
    media_id: str,
    _: None = Depends(require_admin_or_owner),
    user: User = Depends(get_current_user),
) -> Any:
    from fastapi.responses import FileResponse
    from app.media.storage import media_root

    media = await get_media(user, media_id)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found.",
        )
    
    file_path = media_root() / media["subpath"]
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk.",
        )
        
    return FileResponse(path=file_path, filename=media["name"])


@router.delete("/{media_id}")
async def remove_media(
    media_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    deleted = await delete_media(user, media_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found.",
        )
    return {"deleted": True}


@router.patch("/{media_id}")
async def edit_media(
    media_id: str,
    payload: dict[str, Any],
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    media = await update_media(user, media_id, payload)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found.",
        )
    return media
