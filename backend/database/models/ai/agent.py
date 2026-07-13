import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base


class Agent(Base):
    __tablename__ = "agent"
    __table_args__ = {"schema": "ai"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    model_id = Column(Integer, ForeignKey("ai.model.id"), nullable=False)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    prompt = Column(Text, nullable=False)
    structured_output = Column(JSONB, nullable=True)
    placeholders = Column(ARRAY(String), nullable=True)
    inserted_at = Column(DateTime, nullable=False, default=func.now())

    model = relationship("Model", back_populates="agents")
    preferences = relationship("UserAgentPreference", back_populates="agent")
