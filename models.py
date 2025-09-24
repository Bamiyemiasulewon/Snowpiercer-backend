# UPDATED FOR SMITHII LOGIC: Enhanced models for advanced volume bot
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum
import time


class HealthResponse(BaseModel):
    message: str


class Token(BaseModel):
    mint: str = Field(..., description="Token mint address")
    symbol: str = Field(..., description="Token symbol")
    name: str = Field(..., description="Token name") 
    decimals: int = Field(..., description="Token decimals")
    logoURI: Optional[str] = Field(None, description="Token logo URL")


# UPDATED FOR SMITHII LOGIC: Enhanced bot mode enumeration
class BotMode(str, Enum):
    BOOST = "boost"
    BUMP = "bump" 
    ADVANCED = "advanced"
    TRENDING = "trending"

class SwapQuoteRequest(BaseModel):
    inputMint: str = Field(..., description="Input token mint address", min_length=32, max_length=44)
    outputMint: str = Field(..., description="Output token mint address", min_length=32, max_length=44)
    amount: int = Field(..., description="Amount in lamports/smallest unit", gt=0)
    slippageBps: int = Field(default=50, description="Slippage tolerance in basis points", ge=1, le=10000)
    
    # UPDATED FOR SMITHII LOGIC: Added bot parameters to swap quote
    mode: Optional[BotMode] = Field(None, description="Bot execution mode")
    num_makers: Optional[int] = Field(None, ge=100, le=10000, description="Number of maker wallets")
    duration_hours: Optional[float] = Field(None, ge=1, le=24, description="Bot duration in hours")
    trade_size_sol: Optional[float] = Field(None, ge=0.01, le=0.1, description="Trade size in SOL")
    target_price_usd: Optional[float] = Field(None, description="Target price for Bump mode")
    use_jito: Optional[bool] = Field(False, description="Use Jito MEV protection")

    @validator('inputMint', 'outputMint')
    def validate_mint_address(cls, v):
        if not v or len(v) < 32:
            raise ValueError('Invalid Solana mint address')
        return v

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v


class SwapQuoteResponse(BaseModel):
    swapTransaction: str = Field(..., description="Base64 encoded serialized transaction")
    inputAmount: int = Field(..., description="Input amount in smallest unit")
    outputAmount: int = Field(..., description="Estimated output amount")
    priceImpact: float = Field(..., description="Price impact percentage")
    marketInfos: List[dict] = Field(default=[], description="Market route information")
    
    # UPDATED FOR SMITHII LOGIC: Enhanced response for bot modes
    estimated_volume: Optional[float] = Field(None, description="Estimated volume for bot mode")
    estimated_makers: Optional[int] = Field(None, description="Estimated makers for bot mode")
    mode_analysis: Optional[Dict[str, Any]] = Field(None, description="Mode-specific analysis")


class VolumeSimulationRequest(BaseModel):
    tokenMint: str = Field(..., description="Target token mint address")
    numTrades: int = Field(..., description="Number of buy-sell pairs", ge=1, le=10000)
    durationMinutes: int = Field(..., description="Duration in minutes", ge=1, le=1440)
    tradeSizeSol: float = Field(..., description="Trade size in SOL", ge=0.001, le=10.0)
    slippageBps: int = Field(default=50, description="Slippage tolerance in bps", ge=1, le=10000)

    @validator('tokenMint')
    def validate_token_mint(cls, v):
        if not v or len(v) < 32:
            raise ValueError('Invalid token mint address')
        return v


class VolumeSimulationResponse(BaseModel):
    estimatedVolume: float = Field(..., description="Estimated volume in USD")
    estimatedFees: float = Field(..., description="Estimated total fees in SOL")
    estimatedTime: int = Field(..., description="Estimated completion time in minutes")
    averageDelay: float = Field(..., description="Average delay between trades in seconds")
    priceImpact: float = Field(..., description="Estimated price impact percentage")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    code: Optional[int] = Field(None, description="Error code")


class TokenListResponse(BaseModel):
    tokens: List[Token] = Field(..., description="List of supported tokens")
    count: int = Field(..., description="Number of tokens returned")


