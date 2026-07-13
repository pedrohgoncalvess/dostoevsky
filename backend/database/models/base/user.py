from sqlalchemy import (
    Column, Integer, String,
    Boolean, DateTime, func, Text
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship
import uuid

from database.models.base_model import Base

LanguageEnum = ENUM(
    "portuguese", "english", "french", "spanish", "russian", "mandarim",
    name="language",
    create_type=False,
    schema="conf",
)


class User(Base):
    __tablename__ = "user"
    __table_args__ = {"schema": "base"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True, index=True)
    password = Column(Text, nullable=False)
    is_verified = Column(Boolean, nullable=False, default=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    native_language = Column(LanguageEnum, nullable=False, default="portuguese")
    inserted_at = Column(DateTime, nullable=False, default=func.now())
    deleted_at = Column(DateTime, nullable=True)

    refresh_tokens = relationship(
        "Refresh",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    preferences = relationship("UserPreference", back_populates="user")
    profiles = relationship("Profile", back_populates="user")
    study_plans = relationship("StudyPlan", back_populates="user")
    interactions = relationship("Interaction", back_populates="user")
    medias = relationship("Media", back_populates="user")
