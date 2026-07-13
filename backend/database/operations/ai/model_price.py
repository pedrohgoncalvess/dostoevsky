from datetime import datetime
from typing import Optional

from sqlalchemy import select

from database.models.ai import ModelPrice
from database.operations import Interface


class ModelPriceRepository(Interface[ModelPrice]):
    def __init__(self, db):
        super().__init__(ModelPrice, db)

    async def find_current_by_model_id(self, model_id: int) -> Optional[ModelPrice]:
        result = await self.db.execute(
            select(self.model)
            .where(
                self.model.model_id == model_id,
                self.model.valid_from <= datetime.utcnow(),
            )
            .order_by(self.model.valid_from.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def find_last_inserted(self) -> Optional[ModelPrice]:
        result = await self.db.execute(
            select(self.model).order_by(self.model.valid_from.desc()).limit(1)
        )
        return result.scalar_one_or_none()
