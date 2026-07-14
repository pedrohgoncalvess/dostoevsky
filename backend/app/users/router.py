from fastapi import Depends, APIRouter, HTTPException
from starlette import status

from app.auth.models import UserCreate
from app.auth.services import get_current_user
from app.users.services import get_password_hash
from database.connection import DatabaseConnection
from database.models.ai import Model
from database.models.base import User
from database.models.conf import UserPreference
from database.operations.ai import ModelRepository
from database.operations.base.user import UserRepository
from database.operations.conf import UserPreferenceRepository


router = APIRouter(
    prefix="/users",
)


async def _create_default_preferences(conn, user_id: int) -> None:
    model_repo = ModelRepository(conn)
    stt_model = await model_repo.find_by_openrouter_id("local:faster-whisper")
    tts_model = await model_repo.find_by_openrouter_id("local:kokoro")

    preference = UserPreference(
        user_id=user_id,
        stt_model_id=stt_model.id if stt_model else None,
        tts_model_id=tts_model.id if tts_model else None,
        voice="af_heart",
    )
    await UserPreferenceRepository(conn).insert(preference)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    async with DatabaseConnection() as conn:

        user_repository = UserRepository(conn)
        exists = await user_repository.find_by_email(user.email)
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered."
            )

        hashed_password = get_password_hash(user.password)
        new_user = User(
            email=user.email,
            name=user.name,
            password=hashed_password
        )
        _ = await user_repository.insert(new_user)
        await _create_default_preferences(conn, new_user.id)

    return {
        "id": new_user.id,
        "public_id": new_user.public_id,
        "name": new_user.name,
        "email": new_user.email,
        "is_verified": new_user.is_verified,
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "name": user.name,
        "email": user.email,
        "native_language": user.native_language,
    }