# Wallet Connection Models
class WalletConnectionRequest(BaseModel):
    publicKey: str = Field(..., description="Wallet public key")
    signature: Optional[str] = Field(None, description="Signature for wallet verification")

    @validator('publicKey')
    def validate_public_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError('Invalid Solana public key')
        return v


class WalletInfo(BaseModel):
    publicKey: str = Field(..., description="Wallet public key")
    balance: float = Field(..., description="SOL balance")
    connected: bool = Field(..., description="Connection status")
    lastUpdate: str = Field(..., description="Last update timestamp")


# Trade Execution Models
class TradeExecutionRequest(BaseModel):
    walletPublicKey: str = Field(..., description="Wallet public key for execution")
    tokenMint: str = Field(..., description="Target token mint address")
    numTrades: int = Field(..., description="Number of buy-sell pairs", ge=1, le=1000)
    durationMinutes: int = Field(..., description="Duration in minutes", ge=1, le=1440)
    tradeSizeSol: float = Field(..., description="Trade size in SOL", ge=0.001, le=10.0)
    slippageBps: int = Field(default=50, description="Slippage tolerance in bps", ge=1, le=10000)
    strategy: str = Field(default="balanced", description="Trading strategy: balanced, aggressive, organic")


class TradeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeExecutionResponse(BaseModel):
    executionId: str = Field(..., description="Unique execution ID")
    status: TradeStatus = Field(..., description="Current execution status")
    message: str = Field(..., description="Status message")
    estimatedCompletionTime: Optional[str] = Field(None, description="Estimated completion time")


# WebSocket Models
class WSMessageType(str, Enum):
    TRADE_UPDATE = "trade_update"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


class WSMessage(BaseModel):
    type: WSMessageType = Field(..., description="Message type")
    data: dict = Field(default={}, description="Message data")
    timestamp: str = Field(..., description="Message timestamp")
    executionId: Optional[str] = Field(None, description="Related execution ID")


class TradeUpdate(BaseModel):
    executionId: str = Field(..., description="Execution ID")
    tradeNumber: int = Field(..., description="Current trade number")
    totalTrades: int = Field(..., description="Total trades planned")
    status: TradeStatus = Field(..., description="Current status")
    volumeGenerated: float = Field(..., description="Volume generated so far (USD)")
    feesSpent: float = Field(..., description="Fees spent so far (SOL)")
    progress: float = Field(..., description="Progress percentage (0-100)")
    lastTradeResult: Optional[dict] = Field(None, description="Last trade result")
    estimatedTimeRemaining: Optional[int] = Field(None, description="Estimated minutes remaining")


# History and Monitoring Models
class TradeHistoryEntry(BaseModel):
    executionId: str = Field(..., description="Execution ID")
    timestamp: str = Field(..., description="Trade timestamp")
    tokenMint: str = Field(..., description="Token mint address")
    tradeType: str = Field(..., description="buy or sell")
    amount: float = Field(..., description="Trade amount in SOL")
    price: Optional[float] = Field(None, description="Execution price")
    fees: float = Field(..., description="Fees paid in SOL")
    status: str = Field(..., description="Trade status")
    txSignature: Optional[str] = Field(None, description="Transaction signature")


class ExecutionSummary(BaseModel):
    executionId: str = Field(..., description="Execution ID")
    walletPublicKey: str = Field(..., description="Wallet used")
    tokenMint: str = Field(..., description="Token traded")
    startTime: str = Field(..., description="Start timestamp")
    endTime: Optional[str] = Field(None, description="End timestamp")
    status: TradeStatus = Field(..., description="Final status")
    tradesCompleted: int = Field(..., description="Number of trades completed")
    totalVolume: float = Field(..., description="Total volume generated (USD)")
    totalFees: float = Field(..., description="Total fees paid (SOL)")
    efficiency: Optional[float] = Field(None, description="Execution efficiency score")


class TradeHistoryResponse(BaseModel):
    trades: List[TradeHistoryEntry] = Field(..., description="Trade history entries")
    total: int = Field(..., description="Total trades")
    page: int = Field(..., description="Current page")
    pageSize: int = Field(..., description="Page size")


