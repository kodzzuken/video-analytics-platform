from sqlalchemy import Column, Integer, String, DateTime, UUID
from sqlalchemy.sql import func
from orchestrator.database import Base
import uuid

class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    scenario_uuid = Column(UUID(as_uuid=True), nullable=False)
    camera_url = Column(String, nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    process_pid = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    class Config:
        from_attributes = True
