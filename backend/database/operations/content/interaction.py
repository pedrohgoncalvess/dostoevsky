import uuid
from typing import Any, Optional

from sqlalchemy import desc, select

from database.models.content import Interaction, Profile
from database.operations import Interface


class InteractionRepository(Interface[Interaction]):
    def __init__(self, db):
        super().__init__(Interaction, db)

    async def find_by_public_id(self, public_id: uuid.UUID) -> Optional[Interaction]:
        return await self.find_one_by(public_id=public_id)

    async def find_for_user_by_identifier(
        self,
        value: Any,
        user_id: int,
    ) -> Optional[Interaction]:
        parsed_uuid = _parse_uuid(value)
        if parsed_uuid:
            result = await self.db.execute(
                select(self.model).where(
                    self.model.public_id == parsed_uuid,
                    self.model.user_id == user_id,
                )
            )
            return result.scalar_one_or_none()

        try:
            interaction_id = int(value)
        except (TypeError, ValueError):
            return None

        result = await self.db.execute(
            select(self.model).where(
                self.model.id == interaction_id,
                self.model.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_interaction(
        self,
        profile_id: int,
        user_id: int,
        study_plan_id: int,
        name: str | None = None,
        initial_context: str | None = None,
        need_tip: bool = False,
    ) -> Interaction:
        return await self.insert(
            Interaction(
                profile_id=profile_id,
                user_id=user_id,
                study_plan_id=study_plan_id,
                name=name,
                initial_context=initial_context,
                need_tip=need_tip,
            )
        )

    async def find_recent_by_user(
        self,
        user_id: int,
        limit: int = 20,
    ) -> list[Interaction]:
        """Return the *limit* most recent interactions for a user, ordered by
        ``inserted_at DESC`` (falling back to ``id DESC``) — all in SQL."""
        result = await self.db.execute(
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(
                desc(self.model.inserted_at),
                desc(self.model.id),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_with_profile(self, interaction_id: int) -> tuple[Interaction, Profile] | None:
        result = await self.db.execute(
            select(Interaction, Profile)
            .join(Profile, Profile.id == Interaction.profile_id)
            .where(Interaction.id == interaction_id)
        )
        row = result.one_or_none()
        if not row:
            return None
        interaction, profile = row
        return interaction, profile


def _parse_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
