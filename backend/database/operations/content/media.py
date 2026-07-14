import uuid
from typing import Any, Optional

from sqlalchemy import text

from database.models.content import Media
from database.operations import Interface


class MediaRepository(Interface[Media]):
    def __init__(self, db):
        super().__init__(Media, db)

    async def create_user_media(
        self,
        user_id: int,
        name: str,
        bucket: str,
        subpath: str,
        media_format: str,
        description: str | None = None,
        transcription: str | None = None,
        embedding: list[float] | None = None,
    ) -> Media:
        media = Media(
            user_id=user_id,
            name=name,
            bucket=bucket,
            subpath=subpath,
            format=media_format,
            description=description,
            transcription=transcription,
        )
        result = await self.insert(media)

        if embedding:
            await self.update_embedding(result.id, embedding)

        return result

    async def update_transcription(self, media_id: int, transcription: str) -> None:
        media = await self.find_by_id(media_id)
        if media:
            media.transcription = transcription
            await self.db.commit()

    async def update_embedding(self, media_id: int, embedding: list[float]) -> None:
        vector_literal = "[" + ",".join(str(v) for v in embedding) + "]"
        await self.db.execute(
            text(
                'UPDATE "content"."media" SET "embedding" = :embedding::vector WHERE "id" = :id'
            ),
            {"embedding": vector_literal, "id": media_id},
        )
        await self.db.commit()

    async def find_by_public_id(self, public_id: uuid.UUID) -> Optional[Media]:
        return await self.find_one_by(public_id=public_id)

    async def find_by_identifier(self, value: Any) -> Optional[Media]:
        parsed_uuid = _parse_uuid(value)
        if parsed_uuid:
            return await self.find_by_public_id(parsed_uuid)

        try:
            return await self.find_by_id(int(value))
        except (TypeError, ValueError):
            return None

    async def find_by_user(self, user_id: int) -> list[Media]:
        return await self.find_by(user_id=user_id)


def _parse_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
