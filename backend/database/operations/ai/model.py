from typing import Optional

from sqlalchemy import select

from database.models.ai import Model
from database.operations import Interface


class ModelRepository(Interface[Model]):
    def __init__(self, db):
        super().__init__(Model, db)

    async def find_by_external_id(self, external_id: str) -> Optional[Model]:
        return await self.find_one_by(external_id=external_id, deleted_at=None)

    async def find_first_text_model(self) -> Optional[Model]:
        result = await self.db.execute(
            select(self.model).where(
                self.model.for_text.is_(True),
                self.model.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    async def find_first_planning_model(self) -> Optional[Model]:
        result = await self.db.execute(
            select(self.model).where(
                self.model.for_planning.is_(True),
                self.model.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    async def find_first_tts_model(self) -> Optional[Model]:
        result = await self.db.execute(
            select(self.model).where(
                self.model.for_tts.is_(True),
                self.model.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    async def find_first_stt_model(self) -> Optional[Model]:
        result = await self.db.execute(
            select(self.model).where(
                self.model.for_stt.is_(True),
                self.model.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    async def find_first_embedding_model(self) -> Optional[Model]:
        result = await self.db.execute(
            select(self.model).where(
                self.model.for_embedding.is_(True),
                self.model.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    async def find_chat_model(self, preferred_external_id: str) -> Optional[Model]:
        model = await self.find_by_external_id(preferred_external_id)
        if model:
            return model
        return await self.find_first_text_model()
