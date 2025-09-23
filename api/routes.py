from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging
from typing import List

from models import (
    HealthResponse, 
    SwapQuoteRequest, 
    SwapQuoteResponse, 
    TokenListResponse,
    VolumeSimulationRequest,
    VolumeSimulationResponse,
    ErrorResponse
)
from services.jupiter import JupiterService
from services.volume_simulator import VolumeSimulator

logger = logging.getLogger(__name__)
router = APIRouter()

# Global service instances (will be initialized in main.py)
jupiter_service: JupiterService = None
volume_simulator: VolumeSimulator = None

def get_jupiter_service() -> JupiterService:
    """Dependency to get Jupiter service instance"""
    if jupiter_service is None:
        raise HTTPException(status_code=500, detail="Jupiter service not initialized")
    return jupiter_service

def get_volume_simulator() -> VolumeSimulator:
    """Dependency to get volume simulator instance"""
    if volume_simulator is None:
        raise HTTPException(status_code=500, detail="Volume simulator not initialized")
    return volume_simulator

@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    """
    logger.info("Health check requested")
    return HealthResponse(message="VolumeBot backend ready")

@router.post("/get-swap-quote", response_model=SwapQuoteResponse)
async def get_swap_quote(
    request: SwapQuoteRequest,
    jupiter: JupiterService = Depends(get_jupiter_service)
):
    """
    Get swap quote and serialized transaction from Jupiter
    """
    try:
        logger.info(f"Swap quote requested: {request.inputMint[:8]}... -> {request.outputMint[:8]}...")
        
        # Validate mint addresses format (basic check)
        if not request.inputMint or not request.outputMint:
            raise HTTPException(
                status_code=400,
                detail="Input and output mint addresses are required"
            )
        
        if request.inputMint == request.outputMint:
            raise HTTPException(
                status_code=400,
                detail="Input and output mints cannot be the same"
            )
        
        # Get quote and transaction from Jupiter
        swap_response = await jupiter.get_swap_quote_and_transaction(request)
        
        logger.info(f"Quote successful: {swap_response.outputAmount} output, {swap_response.priceImpact:.4f}% impact")
        
        return swap_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_swap_quote: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get swap quote: {str(e)}"
        )

@router.get("/tokens", response_model=TokenListResponse)
async def get_tokens(
    jupiter: JupiterService = Depends(get_jupiter_service)
):
    """
    Get list of popular tokens for frontend autocomplete
    """
    try:
        logger.info("Token list requested")
        
        tokens = await jupiter.get_tokens()
        
        return TokenListResponse(
            tokens=tokens,
            count=len(tokens)
        )
        
    except Exception as e:
        logger.error(f"Error in get_tokens: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tokens: {str(e)}"
        )

@router.post("/simulate-volume", response_model=VolumeSimulationResponse)
async def simulate_volume(
    request: VolumeSimulationRequest,
    simulator: VolumeSimulator = Depends(get_volume_simulator)
):
    """
    Simulate volume trading strategy and return cost estimates
    """
    try:
        logger.info(f"Volume simulation requested for {request.tokenMint[:8]}...")
        
        # Validate token mint
        if not request.tokenMint:
            raise HTTPException(
                status_code=400,
                detail="Token mint address is required"
            )
        
        # Validate parameters
        if request.numTrades <= 0 or request.numTrades > 10000:
            raise HTTPException(
                status_code=400,
                detail="Number of trades must be between 1 and 10,000"
            )
        
        if request.durationMinutes <= 0 or request.durationMinutes > 1440:
            raise HTTPException(
                status_code=400,
                detail="Duration must be between 1 and 1,440 minutes (24 hours)"
            )
        
        if request.tradeSizeSol <= 0 or request.tradeSizeSol > 10:
            raise HTTPException(
                status_code=400,
                detail="Trade size must be between 0.001 and 10 SOL"
            )
        
        # Run simulation
        simulation_result = await simulator.simulate_volume_strategy(request)
        
        logger.info(f"Simulation complete: ${simulation_result.estimatedVolume:.2f} volume, {simulation_result.estimatedFees:.4f} SOL fees")
        
        return simulation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in simulate_volume: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to simulate volume: {str(e)}"
        )

@router.get("/health", response_model=dict)
async def detailed_health_check(
    jupiter: JupiterService = Depends(get_jupiter_service)
):
    """
    Detailed health check with service status
    """
    try:
        health_status = {
            "status": "healthy",
            "services": {
                "jupiter": "unknown",
                "database": "not_applicable"
            },
            "timestamp": None
        }
        
        # Test Jupiter API connection
        try:
            # Try to get tokens as a connectivity test
            tokens = await jupiter.get_tokens()
            health_status["services"]["jupiter"] = "healthy"
        except Exception as e:
            logger.warning(f"Jupiter service check failed: {str(e)}")
            health_status["services"]["jupiter"] = "unhealthy"
            health_status["status"] = "degraded"
        
        import datetime
        health_status["timestamp"] = datetime.datetime.utcnow().isoformat()
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

# Exception handlers will be added to the main FastAPI app in main.py
