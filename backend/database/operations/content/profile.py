import uuid
from typing import Any, Optional

from database.models.content import Profile
from database.operations import Interface


class ProfileRepository(Interface[Profile]):
    def __init__(self, db):
        super().__init__(Profile, db)

    async def find_by_name(self, name: str) -> Optional[Profile]:
        return await self.find_one_by(name=name)

    async def find_by_public_id(self, public_id: uuid.UUID) -> Optional[Profile]:
        return await self.find_one_by(public_id=public_id)

    async def find_by_identifier(self, value: Any) -> Optional[Profile]:
        parsed_uuid = _parse_uuid(value)
        if parsed_uuid:
            return await self.find_by_public_id(parsed_uuid)

        try:
            return await self.find_by_id(int(value))
        except (TypeError, ValueError):
            return None


def _parse_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
