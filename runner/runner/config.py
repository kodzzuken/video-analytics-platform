import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Kafka
    kafka_bootstrap_servers: str = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS",
        "localhost:9092"
    )
    consumer_group: str = os.getenv("CONSUMER_GROUP", "runner-group")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Worker settings
    max_workers: int = int(os.getenv("MAX_WORKERS", "4"))
    video_fps: int = int(os.getenv("VIDEO_FPS", "2"))  # Frame extraction rate
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
