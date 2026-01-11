from kafka import KafkaProducer
from runner.config import settings
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
    
    def send_result(self, scenario_uuid: str, frame_number: int, 
                   detections: list, timestamp: str):
        """Send inference results to results topic"""
        try:
            payload = {
                "scenario_uuid": scenario_uuid,
                "frame_number": frame_number,
                "detections": detections,
                "timestamp": timestamp
            }
            self.producer.send('results', value=payload)
            logger.debug(f"Sent result for frame {frame_number}")
        except Exception as e:
            logger.error(f"Failed to send result: {str(e)}")
            raise
    
    def flush(self, timeout=10):
        """Flush pending messages"""
        self.producer.flush(timeout=timeout)
    
    def close(self):
        self.producer.close()

kafka_producer = None

def get_kafka_producer() -> KafkaProducerService:
    global kafka_producer
    if kafka_producer is None:
        kafka_producer = KafkaProducerService()
    return kafka_producer
