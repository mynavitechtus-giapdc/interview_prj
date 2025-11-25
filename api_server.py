"""
FastAPI server for Interview System API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.api.routes import router as api_router
from src.api.webhook_routes import router as webhook_router
from config.database import db_manager
from src.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    logger.info("Starting Interview System API...")
    
    # Test database connection
    if db_manager.test_connection():
        logger.info("Database connection successful")
    else:
        logger.error("Database connection failed!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Interview System API...")


# Create FastAPI app
app = FastAPI(
    title="Interview System API",
    description="API for managing and retrieving interview data with AI-powered grading",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)
app.include_router(webhook_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Interview System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "webhook": "/webhook"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
