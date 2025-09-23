from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.responses import JSONResponse
# Rate limiting imports - temporarily disabled
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded
import logging
from typing import List, Optional
from datetime import datetime

from models import (
    HealthResponse, 
    SwapQuoteRequest, 
    SwapQuoteResponse, 
    TokenListResponse,
    VolumeSimulationRequest,
    VolumeSimulationResponse,
    ErrorResponse,
    WalletConnectionRequest,
    WalletInfo,
    TradeExecutionRequest,
    TradeExecutionResponse,
    TradeHistoryResponse,
    ExecutionListResponse,
    TrendingExecutionRequest,
    TrendingExecutionResponse,
    TrendingAnalysisResponse,
    TrendingRecommendation,
    TrendingPlatform,
    TrendingIntensity,
    MultiPlatformCostRequest,
    MultiPlatformCostResponse
)
from services.jupiter import JupiterService
from services.volume_simulator import VolumeSimulator
from services.trade_executor import TradeExecutor
from services.websocket_manager import websocket_manager
from services.trending_strategy import TrendingStrategy, TrendingConfig

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiting - temporarily disabled
# limiter = Limiter(key_func=get_remote_address)

# Global service instances (will be initialized in main.py)
jupiter_service: JupiterService = None
volume_simulator: VolumeSimulator = None
trade_executor: TradeExecutor = None
trending_strategy: TrendingStrategy = None

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


def get_trade_executor() -> TradeExecutor:
    """Dependency to get trade executor instance"""
    if trade_executor is None:
        raise HTTPException(status_code=500, detail="Trade executor not initialized")
    return trade_executor


def get_trending_strategy() -> TrendingStrategy:
    """Dependency to get trending strategy instance"""
    if trending_strategy is None:
        raise HTTPException(status_code=500, detail="Trending strategy not initialized")
    return trending_strategy

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

# =============================================================================
# WALLET CONNECTION ENDPOINTS
# =============================================================================

@router.post("/wallet/connect", response_model=WalletInfo)
async def connect_wallet(
    wallet_request: WalletConnectionRequest,
    request: Request,
    executor: TradeExecutor = Depends(get_trade_executor)
):
    """
    Connect and validate a wallet
    """
    try:
        logger.info(f"Wallet connection request from {wallet_request.publicKey[:8]}...")
        
        # Get wallet balance (simulated for now)
        balance = await executor._get_wallet_balance(wallet_request.publicKey)
        
        wallet_info = WalletInfo(
            publicKey=wallet_request.publicKey,
            balance=balance,
            connected=True,
            lastUpdate=datetime.utcnow().isoformat()
        )
        
        logger.info(f"Wallet connected successfully: {balance:.4f} SOL")
        return wallet_info
        
    except Exception as e:
        logger.error(f"Error connecting wallet: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect wallet: {str(e)}"
        )


@router.get("/wallet/{wallet_pubkey}/balance", response_model=dict)
async def get_wallet_balance(
    wallet_pubkey: str,
    executor: TradeExecutor = Depends(get_trade_executor)
):
    """
    Get wallet balance
    """
    try:
        balance = await executor._get_wallet_balance(wallet_pubkey)
        return {
            "publicKey": wallet_pubkey,
            "balance": balance,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting wallet balance: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get wallet balance: {str(e)}"
        )


# =============================================================================
# TRADE EXECUTION ENDPOINTS
# =============================================================================

@router.post("/execute/start", response_model=TradeExecutionResponse)
async def start_execution(
    request: TradeExecutionRequest,
    executor: TradeExecutor = Depends(get_trade_executor)
):
    """
    Start a new volume trading execution
    """
    try:
        logger.info(f"Starting execution for wallet {request.walletPublicKey[:8]}...")
        
        response = await executor.start_execution(request)
        logger.info(f"Execution started: {response.executionId}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error starting execution: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start execution: {str(e)}"
        )


