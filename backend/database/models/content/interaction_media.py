import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base


class InteractionMedia(Base):
    __tablename__ = "interaction_media"
    __table_args__ = {"schema": "content"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    interaction_id = Column(Integer, ForeignKey("content.interaction.id"), nullable=False)
    media_id = Column(Integer, ForeignKey("content.media.id"), nullable=False)
    instruction = Column(Text, nullable=True)
    inserted_at = Column(DateTime, nullable=False, default=func.now())

    interaction = relationship("Interaction", back_populates="media_links")
    media = relationship("Media", back_populates="interaction_links")
