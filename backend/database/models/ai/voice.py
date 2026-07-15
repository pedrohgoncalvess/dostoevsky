import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base


class Voice(Base):
    __tablename__ = "voice"
    __table_args__ = {"schema": "ai"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    model_id = Column(Integer, ForeignKey("ai.model.id"), nullable=False)
    language = Column(String(30), nullable=False)
    voice_code = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    downloaded = Column(Boolean, nullable=False, default=False)
    download_status = Column(String(20), nullable=False, default="not_downloaded")
    inserted_at = Column(DateTime, nullable=False, default=func.now())

    model = relationship("Model", back_populates="voice_entries")
