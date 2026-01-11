from kafka import KafkaConsumer
from runner.config import settings
from runner.worker import WorkerManager
import json
import logging

logger = logging.getLogger(__name__)

class RunnerConsumer:
    """
    Kafka consumer that listens to to_deploy topic.
    Creates new worker process for each deployment.
    """
    
    def __init__(self):
        self.consumer = KafkaConsumer(
            'to_deploy',
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.consumer_group,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        self.worker_manager = WorkerManager(max_workers=settings.max_workers)
    
    def start(self):
        """Start consuming deploy orders"""
        logger.info("Runner consumer started")
        
        try:
            for message in self.consumer:
                try:
                    payload = message.value
                    worker_id = payload.get('worker_id')
                    scenario_uuid = payload.get('scenario_uuid')
                    camera_url = payload.get('camera_url')
                    
                    if not all([worker_id, scenario_uuid, camera_url]):
                        logger.warning(f"Invalid message format: {payload}")
                        continue
                    
                    # Start new worker process
                    success = self.worker_manager.start_worker(
                        worker_id,
                        scenario_uuid,
                        camera_url,
                        settings.video_fps
                    )
                    
                    if not success:
                        logger.error(f"Failed to start worker for {scenario_uuid}")
                    
                    # Log active workers count
                    active_count = self.worker_manager.get_active_workers_count()
                    logger.info(f"Active workers: {active_count}")
                
                except Exception as e:
                    logger.error(f"Error processing deploy message: {str(e)}")
                    continue
        
        except KeyboardInterrupt:
            logger.info("Runner consumer interrupted")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up runner resources")
        self.worker_manager.stop_all()
        self.consumer.close()
        logger.info("Runner cleanup complete")

def start_runner_consumer():
    """Entry point for runner service"""
    consumer = RunnerConsumer()
    consumer.start()
