from sqlalchemy.orm import Session
from app import models, schemas
from app.kafka_producer import get_kafka_producer
import uuid
from datetime import datetime
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class ScenarioService:
    @staticmethod
    def init_scenario(db: Session, request: schemas.ScenarioInitRequest) -> schemas.ScenarioResponse:
        """Initialize new scenario with transactional outbox pattern"""
        scenario_uuid = uuid.uuid4()
        
        try:
            # Create scenario record
            scenario = models.Scenario(
                scenario_uuid=scenario_uuid,
                camera_url=request.camera_url,
                status="init_startup"
            )
            db.add(scenario)
            db.flush()  # Ensure scenario is written before outbox
            
            # Create outbox record (same transaction)
            outbox_record = models.OutboxScenario(
                scenario_uuid=scenario_uuid,
                payload={
                    "scenario_uuid": str(scenario_uuid),
                    "camera_url": request.camera_url
                },
                published=False
            )
            db.add(outbox_record)
            
            # Commit both records in single transaction
            db.commit()
            db.refresh(scenario)
            
            # Send to Kafka (outside transaction for idempotency)
            kafka_producer = get_kafka_producer()
            kafka_producer.send_init_scenario(str(scenario_uuid), request.camera_url)
            
            # Mark as published
            outbox_record.published = True
            outbox_record.published_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Scenario {scenario_uuid} initialized")
            return schemas.ScenarioResponse.from_orm(scenario)
        
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to initialize scenario: {str(e)}")
            raise
    
    @staticmethod
    def get_scenario(db: Session, scenario_uuid: str) -> Optional[schemas.ScenarioResponse]:
        """Get scenario by UUID"""
        scenario = db.query(models.Scenario).filter(
            models.Scenario.scenario_uuid == uuid.UUID(scenario_uuid)
        ).first()
        return schemas.ScenarioResponse.from_orm(scenario) if scenario else None
    
    @staticmethod
    def get_predictions(db: Session, scenario_uuid: str) -> Optional[schemas.PredictionResponse]:
        """Get predictions/results for scenario"""
        scenario_id = uuid.UUID(scenario_uuid)
        
        scenario = db.query(models.Scenario).filter(
            models.Scenario.scenario_uuid == scenario_id
        ).first()
        
        if not scenario:
            return None
        
        results = db.query(models.ScenarioResult).filter(
            models.ScenarioResult.scenario_uuid == scenario_id
        ).order_by(models.ScenarioResult.frame_number).all()
        
        frame_results = []
        for result in results:
            detections = [
                schemas.DetectionResult(
                    class_label=det["class"],
                    confidence=det["confidence"],
                    bbox=det["bbox"]
                )
                for det in result.detections
            ]
            frame_results.append(
                schemas.FrameResult(
                    frame_number=result.frame_number,
                    detections=detections,
                    timestamp=result.timestamp
                )
            )
        
        return schemas.PredictionResponse(
            scenario_uuid=scenario_id,
            status=scenario.status,
            total_frames_processed=len(frame_results),
            results=frame_results
        )
    
    @staticmethod
    def save_result(db: Session, scenario_uuid: str, frame_number: int, detections: List[dict], timestamp: datetime):
        """Save prediction result (idempotent - upsert)"""
        try:
            scenario_id = uuid.UUID(scenario_uuid)
            
            # Check if exists
            existing = db.query(models.ScenarioResult).filter(
                models.ScenarioResult.scenario_uuid == scenario_id,
                models.ScenarioResult.frame_number == frame_number
            ).first()
            
            if existing:
                existing.detections = detections
                existing.timestamp = timestamp
            else:
                result = models.ScenarioResult(
                    scenario_uuid=scenario_id,
                    frame_number=frame_number,
                    detections=detections,
                    timestamp=timestamp
                )
                db.add(result)
            
            db.commit()
            logger.info(f"Saved result for scenario {scenario_uuid} frame {frame_number}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save result: {str(e)}")
            raise
