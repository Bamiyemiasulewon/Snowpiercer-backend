import httpx
import base64
import logging
from typing import Dict, Any, Optional, List
from models import SwapQuoteRequest, SwapQuoteResponse, Token
import os

logger = logging.getLogger(__name__)

class JupiterService:
    def __init__(self):
        self.api_base_url = os.getenv("JUPITER_API_BASE_URL", "https://quote-api.jup.ag/v6")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def get_quote(self, request: SwapQuoteRequest) -> Dict[str, Any]:
        """
        Get swap quote from Jupiter API
        """
        try:
            url = f"{self.api_base_url}/quote"
            params = {
                "inputMint": request.inputMint,
                "outputMint": request.outputMint,
                "amount": str(request.amount),
                "slippageBps": str(request.slippageBps),
                "onlyDirectRoutes": "false",
                "asLegacyTransaction": "false"
            }
            
            logger.info(f"Getting quote for {request.inputMint} -> {request.outputMint}, amount: {request.amount}")
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            quote_data = response.json()
            logger.info(f"Quote received: {quote_data.get('outAmount', 'N/A')} output amount")
            
            return quote_data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Jupiter API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to get quote: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting quote: {str(e)}")
            raise Exception(f"Failed to get quote: {str(e)}")
    
    async def get_swap_transaction(self, quote: Dict[str, Any], user_public_key: Optional[str] = None) -> str:
        """
        Get serialized swap transaction from Jupiter API
        """
        try:
            url = f"{self.api_base_url}/swap"
            
            # Prepare swap request
            swap_request = {
                "quoteResponse": quote,
                "userPublicKey": user_public_key or "11111111111111111111111111111111",  # Dummy public key if not provided
                "wrapAndUnwrapSol": True,
                "useSharedAccounts": True,
                "feeAccount": None,
                "trackingAccount": None,
                "computeUnitPriceMicroLamports": 100000,  # Priority fee
                "asLegacyTransaction": False,
                "useTokenLedger": False,
            }
            
            logger.info("Getting swap transaction")
            
            response = await self.client.post(url, json=swap_request)
            response.raise_for_status()
            
            swap_data = response.json()
            
            if "swapTransaction" not in swap_data:
                raise Exception("No swap transaction in response")
            
            return swap_data["swapTransaction"]
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Jupiter swap API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to get swap transaction: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting swap transaction: {str(e)}")
            raise Exception(f"Failed to get swap transaction: {str(e)}")
    
    async def get_swap_quote_and_transaction(self, request: SwapQuoteRequest) -> SwapQuoteResponse:
        """
        Get both quote and transaction in one call
        """
        try:
            # Get quote first
            quote_data = await self.get_quote(request)
            
            # Get swap transaction
            swap_transaction = await self.get_swap_transaction(quote_data)
            
            # Extract relevant information
            input_amount = int(quote_data.get("inAmount", request.amount))
            output_amount = int(quote_data.get("outAmount", 0))
            price_impact = float(quote_data.get("priceImpactPct", 0))
            market_infos = quote_data.get("routePlan", [])
            
            return SwapQuoteResponse(
                swapTransaction=swap_transaction,
                inputAmount=input_amount,
                outputAmount=output_amount,
                priceImpact=price_impact,
                marketInfos=market_infos
            )
            
        except Exception as e:
            logger.error(f"Error in get_swap_quote_and_transaction: {str(e)}")
            raise
    
    async def get_tokens(self) -> List[Token]:
        """
        Get list of popular tokens from Jupiter API or return hardcoded list
        """
        try:
            # Try to fetch from Jupiter first
            url = f"{self.api_base_url}/tokens"
            
            response = await self.client.get(url)
            if response.status_code == 200:
                tokens_data = response.json()
                
                # Filter for popular tokens
                popular_tokens = []
                popular_mints = [
                    "So11111111111111111111111111111111111111112",  # SOL (Wrapped)
                    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
                    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
                    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",   # ETH (Wormhole)
                    "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",   # BTC (Wormhole)
                ]
                
                for token_data in tokens_data:
                    if token_data.get("address") in popular_mints:
                        popular_tokens.append(Token(
                            mint=token_data.get("address"),
                            symbol=token_data.get("symbol"),
                            name=token_data.get("name"),
                            decimals=token_data.get("decimals"),
                            logoURI=token_data.get("logoURI")
                        ))
                
                if popular_tokens:
                    return popular_tokens
            
        except Exception as e:
            logger.warning(f"Failed to fetch tokens from Jupiter API: {str(e)}")
        
        # Fallback to hardcoded popular tokens
        return [
            Token(
                mint="So11111111111111111111111111111111111111112",
                symbol="SOL",
                name="Wrapped Solana",
                decimals=9,
                logoURI="https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/So11111111111111111111111111111111111111112/logo.png"
            ),
            Token(
                mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                symbol="USDC",
                name="USD Coin",
                decimals=6,
                logoURI="https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/logo.png"
            ),
            Token(
                mint="Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
                symbol="USDT",
                name="Tether USD",
                decimals=6,
                logoURI="https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB/logo.png"
            ),
            Token(
                mint="mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
                symbol="mSOL",
                name="Marinade staked SOL",
                decimals=9,
                logoURI="https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So/logo.svg"
            ),
            Token(
                mint="7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
                symbol="ETH",
                name="Ethereum (Wormhole)",
                decimals=8,
                logoURI="https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs/logo.png"
            ),
            Token(
                mint="9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",
                symbol="BTC",
                name="Bitcoin (Wormhole)",
                decimals=8,
                logoURI="https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E/logo.png"
            )
        ]