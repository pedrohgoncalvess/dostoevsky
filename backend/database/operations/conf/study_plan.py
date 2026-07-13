import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select

from database.models.conf import StudyPlan
from database.operations import Interface


class StudyPlanRepository(Interface[StudyPlan]):
    def __init__(self, db):
        super().__init__(StudyPlan, db)

    async def create(
        self,
        user_id: int,
        study_language: str,
        self_declared_level: str,
        goal: str | None = None,
    ) -> StudyPlan:
        return await self.insert(
            StudyPlan(
                user_id=user_id,
                study_language=study_language,
                self_declared_level=self_declared_level,
                goal=goal,
            )
        )

    async def find_by_public_id(self, public_id: uuid.UUID) -> Optional[StudyPlan]:
        return await self.find_one_by(public_id=public_id)

    async def find_by_identifier(self, value: Any) -> Optional[StudyPlan]:
        parsed_uuid = _parse_uuid(value)
        if parsed_uuid:
            return await self.find_by_public_id(parsed_uuid)

        try:
            return await self.find_by_id(int(value))
        except (TypeError, ValueError):
            return None

    async def find_first_by_user(self, user_id: int) -> Optional[StudyPlan]:
        result = await self.db.execute(
            select(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.deleted_at.is_(None),
            )
            .order_by(self.model.id)
            .limit(1)
        )
        return result.scalars().first()

    async def find_active_by_user(self, user_id: int) -> list[StudyPlan]:
        result = await self.db.execute(
            select(self.model)
            .where(
                self.model.user_id == user_id,
                self.model.deleted_at.is_(None),
            )
            .order_by(self.model.id.desc())
        )
        return list(result.scalars().all())

    async def soft_delete(self, study_plan_id: int) -> Optional[StudyPlan]:
        return await self.update(
            study_plan_id, {"deleted_at": datetime.now(timezone.utc)}
        )


def _parse_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
