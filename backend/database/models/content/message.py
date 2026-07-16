import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base


class Message(Base):
    __tablename__ = "message"
    __table_args__ = {"schema": "content"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    interaction_id = Column(Integer, ForeignKey("content.interaction.id"), nullable=False)
    media_id = Column(Integer, ForeignKey("content.media.id"), nullable=True)
    sent_by = Column(String(10), nullable=False)
    content = Column(Text, nullable=True)
    tip = Column(Text, nullable=True)
    correction = Column(Text, nullable=True)
    inserted_at = Column(DateTime, nullable=False, default=func.now())

    interaction = relationship("Interaction", back_populates="messages")
    media = relationship("Media", back_populates="messages")
