import logging
from typing import Tuple
from models import VolumeSimulationRequest, VolumeSimulationResponse, SwapQuoteRequest
from services.jupiter import JupiterService

logger = logging.getLogger(__name__)

class VolumeSimulator:
    def __init__(self, jupiter_service: JupiterService):
        self.jupiter_service = jupiter_service
        
    async def simulate_volume_strategy(self, request: VolumeSimulationRequest) -> VolumeSimulationResponse:
        """
        Simulate volume trading strategy and return estimates
        """
        try:
            logger.info(f"Simulating volume for token {request.tokenMint}")
            
            # Constants
            SOL_MINT = "So11111111111111111111111111111111111111112"
            LAMPORTS_PER_SOL = 1_000_000_000
            
            # Convert SOL to lamports
            trade_amount_lamports = int(request.tradeSizeSol * LAMPORTS_PER_SOL)
            
            # Get sample quotes for cost estimation
            # SOL -> Token quote
            sol_to_token_request = SwapQuoteRequest(
                inputMint=SOL_MINT,
                outputMint=request.tokenMint,
                amount=trade_amount_lamports,
                slippageBps=request.slippageBps
            )
            
            try:
                sol_to_token_quote = await self.jupiter_service.get_quote(sol_to_token_request)
                token_output_amount = int(sol_to_token_quote.get("outAmount", 0))
                sol_to_token_impact = float(sol_to_token_quote.get("priceImpactPct", 0))
                
                # Token -> SOL quote (reverse)
                token_to_sol_request = SwapQuoteRequest(
                    inputMint=request.tokenMint,
                    outputMint=SOL_MINT,
                    amount=token_output_amount,
                    slippageBps=request.slippageBps
                )
                
                token_to_sol_quote = await self.jupiter_service.get_quote(token_to_sol_request)
                final_sol_amount = int(token_to_sol_quote.get("outAmount", 0))
                token_to_sol_impact = float(token_to_sol_quote.get("priceImpactPct", 0))
                
            except Exception as e:
                logger.warning(f"Failed to get live quotes, using estimates: {str(e)}")
                # Fallback to estimated values
                sol_to_token_impact = 0.1  # 0.1% estimated impact
                token_to_sol_impact = 0.1
                final_sol_amount = int(trade_amount_lamports * 0.995)  # Assume 0.5% total slippage
            
            # Calculate trade pair cost (SOL lost per round trip)
            trade_pair_cost_lamports = trade_amount_lamports - final_sol_amount
            trade_pair_cost_sol = trade_pair_cost_lamports / LAMPORTS_PER_SOL
            
            # Estimate fees (Jupiter typically charges 0.1-0.3% + gas)
            estimated_jupiter_fee_per_swap = trade_amount_lamports * 0.002  # 0.2% estimated
            estimated_gas_per_swap = 5000  # ~5k lamports gas per swap
            total_fee_per_pair_lamports = (estimated_jupiter_fee_per_swap * 2) + (estimated_gas_per_swap * 2)
            total_fee_per_pair_sol = total_fee_per_pair_lamports / LAMPORTS_PER_SOL
            
            # Calculate total estimates
            total_fees_sol = total_fee_per_pair_sol * request.numTrades
            total_volume_usd = request.tradeSizeSol * 2 * request.numTrades * 100  # Rough SOL price estimate
            
            # Calculate timing
            average_delay_seconds = (request.durationMinutes * 60) / request.numTrades
            estimated_time_minutes = request.durationMinutes
            
            # Calculate average price impact
            average_price_impact = (abs(sol_to_token_impact) + abs(token_to_sol_impact)) / 2
            
            return VolumeSimulationResponse(
                estimatedVolume=total_volume_usd,
                estimatedFees=total_fees_sol,
                estimatedTime=estimated_time_minutes,
                averageDelay=average_delay_seconds,
                priceImpact=average_price_impact
            )
            
        except Exception as e:
            logger.error(f"Error in volume simulation: {str(e)}")
            raise Exception(f"Volume simulation failed: {str(e)}")
    
    def calculate_optimal_timing(self, num_trades: int, duration_minutes: int, mode: str = "balanced") -> Tuple[float, float]:
        """
        Calculate optimal timing between trades
        Returns: (min_delay_seconds, max_delay_seconds)
        """
        base_delay = (duration_minutes * 60) / num_trades
        
        if mode == "aggressive":
            # Faster execution with less randomization
            return (base_delay * 0.7, base_delay * 1.1)
        elif mode == "organic":
            # More randomized, organic-looking timing
            return (base_delay * 0.5, base_delay * 1.8)
        else:  # balanced
            return (base_delay * 0.8, base_delay * 1.2)
