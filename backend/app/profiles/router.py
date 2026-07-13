from fastapi import APIRouter, Depends

from app.auth.services import get_current_user
from database.connection import DatabaseConnection
from database.models.base import User
from database.operations.content import ProfileRepository


router = APIRouter(prefix="/profiles")


@router.get("")
async def list_profiles(user: User = Depends(get_current_user)):
    async with DatabaseConnection() as conn:
        profiles = await ProfileRepository(conn).find_all(limit=100)
    return [
        {
            "id": p.id,
            "public_id": str(p.public_id),
            "name": p.name,
            "description": p.description,
        }
        for p in profiles
    ]