@router.post("/execute/{execution_id}/stop", response_model=dict)
async def stop_execution(
    execution_id: str,
    executor: TradeExecutor = Depends(get_trade_executor)
):
    """
    Stop an active execution
    """
    try:
        success = await executor.stop_execution(execution_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Execution not found or already completed"
            )
        
        return {
            "success": True,
            "message": "Execution stopped successfully",
            "executionId": execution_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping execution: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop execution: {str(e)}"
        )


@router.get("/execute/{execution_id}/status", response_model=dict)
async def get_execution_status(
    execution_id: str,
    executor: TradeExecutor = Depends(get_trade_executor)
):
    """
    Get status of a specific execution
    """
    try:
        status = await executor.get_execution_status(execution_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail="Execution not found"
            )
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution status: {str(e)}"
        )


@router.get("/execute/active", response_model=dict)
async def get_active_executions(
    executor: TradeExecutor = Depends(get_trade_executor)
):
    """
    Get all active executions
    """
    try:
        active_executions = executor.get_active_executions()
        return {
            "executions": active_executions,
            "count": len(active_executions)
        }
    except Exception as e:
        logger.error(f"Error getting active executions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active executions: {str(e)}"
        )


# =============================================================================
# MONITORING AND HISTORY ENDPOINTS
# =============================================================================

@router.get("/history/trades", response_model=TradeHistoryResponse)
async def get_trade_history(
    executor: TradeExecutor = Depends(get_trade_executor),
    execution_id: Optional[str] = Query(None, description="Filter by execution ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size")
):
    """
    Get trade history with pagination
    """
    try:
        trades = executor.get_trade_history(execution_id, page, page_size)
        total_trades = len(executor.trade_history)
        
        if execution_id:
            total_trades = len([t for t in executor.trade_history if t.executionId == execution_id])
        
        return TradeHistoryResponse(
            trades=trades,
            total=total_trades,
            page=page,
            pageSize=page_size
        )
        
    except Exception as e:
        logger.error(f"Error getting trade history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trade history: {str(e)}"
        )


@router.get("/history/executions", response_model=ExecutionListResponse)
async def get_execution_history(
    executor: TradeExecutor = Depends(get_trade_executor)
):
    """
    Get execution history and summaries
    """
    try:
        summaries = executor.get_execution_summaries()
        active_count = len(executor.get_active_executions())
        
        return ExecutionListResponse(
            executions=summaries,
            total=len(summaries),
            active=active_count
        )
        
    except Exception as e:
        logger.error(f"Error getting execution history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution history: {str(e)}"
        )


@router.get("/stats", response_model=dict)
async def get_system_stats(
    executor: TradeExecutor = Depends(get_trade_executor)
):
    """
    Get system statistics
    """
    try:
        active_executions = executor.get_active_executions()
        websocket_stats = websocket_manager.get_connection_stats()
        
        return {
            "executions": {
                "active": len(active_executions),
                "total_completed": len(executor.execution_summaries)
            },
            "trades": {
                "total": len(executor.trade_history)
            },
            "websockets": websocket_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system stats: {str(e)}"
        )


# =============================================================================
# WEBSOCKET ENDPOINTS
# =============================================================================

@router.websocket("/ws")
async def websocket_global_endpoint(websocket: WebSocket):
    """
    Global WebSocket endpoint for general updates
    """
    try:
        await websocket_manager.connect(websocket)
        await websocket_manager.handle_websocket_messages(websocket)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        websocket_manager.disconnect(websocket)


@router.websocket("/ws/{execution_id}")
async def websocket_execution_endpoint(websocket: WebSocket, execution_id: str):
    """
    WebSocket endpoint for specific execution updates
    """
    try:
        await websocket_manager.connect(websocket, execution_id)
        await websocket_manager.handle_websocket_messages(websocket, execution_id)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, execution_id)
    except Exception as e:
        logger.error(f"WebSocket error for execution {execution_id}: {str(e)}")
        websocket_manager.disconnect(websocket, execution_id)


# =============================================================================
# TRENDING ENDPOINTS
# =============================================================================

