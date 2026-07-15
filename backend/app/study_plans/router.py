import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from app.auth.services import get_current_user

logger = logging.getLogger(__name__)
from app.conversation.local_model_manager import ensure_local_models_for_study_plan
from database.connection import DatabaseConnection
from database.models.base import User
from database.operations.conf import StudyPlanRepository


router = APIRouter(prefix="/study-plans")


@router.post("")
async def create_study_plan(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    study_language = (payload.get("study_language") or "").strip()
    self_declared_level = (payload.get("self_declared_level") or "").strip()
    goal = payload.get("goal")

    if not study_language:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="study_language is required.",
        )
    if not self_declared_level:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="self_declared_level is required.",
        )

    async with DatabaseConnection() as conn:
        plan = await StudyPlanRepository(conn).create(
            user_id=user.id,
            study_language=study_language,
            self_declared_level=self_declared_level,
            goal=goal,
            setup_completed=False,
        )

    background_tasks.add_task(
        background_download_models, user.id, study_language, plan.id
    )

    return {"plan": _serialize(plan), "feedback": "Download initiated"}

async def background_download_models(user_id: int, study_language: str, plan_id: int):
    try:
        from app.conversation.local_model_manager import ensure_local_models_for_study_plan
        from app.conversation.providers import FasterWhisperSTTProvider
        
        await ensure_local_models_for_study_plan(user_id, study_language)
        async with DatabaseConnection() as conn:
            from database.operations.ai import ModelRepository
            import asyncio
            model_repo = ModelRepository(conn)
            whisper_model = await model_repo.find_first_stt_model()
            if whisper_model and whisper_model.download_status != "downloaded":
                if whisper_model.download_status == "processing":
                    while whisper_model.download_status == "processing":
                        await asyncio.sleep(2)
                        await conn.refresh(whisper_model)
                else:
                    whisper_model.download_status = "processing"
                    await conn.commit()
                    try:
                        await FasterWhisperSTTProvider()._ensure_model()
                        whisper_model.download_status = "downloaded"
                        await conn.commit()
                    except Exception:
                        whisper_model.download_status = "not_downloaded"
                        await conn.commit()
                        raise
            await StudyPlanRepository(conn).update(plan_id, {"setup_completed": True})
    except Exception:
        logger.exception("Failed to activate local models in background")


@router.get("")
async def list_study_plans(
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    async with DatabaseConnection() as conn:
        plans = await StudyPlanRepository(conn).find_active_by_user(user.id)

    return [_serialize(p) for p in plans]


@router.get("/{study_plan_id}")
async def get_study_plan(
    study_plan_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    async with DatabaseConnection() as conn:
        plan = await StudyPlanRepository(conn).find_by_identifier(study_plan_id)

    if not plan or plan.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study plan not found.",
        )

    return _serialize(plan)


@router.patch("/{study_plan_id}")
async def update_study_plan(
    study_plan_id: str,
    payload: dict[str, Any],
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    async with DatabaseConnection() as conn:
        repository = StudyPlanRepository(conn)
        plan = await repository.find_by_identifier(study_plan_id)

        if not plan or plan.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study plan not found.",
            )

        data: dict[str, Any] = {}
        if "study_language" in payload:
            data["study_language"] = payload["study_language"]
        if "self_declared_level" in payload:
            data["self_declared_level"] = payload["self_declared_level"]
        if "goal" in payload:
            data["goal"] = payload["goal"]

        if data:
            updated = await repository.update(plan.id, data)
            if updated:
                plan = updated

    return _serialize(plan)


@router.delete("/{study_plan_id}")
async def delete_study_plan(
    study_plan_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    async with DatabaseConnection() as conn:
        repository = StudyPlanRepository(conn)
        plan = await repository.find_by_identifier(study_plan_id)

        if not plan or plan.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study plan not found.",
            )

        await repository.soft_delete(plan.id)

    return {"deleted": True}


def _serialize(plan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "public_id": str(plan.public_id),
        "user_id": plan.user_id,
        "study_language": plan.study_language,
        "self_declared_level": plan.self_declared_level,
        "goal": plan.goal,
        "setup_completed": plan.setup_completed,
        "inserted_at": plan.inserted_at.isoformat() if plan.inserted_at else None,
        "deleted_at": plan.deleted_at.isoformat() if plan.deleted_at else None,
    }