class ExecutionListResponse(BaseModel):
    executions: List[ExecutionSummary] = Field(..., description="Execution summaries")
    total: int = Field(..., description="Total executions")
    active: int = Field(..., description="Currently active executions")


# Trending Models
class TrendingPlatform(str, Enum):
    DEXSCREENER = "dexscreener"
    DEXTOOLS = "dextools"
    JUPITER = "jupiter"
    BIRDEYE = "birdeye"
    SOLSCAN = "solscan"
    ALL = "all"


class TrendingIntensity(str, Enum):
    ORGANIC = "organic"        # Subtle, long-term trending
    AGGRESSIVE = "aggressive"  # Fast, high-volume trending
    STEALTH = "stealth"       # Undetectable, gradual trending
    VIRAL = "viral"           # Maximum visibility trending


class PlatformCostEstimate(BaseModel):
    platform: str = Field(..., description="Platform name")
    volumeRequired: float = Field(..., description="Minimum volume required in USD")
    transactionsRequired: int = Field(..., description="Minimum transactions required")
    estimatedCostSOL: float = Field(..., description="Estimated cost in SOL")
    successProbability: float = Field(..., description="Estimated success probability")
    timeToTrend: str = Field(..., description="Estimated time to trend")
    difficulty: str = Field(..., description="Difficulty level")


