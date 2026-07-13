from fastapi import Depends, HTTPException, status

from app.auth.services import get_current_user
from database.connection import DatabaseConnection
from database.models.base import User
from database.operations.content import MediaRepository


async def require_admin_or_owner(
    media_id: str,
    user: User = Depends(get_current_user),
) -> None:
    if user.is_admin:
        return

    async with DatabaseConnection() as conn:
        media = await MediaRepository(conn).find_by_identifier(media_id)

    if not media or media.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found.",
        )
