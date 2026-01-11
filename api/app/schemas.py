from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class ScenarioInitRequest(BaseModel):
    camera_url: str = Field(..., description="RTSP or HTTP URL to video stream")

class ScenarioResponse(BaseModel):
    scenario_uuid: UUID
    camera_url: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DetectionResult(BaseModel):
    class_label: str
    confidence: float
    bbox: List[float] = Field(..., description="[x_min, y_min, x_max, y_max]")

class FrameResult(BaseModel):
    frame_number: int
    detections: List[DetectionResult]
    timestamp: datetime

class PredictionResponse(BaseModel):
    scenario_uuid: UUID
    status: str
    total_frames_processed: int
    results: List[FrameResult]

    class Config:
        from_attributes = True

class ScenarioShutdownRequest(BaseModel):
    pass
