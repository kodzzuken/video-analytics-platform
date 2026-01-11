import logging
import sys
from runner.config import settings
from runner.kafka_consumer import start_runner_consumer

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Starting Runner Service")
        logger.info(f"Max workers: {settings.max_workers}")
        logger.info(f"Video FPS target: {settings.video_fps}")
        start_runner_consumer()
    except Exception as e:
        logger.error(f"Runner failed: {str(e)}")
        sys.exit(1)