@router.post("/trending/analyze", response_model=TrendingAnalysisResponse)
async def analyze_trending_potential(
    token_mint: str,
    current_volume: float = 0,
    trending_service: TrendingStrategy = Depends(get_trending_strategy)
):
    """
    Analyze trending potential and get recommendations
    """
    try:
        logger.info(f"Analyzing trending potential for token {token_mint[:8]}...")
        
        # Get trending recommendations
        recommendations = trending_service.get_trending_recommendations(token_mint, current_volume)
        
        # Convert to TrendingRecommendation objects
        recommendation_objects = [
            TrendingRecommendation(
                platform=rec["platform"],
                volumeNeeded24h=rec["volume_needed_24h"],
                estimatedCostSol=rec["estimated_cost_sol"],
                minimumTransactions=rec["minimum_transactions"],
                recommendedIntensity=rec["recommended_intensity"],
                timeToTrend=rec["time_to_trend"],
                successProbability=rec["success_probability"]
            ) for rec in recommendations
        ]
        
        # Get optimal timing for DEXScreener (most restrictive)
        sample_config = TrendingConfig(
            platform=TrendingPlatform.DEXSCREENER,
            intensity=TrendingIntensity.AGGRESSIVE,
            target_volume_24h=50000,
            target_transactions=200,
            price_impact_tolerance=2.0,
            time_window_hours=6,
            use_multiple_wallets=False,
            include_failed_txs=True
        )
        
        params = trending_service.calculate_trending_parameters(sample_config)
        optimal_timing = params["timing_strategy"]
        
        # Estimate probabilities for all platforms
        probabilities = {}
        for rec in recommendations:
            config = TrendingConfig(
                platform=getattr(TrendingPlatform, rec["platform"].upper()),
                intensity=rec["recommended_intensity"],
                target_volume_24h=rec["volume_needed_24h"] + current_volume,
                target_transactions=rec["minimum_transactions"],
                price_impact_tolerance=2.0,
                time_window_hours=6,
                use_multiple_wallets=False,
                include_failed_txs=True
            )
            platform_probs = trending_service.estimate_trending_probability(config, {})
            probabilities.update(platform_probs)
        
        return TrendingAnalysisResponse(
            tokenMint=token_mint,
            currentVolume24h=current_volume,
            recommendations=recommendation_objects,
            optimalTiming=optimal_timing,
            estimatedProbabilities=probabilities
        )
        
    except Exception as e:
        logger.error(f"Error analyzing trending potential: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze trending potential: {str(e)}"
        )


@router.post("/trending/execute", response_model=TrendingExecutionResponse)
async def execute_trending_strategy(
    request: TrendingExecutionRequest,
    trending_service: TrendingStrategy = Depends(get_trending_strategy),
    trade_executor: TradeExecutor = Depends(get_trade_executor)
):
    """
    Execute trending-optimized volume strategy
    """
    try:
        logger.info(f"Starting trending execution for {request.platform.value} platform")
        
        # Create trending configuration
        trending_config = TrendingConfig(
            platform=request.platform,
            intensity=request.intensity,
            target_volume_24h=request.targetVolume24h,
            target_transactions=request.targetTransactions,
            price_impact_tolerance=request.priceImpactTolerance,
            time_window_hours=request.timeWindowHours,
            use_multiple_wallets=request.useMultipleWallets,
            include_failed_txs=request.includeFailedTxs
        )
        
        # Calculate trending probability
        probabilities = trending_service.estimate_trending_probability(trending_config, {})
        trending_probability = probabilities.get(request.platform.value, 0.5)
        
        # Generate optimized trading sequence
        trades = await trending_service.generate_trending_trades(
            request.tokenMint,
            trending_config,
            request.walletPublicKey
        )
        
        # Convert to standard trade execution request for executor
        # This is a simplified conversion - in production, you'd want to 
        # integrate the trending trades directly into the executor
        standard_request = TradeExecutionRequest(
            walletPublicKey=request.walletPublicKey,
            tokenMint=request.tokenMint,
            numTrades=len(trades) // 2,  # Divide by 2 since we have buy+sell pairs
            durationMinutes=request.timeWindowHours * 60,
            tradeSizeSol=request.targetVolume24h / (len(trades) * 100),  # Rough conversion
            slippageBps=int(request.priceImpactTolerance * 100),
            strategy=request.intensity.value
        )
        
        # Start execution using the trade executor
        execution_response = await trade_executor.start_execution(standard_request)
        
        # Create trending-specific response
        trending_response = TrendingExecutionResponse(
            executionId=execution_response.executionId,
            status=execution_response.status,
            message=f"Trending execution started for {request.platform.value} with {request.intensity.value} intensity",
            platform=request.platform,
            intensity=request.intensity,
            estimatedCompletionTime=execution_response.estimatedCompletionTime,
            trendingProbability=trending_probability
        )
        
        logger.info(f"Trending execution {execution_response.executionId} started with {trending_probability:.1%} success probability")
        
        return trending_response
        
    except Exception as e:
        logger.error(f"Error executing trending strategy: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute trending strategy: {str(e)}"
        )


