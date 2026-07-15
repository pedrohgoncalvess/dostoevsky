from typing import Optional

from sqlalchemy import select, update

from database.models.ai import Voice
from database.operations import Interface


class VoiceRepository(Interface[Voice]):
    def __init__(self, db):
        super().__init__(Voice, db)

    async def find_default_by_language(
        self, model_id: int, language: str
    ) -> Optional[Voice]:
        result = await self.db.execute(
            select(self.model).where(
                self.model.model_id == model_id,
                self.model.language == language,
                self.model.is_default.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def find_by_voice_code(
        self,
        voice_code: str,
        model_id: int | None = None,
        language: str | None = None,
    ) -> Optional[Voice]:
        conditions = [self.model.voice_code == voice_code]
        if model_id is not None:
            conditions.append(self.model.model_id == model_id)
        if language is not None:
            conditions.append(self.model.language == language)
        result = await self.db.execute(select(self.model).where(*conditions))
        return result.scalar_one_or_none()

    async def mark_downloaded(self, voice_id: int) -> None:
        await self.db.execute(
            update(self.model)
            .where(self.model.id == voice_id)
            .values(downloaded=True)
        )
        await self.db.commit()
