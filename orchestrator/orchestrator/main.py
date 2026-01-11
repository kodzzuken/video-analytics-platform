import logging
import sys
from orchestrator.config import settings
from orchestrator.orchestrator_logic import start_orchestrator

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Starting Orchestrator Service")
        start_orchestrator()
    except Exception as e:
        logger.error(f"Orchestrator failed: {str(e)}")
        sys.exit(1)
