import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base

LanguageEnum = ENUM(
    "portuguese", "english", "french", "spanish", "russian", "mandarim",
    name="language",
    create_type=False,
    schema="conf",
)

KnowledgeLevelEnum = ENUM(
    "a1", "a2", "b1", "b2", "c1", "c2",
    name="knowledge_level",
    create_type=False,
    schema="conf",
)


class StudyPlan(Base):
    __tablename__ = "study_plan"
    __table_args__ = {"schema": "conf"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("base.user.id"), nullable=False)
    study_language = Column(LanguageEnum, nullable=False)
    self_declared_level = Column(KnowledgeLevelEnum, nullable=False)
    goal = Column(Text, nullable=True)
    setup_completed = Column(Boolean, nullable=False, default=False)
    inserted_at = Column(DateTime, nullable=False, default=func.now())
    deleted_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="study_plans")
    interactions = relationship("Interaction", back_populates="study_plan")
