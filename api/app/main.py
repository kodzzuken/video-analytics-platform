from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app import routes
from app.database import engine, Base
from app.config import settings
import logging
import threading
from app.inbox_consumer import start_inbox_consumer

# Create database tables
Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Video Analytics Platform - API",
    description="API Service for video scenario management and result retrieval",
    version="1.0.0"
)

# Include routes
app.include_router(routes.router)

@app.on_event("startup")
async def startup_event():
    """Start inbox consumer in background thread"""
    logger.info("API Service starting")
    # Start inbox consumer in separate thread
    inbox_thread = threading.Thread(target=start_inbox_consumer, daemon=True)
    inbox_thread.start()
    logger.info("Inbox consumer thread started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("API Service shutting down")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.exception_handler(Exception)
async def exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
