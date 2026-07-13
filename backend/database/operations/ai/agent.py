from typing import Optional

from database.models.ai import Agent
from database.operations import Interface


class AgentRepository(Interface[Agent]):
    def __init__(self, db):
        super().__init__(Agent, db)

    async def find_by_name(self, name: str) -> Optional[Agent]:
        return await self.find_one_by(name=name)