@router.get("/trending/platforms", response_model=dict)
async def get_trending_platforms():
    """
    Get available trending platforms and their requirements
    """
    return {
        "platforms": [
            {
                "id": "dexscreener",
                "name": "DEXScreener",
                "description": "Most popular DEX analytics platform",
                "min_volume_24h": 50000,
                "min_transactions": 100,
                "difficulty": "high",
                "update_frequency": "5 minutes"
            },
            {
                "id": "dextools",
                "name": "DEXTools",
                "description": "Professional trading analytics",
                "min_volume_24h": 25000,
                "min_transactions": 75,
                "difficulty": "medium",
                "update_frequency": "3 minutes"
            },
            {
                "id": "jupiter",
                "name": "Jupiter Terminal",
                "description": "Leading Solana DEX aggregator",
                "min_volume_24h": 15000,
                "min_transactions": 50,
                "difficulty": "low",
                "update_frequency": "2 minutes"
            },
            {
                "id": "birdeye",
                "name": "Birdeye",
                "description": "Comprehensive DeFi analytics",
                "min_volume_24h": 35000,
                "min_transactions": 80,
                "difficulty": "medium",
                "update_frequency": "4 minutes"
            },
            {
                "id": "solscan",
                "name": "Solscan",
                "description": "Solana blockchain explorer",
                "min_volume_24h": 10000,
                "min_transactions": 30,
                "difficulty": "low",
                "update_frequency": "1 minute"
            }
        ],
        "intensities": [
            {
                "id": "organic",
                "name": "Organic",
                "description": "Natural, long-term trending approach",
                "speed": "slow",
                "detection_risk": "very_low"
            },
            {
                "id": "aggressive",
                "name": "Aggressive",
                "description": "Fast, high-impact trending",
                "speed": "fast",
                "detection_risk": "low"
            },
            {
                "id": "stealth",
                "name": "Stealth",
                "description": "Undetectable, gradual approach",
                "speed": "very_slow",
                "detection_risk": "minimal"
            },
            {
                "id": "viral",
                "name": "Viral",
                "description": "Maximum visibility and impact",
                "speed": "very_fast",
                "detection_risk": "medium"
            }
        ]
    }

@router.get("/trending/strategies")
async def get_trending_strategies(
    trending_service: TrendingStrategy = Depends(get_trending_strategy)
):
    """Get available trending strategies"""
    return trending_service.get_all_strategies()

@router.post("/trending/multi-platform-costs", response_model=MultiPlatformCostResponse)
async def calculate_multi_platform_costs(
    request: MultiPlatformCostRequest,
    trending_service: TrendingStrategy = Depends(get_trending_strategy)
):
    """Calculate costs and requirements for multiple platforms"""
    try:
        logger.info(f"Multi-platform cost calculation requested for {len(request.platforms)} platforms")
        
        # Get current volume for the token (mock data for now)
        current_volume = 5000  # This would come from actual token data
        
        costs = trending_service.calculate_multi_platform_costs(
            platforms=request.platforms,
            intensity=request.intensity,
            current_volume=current_volume
        )
        
        return MultiPlatformCostResponse(**costs)
        
    except Exception as e:
        logger.error(f"Error calculating multi-platform costs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate costs: {str(e)}")


# Exception handlers will be added to the main FastAPI app in main.py
