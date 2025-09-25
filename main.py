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
from services.trade_executor import TradeExecutor
from services.trending_strategy import TrendingStrategy
# Rate limiting temporarily disabled
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded

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
_trade_executor: TradeExecutor = None
_trending_strategy: TrendingStrategy = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    """
    # Startup
    logger.info("Starting VolumeBot backend...")
    
    global _jupiter_service, _volume_simulator, _trade_executor, _trending_strategy
    
    try:
        # Initialize services
        _jupiter_service = JupiterService()
        _volume_simulator = VolumeSimulator(_jupiter_service)
        _trade_executor = TradeExecutor(_jupiter_service)
        _trending_strategy = TrendingStrategy(_jupiter_service)
        
        # Set global references for dependency injection
        import api.routes
        api.routes.jupiter_service = _jupiter_service
        api.routes.volume_simulator = _volume_simulator
        api.routes.trade_executor = _trade_executor
        api.routes.trending_strategy = _trending_strategy
        
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
        "https://localhost:3000",
        "http://172.27.208.1:3000",  # Network address from Next.js output
        # Production URLs - Add your frontend domains here
        "https://snowpiercer-backend-1.onrender.com",  # Backend URL (for API docs access)
        "https://snowpiercer-sepia.vercel.app",  # ACTUAL FRONTEND URL
        "https://volumebot-frontend.vercel.app",  # Common frontend deployment pattern
        "https://snowpiercer-frontend.vercel.app",  # Matching frontend pattern
        "https://snowpiercer-frontend.netlify.app",  # Alternative frontend pattern
        "*" if os.getenv("DEBUG", "False").lower() == "true" else None  # Allow all origins only in debug mode
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Rate limiting temporarily disabled
# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Root endpoint for basic info
@app.get("/")
async def root():
    """Root endpoint with basic API information"""
    return {
        "name": "VolumeBot Backend",
        "version": "1.0.0",
        "status": "running",
        "ready": True,
        "backend_url": "https://snowpiercer-backend-1.onrender.com",
        "docs_url": "/docs",
        "api_prefix": "/api",
        "description": "Professional Solana volume bot backend API using Jupiter aggregator"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": "2025-01-24T06:26:36Z",
        "backend_url": "https://snowpiercer-backend-1.onrender.com"
    }

# Include API routes
app.include_router(router, prefix="/api")

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