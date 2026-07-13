from typing import Optional

from database.models.conf import UserPreference
from database.operations import Interface


class UserPreferenceRepository(Interface[UserPreference]):
    def __init__(self, db):
        super().__init__(UserPreference, db)

    async def find_by_user_id(self, user_id: int) -> Optional[UserPreference]:
        return await self.find_one_by(user_id=user_id)
