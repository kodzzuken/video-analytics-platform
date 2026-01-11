from kafka import KafkaConsumer
from app.config import settings
from app.database import SessionLocal
from app import services
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class InboxConsumer:
    def __init__(self):
        self.consumer = KafkaConsumer(
            'results',
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id='api-inbox-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
    
    def start(self):
        """Start consuming results from runner"""
        logger.info("Inbox consumer started")
        db = SessionLocal()
        
        try:
            for message in self.consumer:
                try:
                    payload = message.value
                    scenario_uuid = payload.get('scenario_uuid')
                    frame_number = payload.get('frame_number')
                    detections = payload.get('detections', [])
                    timestamp_str = payload.get('timestamp')
                    
                    if not all([scenario_uuid, frame_number is not None, timestamp_str]):
                        logger.warning(f"Invalid message format: {payload}")
                        continue
                    
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    
                    # Idempotent save
                    services.ScenarioService.save_result(
                        db, scenario_uuid, frame_number, detections, timestamp
                    )
                    
                    logger.info(f"Processed result for {scenario_uuid} frame {frame_number}")
                
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    continue
        
        except KeyboardInterrupt:
            logger.info("Inbox consumer stopped")
        finally:
            db.close()
            self.consumer.close()

def start_inbox_consumer():
    """Entry point for inbox consumer"""
    consumer = InboxConsumer()
    consumer.start()
