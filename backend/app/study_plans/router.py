from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.services import get_current_user
from database.connection import DatabaseConnection
from database.models.base import User
from database.operations.conf import StudyPlanRepository


router = APIRouter(prefix="/study-plans")


@router.post("")
async def create_study_plan(
    payload: dict[str, Any],
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
        )

    return _serialize(plan)


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
        "inserted_at": plan.inserted_at.isoformat() if plan.inserted_at else None,
        "deleted_at": plan.deleted_at.isoformat() if plan.deleted_at else None,
    }
