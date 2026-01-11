import logging
import multiprocessing
from runner.video_processor import extract_frames
from runner.inference import get_model
from runner.kafka_producer import get_kafka_producer

logger = logging.getLogger(__name__)

def worker_process(worker_id: str, scenario_uuid: str, camera_url: str, fps_target: int = 2):
    """
    Worker process that:
    1. Connects to video stream
    2. Reads frames
    3. Performs inference
    4. Publishes results to Kafka
    
    This runs in a SEPARATE PROCESS (multiprocessing.Process),
    NOT as a coroutine (which would block).
    """
    try:
        logger.info(f"Worker {worker_id} starting for scenario {scenario_uuid}")
        
        # Initialize model and producer for this process
        model = get_model()
        producer = get_kafka_producer()
        
        # Process video stream
        frame_count = 0
        for frame, frame_number, timestamp in extract_frames(camera_url, fps_target):
            try:
                # Perform inference
                detections = model.predict(frame)
                
                # Send results to Kafka
                producer.send_result(
                    scenario_uuid,
                    frame_number,
                    detections,
                    timestamp
                )
                
                frame_count += 1
                
                if frame_count % 10 == 0:
                    logger.info(
                        f"Worker {worker_id}: Processed {frame_count} frames "
                        f"(detections: {len(detections)})"
                    )
            
            except Exception as e:
                logger.error(f"Error processing frame {frame_number}: {str(e)}")
                continue
        
        # Flush remaining messages
        producer.flush(timeout=10)
        logger.info(f"Worker {worker_id} finished. Total frames: {frame_count}")
    
    except Exception as e:
        logger.error(f"Worker {worker_id} failed: {str(e)}")
    
    finally:
        logger.info(f"Worker {worker_id} process ended")

class WorkerManager:
    """
    Manages multiple worker processes.
    Each scenario runs in its own process.
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.processes = {}  # scenario_uuid -> Process
        logger.info(f"WorkerManager initialized with max_workers={max_workers}")
    
    def start_worker(self, worker_id: str, scenario_uuid: str, camera_url: str, fps_target: int = 2):
        """
        Start new worker process for scenario.
        """
        if len(self.processes) >= self.max_workers:
            logger.warning(f"Max workers ({self.max_workers}) reached, cannot start new worker")
            return False
        
        try:
            # Create and start process
            process = multiprocessing.Process(
                target=worker_process,
                args=(worker_id, scenario_uuid, camera_url, fps_target),
                name=f"worker-{scenario_uuid}"
            )
            
            process.start()
            self.processes[scenario_uuid] = process
            
            logger.info(
                f"Started worker {worker_id} (PID: {process.pid}) "
                f"for scenario {scenario_uuid}"
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to start worker: {str(e)}")
            return False
    
    def stop_worker(self, scenario_uuid: str):
        """
        Stop worker process for scenario.
        """
        if scenario_uuid not in self.processes:
            logger.warning(f"No worker found for scenario {scenario_uuid}")
            return
        
        try:
            process = self.processes[scenario_uuid]
            process.terminate()
            process.join(timeout=5)  # Wait up to 5 seconds
            
            if process.is_alive():
                process.kill()  # Force kill if still alive
                process.join()
            
            del self.processes[scenario_uuid]
            logger.info(f"Stopped worker for scenario {scenario_uuid}")
        
        except Exception as e:
            logger.error(f"Error stopping worker: {str(e)}")
    
    def stop_all(self):
        """
        Stop all worker processes.
        """
        logger.info("Stopping all workers")
        for scenario_uuid in list(self.processes.keys()):
            self.stop_worker(scenario_uuid)
    
    def get_active_workers_count(self) -> int:
        """
        Get count of active worker processes.
        """
        # Clean up finished processes
        finished = [
            uuid for uuid, proc in self.processes.items()
            if not proc.is_alive()
        ]
        for uuid in finished:
            del self.processes[uuid]
        
        return len(self.processes)
