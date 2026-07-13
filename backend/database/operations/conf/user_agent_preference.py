from typing import Optional

from database.models.conf import UserAgentPreference
from database.operations import Interface


class UserAgentPreferenceRepository(Interface[UserAgentPreference]):
    def __init__(self, db):
        super().__init__(UserAgentPreference, db)

    async def find_by_agent_id(self, agent_id: int) -> list[UserAgentPreference]:
        return await self.find_by(agent_id=agent_id)

    async def find_by_agent_and_model(
        self,
        agent_id: int,
        model_id: int,
    ) -> Optional[UserAgentPreference]:
        return await self.find_one_by(agent_id=agent_id, model_id=model_id)
