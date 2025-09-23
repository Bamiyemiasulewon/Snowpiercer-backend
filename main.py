import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from api.routes import router
from services.jupiter import JupiterService
from services.volume_simulator import VolumeSimulator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('volumebot.log') if os.getenv('DEBUG', 'False').lower() == 'true' else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global service instances
_jupiter_service: JupiterService = None
_volume_simulator: VolumeSimulator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    """
    # Startup
    logger.info("Starting VolumeBot backend...")
    
    global _jupiter_service, _volume_simulator
    
    try:
        # Initialize services
        _jupiter_service = JupiterService()
        _volume_simulator = VolumeSimulator(_jupiter_service)
        
        # Set global references for dependency injection
        import api.routes
        api.routes.jupiter_service = _jupiter_service
        api.routes.volume_simulator = _volume_simulator
        
        logger.info("Services initialized successfully")
        
        # Test Jupiter API connectivity
        try:
            tokens = await _jupiter_service.get_tokens()
            logger.info(f"Jupiter API connectivity test passed - {len(tokens)} tokens available")
        except Exception as e:
            logger.warning(f"Jupiter API connectivity test failed: {str(e)}")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise
    
    logger.info("VolumeBot backend started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down VolumeBot backend...")
    
    try:
        if _jupiter_service:
            await _jupiter_service.close()
        logger.info("Services cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
    
    logger.info("VolumeBot backend shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="VolumeBot Backend",
    description="Professional Solana volume bot backend API using Jupiter aggregator",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred"
        }
    )

# Additional middleware for request logging
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"{request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )