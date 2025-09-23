from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum


class HealthResponse(BaseModel):
    message: str


class Token(BaseModel):
    mint: str = Field(..., description="Token mint address")
    symbol: str = Field(..., description="Token symbol")
    name: str = Field(..., description="Token name") 
    decimals: int = Field(..., description="Token decimals")
    logoURI: Optional[str] = Field(None, description="Token logo URL")


class SwapQuoteRequest(BaseModel):
    inputMint: str = Field(..., description="Input token mint address", min_length=32, max_length=44)
    outputMint: str = Field(..., description="Output token mint address", min_length=32, max_length=44)
    amount: int = Field(..., description="Amount in lamports/smallest unit", gt=0)
    slippageBps: int = Field(default=50, description="Slippage tolerance in basis points", ge=1, le=10000)

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