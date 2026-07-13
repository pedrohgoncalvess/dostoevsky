import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base


class Interaction(Base):
    __tablename__ = "interaction"
    __table_args__ = {"schema": "content"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    profile_id = Column(Integer, ForeignKey("base.profile.id"), nullable=False)
    study_plan_id = Column(Integer, ForeignKey("conf.study_plan.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("base.user.id"), nullable=False)
    plan_id = Column(Integer, nullable=True)
    name = Column(String(70), nullable=True)
    initial_context = Column(Text, nullable=True)
    need_tip = Column(Boolean, nullable=False, default=False)
    inserted_at = Column(DateTime, nullable=False, default=func.now())

    profile = relationship("Profile", back_populates="interactions")
    study_plan = relationship("StudyPlan", back_populates="interactions")
    user = relationship("User", back_populates="interactions")
    media_links = relationship("InteractionMedia", back_populates="interaction")
    messages = relationship("Message", back_populates="interaction")
