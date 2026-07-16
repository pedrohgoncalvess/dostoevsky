from sqlalchemy import select

from database.models.content import Message
from database.operations import Interface


class MessageRepository(Interface[Message]):
    def __init__(self, db):
        super().__init__(Message, db)

    async def create_message(
        self,
        interaction_id: int,
        sent_by: str,
        content: str | None = None,
        media_id: int | None = None,
        tip: str | None = None,
        correction: str | None = None,
    ) -> Message:
        return await self.insert(
            Message(
                interaction_id=interaction_id,
                sent_by=sent_by,
                content=content,
                media_id=media_id,
                tip=tip,
                correction=correction,
            )
        )

    async def find_by_interaction_id(self, interaction_id: int) -> list[Message]:
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(self.model)
            .options(selectinload(self.model.media))
            .where(self.model.interaction_id == interaction_id)
            .order_by(self.model.id)
        )
        return list(result.scalars().all())

    async def build_chat_messages(self, interaction_id: int) -> list[dict[str, str]]:
        messages = await self.find_by_interaction_id(interaction_id)
        history = []
        for message in messages:
            if message.sent_by not in {"user", "assistant"} or not message.content:
                continue
            history.append({"role": message.sent_by, "content": message.content})
        return history
