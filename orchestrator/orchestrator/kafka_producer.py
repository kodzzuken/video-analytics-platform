from kafka import KafkaProducer
from orchestrator.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class KafkaProducerService:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )
    
    def send_deploy_order(self, worker_id: str, scenario_uuid: str, camera_url: str):
        """Send deployment order to runner"""
        try:
            payload = {
                "worker_id": str(worker_id),
                "scenario_uuid": str(scenario_uuid),
                "camera_url": camera_url
            }
            self.producer.send('to_deploy', value=payload)
            self.producer.flush(timeout=10)
            logger.info(f"Sent deploy order for {scenario_uuid}")
        except Exception as e:
            logger.error(f"Failed to send deploy message: {str(e)}")
            raise
    
    def close(self):
        self.producer.close()

kafka_producer = None

def get_kafka_producer() -> KafkaProducerService:
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = KafkaProducerService()
    return kafka_producer
