from typing import Optional

from sqlalchemy import select, update

from database.models.ai import LocalVoice
from database.operations import Interface


class LocalVoiceRepository(Interface[LocalVoice]):
    def __init__(self, db):
        super().__init__(LocalVoice, db)

    async def find_default_by_language(
        self, model_id: int, language: str
    ) -> Optional[LocalVoice]:
        result = await self.db.execute(
            select(self.model).where(
                self.model.model_id == model_id,
                self.model.language == language,
                self.model.is_default.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def find_by_voice_code(
        self, model_id: int, language: str, voice_code: str
    ) -> Optional[LocalVoice]:
        result = await self.db.execute(
            select(self.model).where(
                self.model.model_id == model_id,
                self.model.language == language,
                self.model.voice_code == voice_code,
            )
        )
        return result.scalar_one_or_none()

    async def mark_downloaded(self, voice_id: int) -> None:
        await self.db.execute(
            update(self.model)
            .where(self.model.id == voice_id)
            .values(downloaded=True)
        )
        await self.db.commit()
