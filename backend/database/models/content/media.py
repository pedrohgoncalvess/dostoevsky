import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base


class Media(Base):
    __tablename__ = "media"
    __table_args__ = {"schema": "content"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("base.user.id"), nullable=False)
    name = Column(String(100), nullable=False)
    bucket = Column(String(50), nullable=False)
    subpath = Column(String(80), nullable=False)
    format = Column(String(10), nullable=False)
    transcription = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    inserted_at = Column(DateTime, nullable=False, default=func.now())

    user = relationship("User", back_populates="medias")
    interaction_links = relationship("InteractionMedia", back_populates="media")
    messages = relationship("Message", back_populates="media")
