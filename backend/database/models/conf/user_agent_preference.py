import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base


class UserAgentPreference(Base):
    __tablename__ = "user_agent_preference"
    __table_args__ = {"schema": "conf"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    agent_id = Column(Integer, ForeignKey("ai.agent.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("ai.model.id"), nullable=False)
    inserted_at = Column(DateTime, nullable=False, default=func.now())

    agent = relationship("Agent", back_populates="preferences")
    model = relationship("Model")
