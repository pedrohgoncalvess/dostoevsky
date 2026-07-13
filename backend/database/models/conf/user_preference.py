import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base


class UserPreference(Base):
    __tablename__ = "user_preference"
    __table_args__ = {"schema": "conf"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("base.user.id"), nullable=False)
    tts_model_id = Column(Integer, ForeignKey("ai.model.id"), nullable=True)
    stt_model_id = Column(Integer, ForeignKey("ai.model.id"), nullable=True)
    planning_model_id = Column(Integer, ForeignKey("ai.model.id"), nullable=True)
    voice = Column(String(20), nullable=True)
    inserted_at = Column(DateTime, nullable=False, default=func.now())

    user = relationship("User", back_populates="preferences")
    tts_model = relationship("Model", foreign_keys=[tts_model_id])
    stt_model = relationship("Model", foreign_keys=[stt_model_id])
    planning_model = relationship("Model", foreign_keys=[planning_model_id])
