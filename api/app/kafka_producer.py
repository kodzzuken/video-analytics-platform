from kafka import KafkaProducer
from app.config import settings
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class KafkaProducerService:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )
    
    def send_init_scenario(self, scenario_uuid: str, camera_url: str):
        """Send initialization message to init_scenario topic"""
        try:
            payload = {
                "scenario_uuid": str(scenario_uuid),
                "camera_url": camera_url
            }
            self.producer.send('init_scenario', value=payload)
            self.producer.flush(timeout=10)
            logger.info(f"Sent init_scenario message for {scenario_uuid}")
        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {str(e)}")
            raise
    
    def close(self):
        """Close producer connection"""
        self.producer.close()

# Global producer instance
kafka_producer = None

def get_kafka_producer() -> KafkaProducerService:
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = KafkaProducerService()
    return kafka_producer