class MultiPlatformCostRequest(BaseModel):
    tokenMint: str = Field(..., description="Target token mint address")
    platforms: List[TrendingPlatform] = Field(..., description="Selected platforms for trending")
    intensity: TrendingIntensity = Field(default=TrendingIntensity.AGGRESSIVE, description="Trending intensity")
    currentVolume: float = Field(default=0, description="Current 24h volume")

    @validator('platforms')
    def validate_platforms(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one platform must be selected')
        if len(v) > 5:
            raise ValueError('Maximum 5 platforms can be selected')
        return v


class MultiPlatformCostResponse(BaseModel):
    tokenMint: str = Field(..., description="Token mint address")
    selectedPlatforms: List[str] = Field(..., description="Selected platform names")
    platformCosts: List[PlatformCostEstimate] = Field(..., description="Cost estimates per platform")
    totalCostSOL: float = Field(..., description="Total estimated cost in SOL")
    totalVolumeRequired: float = Field(..., description="Total volume required in USD")
    totalTransactions: int = Field(..., description="Total transactions required")
    estimatedDuration: str = Field(..., description="Estimated completion time")
    overallSuccessProbability: float = Field(..., description="Overall success probability")
    recommendations: str = Field(..., description="Strategy recommendations")


class TrendingExecutionRequest(BaseModel):
    walletPublicKey: str = Field(..., description="Wallet public key for execution")
    tokenMint: str = Field(..., description="Target token mint address")
    platforms: List[TrendingPlatform] = Field(..., description="Target platforms for trending")
    intensity: TrendingIntensity = Field(..., description="Trending intensity level")
    timeWindowHours: int = Field(..., description="Time window to achieve targets", ge=1, le=24)
    priceImpactTolerance: float = Field(default=2.0, description="Max price impact per trade %", ge=0.1, le=10.0)
    useMultipleWallets: bool = Field(default=False, description="Simulate multiple traders")
    includeFailedTxs: bool = Field(default=True, description="Include realistic failed transactions")

    @validator('tokenMint')
    def validate_token_mint(cls, v):
        if not v or len(v) < 32:
            raise ValueError('Invalid token mint address')
        return v


class TrendingRecommendation(BaseModel):
    platform: str = Field(..., description="Platform name")
    volumeNeeded24h: float = Field(..., description="Volume needed for trending")
    estimatedCostSol: float = Field(..., description="Estimated cost in SOL")
    minimumTransactions: int = Field(..., description="Minimum transactions required")
    recommendedIntensity: TrendingIntensity = Field(..., description="Recommended intensity")
    timeToTrend: str = Field(..., description="Estimated time to achieve trending")
    successProbability: float = Field(..., description="Success probability (0-1)")


class TrendingAnalysisResponse(BaseModel):
    tokenMint: str = Field(..., description="Token mint address")
    currentVolume24h: float = Field(..., description="Current 24h volume")
    recommendations: List[TrendingRecommendation] = Field(..., description="Trending recommendations")
    optimalTiming: Dict[str, Any] = Field(..., description="Optimal timing information")
    estimatedProbabilities: Dict[str, float] = Field(..., description="Success probabilities by platform")


class TrendingExecutionResponse(BaseModel):
    executionId: str = Field(..., description="Unique execution ID")
    status: TradeStatus = Field(..., description="Current execution status")
    message: str = Field(..., description="Status message")
    platform: TrendingPlatform = Field(..., description="Target platform")
    intensity: TrendingIntensity = Field(..., description="Trending intensity")
    estimatedCompletionTime: Optional[str] = Field(None, description="Estimated completion time")
    trendingProbability: float = Field(..., description="Estimated trending probability")


# UPDATED FOR SMITHII LOGIC: Advanced bot models
class BotParams(BaseModel):
    # Core parameters
    user_wallet: str = Field(..., description="User's main wallet address")
    token_mint: str = Field(..., description="Target token mint address")
    mode: BotMode = Field(..., description="Bot execution mode")
    
    # Trading parameters
    num_makers: int = Field(..., ge=100, le=10000, description="Number of maker wallets (100-10000)")
    duration_hours: float = Field(..., ge=1, le=24, description="Bot duration in hours (1-24)")
    trade_size_sol: float = Field(..., ge=0.01, le=0.1, description="Trade size in SOL (0.01-0.1)")
    slippage_pct: float = Field(..., ge=0.5, le=2.0, description="Slippage percentage (0.5-2.0)")
    
    # Mode-specific parameters
    target_price_usd: Optional[float] = Field(None, description="Target price for Bump mode")
    use_jito: bool = Field(False, description="Use Jito MEV protection for Advanced mode")
    custom_delay_min: Optional[int] = Field(5, ge=5, le=300, description="Min delay between trades (seconds)")
    custom_delay_max: Optional[int] = Field(60, ge=10, le=600, description="Max delay between trades (seconds)")
    
    # Trending-specific fields (compatibility with existing frontend)
    selected_platforms: Optional[List[str]] = Field(None, description="Selected platforms for trending")
    trending_intensity: Optional[str] = Field(None, description="Trending intensity level")
    
    @validator('target_price_usd')
    def validate_target_price(cls, v, values):
        if values.get('mode') == BotMode.BUMP and v is None:
            raise ValueError("target_price_usd is required for Bump mode")
        return v


class BotJob(BaseModel):
    job_id: str
    user_wallet: str
    status: str = "created"  # created, running, completed, failed, cancelled
    params: BotParams
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # Progress tracking
    completed_makers: int = 0
    generated_volume: float = 0.0
    current_buy_ratio: float = 0.0
    total_transactions: int = 0
    successful_transactions: int = 0
    failed_transactions: int = 0
    
    # Sub-wallet tracking
    generated_wallets: List[str] = []
    active_wallets: int = 0
    
    error_message: Optional[str] = None


class BotProgressResponse(BaseModel):
    job_id: str
    status: str
    completed_makers: int
    total_makers: int
    generated_volume: float
    current_buy_ratio: float
    progress_percentage: float
    estimated_completion: Optional[float] = None
    transactions: Dict[str, int]
    active_wallets: int
    error_message: Optional[str] = None


class SubWallet(BaseModel):
    address: str
    balance_sol: float = 0.0
    balance_token: float = 0.0
    transactions_completed: int = 0
    created_at: float = Field(default_factory=time.time)


class TrendingMetrics(BaseModel):
    token_mint: str
    volume_24h: float
    makers_24h: int
    price_change_24h: float
    
    # UPDATED FOR SMITHII LOGIC: Mode-specific trending estimates
    boost_potential: Optional[Dict[str, float]] = None
    bump_analysis: Optional[Dict[str, Any]] = None
    advanced_metrics: Optional[Dict[str, Any]] = None
