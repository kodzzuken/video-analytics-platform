from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSONB, UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid

class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    scenario_uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    camera_url = Column(String, nullable=False)
    status = Column(String(50), nullable=False, default="init_startup")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    class Config:
        from_attributes = True

class OutboxScenario(Base):
    __tablename__ = "outbox_scenario"

    id = Column(Integer, primary_key=True, index=True)
    scenario_uuid = Column(UUID(as_uuid=True), nullable=False)
    payload = Column(JSONB, nullable=False)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True))

    class Config:
        from_attributes = True

class ScenarioResult(Base):
    __tablename__ = "scenario_results"

    id = Column(Integer, primary_key=True, index=True)
    scenario_uuid = Column(UUID(as_uuid=True), nullable=False)
    frame_number = Column(Integer, nullable=False)
    detections = Column(JSONB, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    class Config:
        from_attributes = True
