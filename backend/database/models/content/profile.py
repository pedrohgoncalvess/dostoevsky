import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base


class Profile(Base):
    __tablename__ = "profile"
    __table_args__ = {"schema": "base"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("base.user.id"), nullable=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=False, unique=True)
    teacher_context = Column(Boolean, nullable=False, default=True)
    tip = Column(Text, nullable=True)
    prompt = Column(Text, nullable=True)
    inserted_at = Column(DateTime, nullable=False, default=func.now())

    user = relationship("User", back_populates="profiles")
    interactions = relationship("Interaction", back_populates="profile")
