from kafka import KafkaConsumer
from orchestrator.config import settings
from orchestrator.database import SessionLocal
from orchestrator.models import Worker
from orchestrator.kafka_producer import get_kafka_producer
import json
import logging
import uuid

logger = logging.getLogger(__name__)

class OrchestratorService:
    def __init__(self):
        self.consumer = KafkaConsumer(
            'init_scenario',
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.consumer_group,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        self.producer = get_kafka_producer()
        self.db = SessionLocal()
    
    def start(self):
        """Start orchestrator - consume init_scenario, send deploy orders"""
        logger.info("Orchestrator started")
        
        try:
            for message in self.consumer:
                try:
                    payload = message.value
                    scenario_uuid = payload.get('scenario_uuid')
                    camera_url = payload.get('camera_url')
                    
                    if not scenario_uuid or not camera_url:
                        logger.warning(f"Invalid message format: {payload}")
                        continue
                    
                    self.process_scenario(scenario_uuid, camera_url)
                    logger.info(f"Processed scenario {scenario_uuid}")
                
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    continue
        
        except KeyboardInterrupt:
            logger.info("Orchestrator stopped")
        finally:
            self.cleanup()
    
    def process_scenario(self, scenario_uuid: str, camera_url: str):
        """
        Process scenario:
        1. Create worker record
        2. Send deploy order to runner
        """
        try:
            worker_id = uuid.uuid4()
            
            # Create worker record
            worker = Worker(
                worker_id=worker_id,
                scenario_uuid=uuid.UUID(scenario_uuid),
                camera_url=camera_url,
                status="pending"
            )
            self.db.add(worker)
            self.db.commit()
            self.db.refresh(worker)
            
            logger.info(f"Created worker {worker_id} for scenario {scenario_uuid}")
            
            # Send deploy order to runner
            self.producer.send_deploy_order(
                str(worker_id),
                scenario_uuid,
                camera_url
            )
            
            # Update worker status
            worker.status = "deployed"
            self.db.commit()
            
            logger.info(f"Sent deploy order for worker {worker_id}")
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to process scenario: {str(e)}")
            raise
    
    def cleanup(self):
        """Cleanup resources"""
        self.db.close()
        self.consumer.close()
        self.producer.close()
        logger.info("Orchestrator cleaned up")

def start_orchestrator():
    """Entry point for orchestrator"""
    from orchestrator.database import Base, engine
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    orchestrator = OrchestratorService()
    orchestrator.start()
