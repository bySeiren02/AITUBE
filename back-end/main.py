import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

from app.config import Config

# Configure logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AITUBE AI Content Detection",
    description="AI-generated video detection backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
try:
    from app.api.routes import router as api_router
    from app.models.ai_adapter import create_ai_model
    ai_model = create_ai_model(use_real=Config.USE_REAL_AI_MODEL)
    app.include_router(api_router, prefix="/api")
    logger.info("API routes loaded successfully")
except Exception as e:
    logger.error(f"Could not import API routes - using mock endpoints: {e}")
    ai_model = None
    
    @app.get("/api/health")
    async def health_check():
        return {"status": "healthy", "model_loaded": False}
    
    @app.get("/api/")
    async def api_root():
        return {
            "message": "UltraWork AI Content Detection API",
            "version": "1.0.0",
            "endpoints": {
                "/analyze": "POST - Analyze images for AI-generated content",
                "/health": "GET - Health check"
            }
        }

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("AITUBE AI Detection API starting up...")
    logger.info(f"Debug mode: {Config.DEBUG}")
    logger.info(f"AI Detection threshold: {Config.AI_DETECTION_THRESHOLD}")
    logger.info(f"Analysis timeout: {Config.ANALYSIS_TIMEOUT}s")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("AITUBE AI Detection API shutting down...")
    try:
        if ai_model:
            ai_model.cleanup()
    except:
        pass

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info" if not Config.DEBUG else "debug"
    )