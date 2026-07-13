from typing import Optional

from database.models.content import InteractionMedia
from database.operations import Interface


class InteractionMediaRepository(Interface[InteractionMedia]):
    def __init__(self, db):
        super().__init__(InteractionMedia, db)

    async def create_link(
        self,
        interaction_id: int,
        media_id: int,
        instruction: str | None = None,
    ) -> InteractionMedia:
        return await self.insert(
            InteractionMedia(
                interaction_id=interaction_id,
                media_id=media_id,
                instruction=instruction,
            )
        )

    async def find_by_interaction_and_media(
        self,
        interaction_id: int,
        media_id: int,
    ) -> Optional[InteractionMedia]:
        return await self.find_one_by(interaction_id=interaction_id, media_id=media_id)
