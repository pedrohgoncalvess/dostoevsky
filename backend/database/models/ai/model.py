import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from database.models.base_model import Base


class Model(Base):
    __tablename__ = "model"
    __table_args__ = {"schema": "ai"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    public_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    evaluation = Column(Text, nullable=True)
    openrouter_id = Column(Text, nullable=False)
    for_embedding = Column(Boolean, nullable=False, default=False)
    for_text = Column(Boolean, nullable=False, default=False)
    for_tts = Column(Boolean, nullable=False, default=False)
    for_stt = Column(Boolean, nullable=False, default=False)
    for_planning = Column(Boolean, nullable=False, default=False)
    voices = Column(ARRAY(Text), nullable=True)
    inserted_at = Column(DateTime, nullable=False, default=func.now())
    deleted_at = Column(DateTime, nullable=True)

    prices = relationship("ModelPrice", back_populates="model")
    agents = relationship("Agent", back_populates="model")


class ModelPrice(Base):
    __tablename__ = "model_price"
    __table_args__ = {"schema": "ai"}

    valid_from = Column(DateTime, primary_key=True, nullable=False, default=func.now())
    model_id = Column(Integer, ForeignKey("ai.model.id"), primary_key=True, nullable=False)
    input_price = Column(Numeric(10, 3), nullable=True)
    output_price = Column(Numeric(10, 3), nullable=True)

    model = relationship("Model", back_populates="prices")
