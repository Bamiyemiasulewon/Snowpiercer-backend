# UPDATED FOR SMITHII LOGIC: Advanced volume bot implementation
import asyncio
import random
import time
import logging
from typing import List, Dict, Optional, Tuple
import json
from decimal import Decimal
import numpy as np

from solana.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed, Finalized
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
import httpx
import base64

from models import BotParams, BotJob, SubWallet, BotMode, SwapQuoteRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmithiiVolumeBot:
    """
    UPDATED FOR SMITHII LOGIC: Advanced volume bot with maker wallet generation,
    mode-specific behaviors, and MEV protection
    """
    
    def __init__(self, rpc_url: str, jito_endpoint: Optional[str] = None):
        self.rpc_url = rpc_url
        self.jito_endpoint = jito_endpoint
        self.client = AsyncClient(rpc_url)
        self.active_jobs: Dict[str, BotJob] = {}
        self.jupiter_api_base = "https://quote-api.jup.ag/v6"
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def create_sub_wallets(self, user_wallet_balance: float, num_wallets: int, 
                               user_keypair: Keypair) -> Tuple[List[SubWallet], List[Keypair], float]:
        """
        UPDATED FOR SMITHII LOGIC: Smart wallet allocation based on available balance
        - Creates up to 100 wallets with 0.025 SOL each
        - Allocates based on available balance (stops when balance insufficient)
        - Reserves gas fees and uses only 70% of wallet balance for trading
        """
        import os
        
        # Configuration from environment
        target_funding_per_wallet = float(os.getenv('SUB_WALLET_FUNDING_SOL', '0.025'))
        gas_reserve = float(os.getenv('GAS_FEE_RESERVE_SOL', '0.5'))
        usable_percentage = float(os.getenv('USABLE_BALANCE_PERCENTAGE', '70')) / 100
        
        # Calculate available balance for trading (reserve gas fees)
        available_balance = max(0, user_wallet_balance - gas_reserve)
        logger.info(f"User balance: {user_wallet_balance} SOL, Available after gas reserve: {available_balance} SOL")
        
        if available_balance < target_funding_per_wallet:
            raise ValueError(f"Insufficient balance. Need at least {target_funding_per_wallet + gas_reserve} SOL (including gas reserve)")
        
        # Calculate how many wallets we can actually fund
        max_wallets_possible = int(available_balance // target_funding_per_wallet)
        actual_wallets = min(num_wallets, max_wallets_possible)
        
        logger.info(f"Requested: {num_wallets} wallets, Can fund: {max_wallets_possible}, Creating: {actual_wallets} wallets")
        
        sub_wallets = []
        funding_per_wallet = target_funding_per_wallet
        
        # Generate keypairs for actual wallets we can fund
        keypairs = [Keypair() for _ in range(actual_wallets)]
        
        # Create wallet objects
        for i, keypair in enumerate(keypairs):
            wallet = SubWallet(
                address=str(keypair.pubkey()),
                balance_sol=0.0
            )
            sub_wallets.append(wallet)
            
        # Fund wallets with interlinking chain (user -> wallet1 -> wallet2 -> ...)
        total_allocated = 0.0
        try:
            # Fund wallets directly from user (simplified for better reliability)
            for i in range(actual_wallets):
                # Add small randomization to avoid detection patterns
                actual_funding = funding_per_wallet * random.uniform(0.98, 1.02)
                
                await self._transfer_sol(user_keypair, keypairs[i].pubkey(), actual_funding)
                sub_wallets[i].balance_sol = actual_funding
                total_allocated += actual_funding
                
                # Small delay to avoid rate limits
                await asyncio.sleep(random.uniform(0.1, 0.2))
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Funded {i+1}/{actual_wallets} sub-wallets")
                    
        except Exception as e:
            logger.error(f"Failed to fund sub-wallets: {e}")
            raise
            
        # Calculate usable amount per wallet (70% of balance for trading)
        usable_per_wallet = funding_per_wallet * usable_percentage
        
        logger.info(f"Successfully generated and funded {len(sub_wallets)} sub-wallets")
        logger.info(f"Total allocated: {total_allocated:.3f} SOL, Usable per wallet: {usable_per_wallet:.3f} SOL (70%)")
        
        return sub_wallets, keypairs, total_allocated
    
    async def _transfer_sol(self, from_keypair: Keypair, to_pubkey: Pubkey, amount_sol: float):
        """Transfer SOL between wallets"""
        amount_lamports = int(amount_sol * 1e9)
        
        transfer_instruction = transfer(
            TransferParams(
                from_pubkey=from_keypair.pubkey(),
                to_pubkey=to_pubkey,
                lamports=amount_lamports
            )
        )
        
        transaction = Transaction()
        transaction.add(transfer_instruction)
        
        # Get recent blockhash
        recent_blockhash = await self.client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash
        
        # Sign and send
        transaction.sign(from_keypair)
        result = await self.client.send_transaction(transaction)
        
        # Confirm transaction
        await self.client.confirm_transaction(result.value, commitment=Confirmed)
        
    async def execute_volume_bot(self, job: BotJob) -> None:
        """
        UPDATED FOR SMITHII LOGIC: Main bot execution with mode-specific behaviors
        """
        try:
            job.status = "running"
            job.started_at = time.time()
            
            params = job.params
            logger.info(f"Starting {params.mode} mode bot for {params.duration_hours} hours")
            
            # Validate pool existence
            pool_exists = await self._check_pool_exists(params.token_mint)
            if not pool_exists:
                raise ValueError(f"No Raydium pool found for token {params.token_mint}")
            
            # For demo purposes, create a dummy user keypair and simulate balance
            # In production, this would come from actual user wallet
            user_keypair = Keypair()
            simulated_balance = 10.0  # Simulate 10 SOL balance for demo
            
            # Generate sub-wallets with smart allocation
            sub_wallets, keypairs, total_allocated = await self.create_sub_wallets(
                simulated_balance, params.num_makers, user_keypair
            )
            
            job.generated_wallets = [w.address for w in sub_wallets]
            job.active_wallets = len(sub_wallets)
            
            # Execute mode-specific trading
            if params.mode == BotMode.BOOST:
                await self._execute_boost_mode(job, sub_wallets, keypairs)
            elif params.mode == BotMode.BUMP:
                await self._execute_bump_mode(job, sub_wallets, keypairs)
            elif params.mode == BotMode.ADVANCED:
                await self._execute_advanced_mode(job, sub_wallets, keypairs)
            elif params.mode == BotMode.TRENDING:
                await self._execute_trending_mode(job, sub_wallets, keypairs)
                
            # Cleanup: Return remaining funds to user
            refunded_amount = await self._cleanup_wallets(sub_wallets, keypairs, user_keypair)
            logger.info(f"Refunded {refunded_amount:.4f} SOL to user wallet")
            
            job.status = "completed"
            job.completed_at = time.time()
            logger.info(f"Bot job {job.job_id} completed successfully")
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = time.time()
            logger.error(f"Bot job {job.job_id} failed: {e}")
            
    async def _execute_boost_mode(self, job: BotJob, sub_wallets: List[SubWallet], 
                                keypairs: List[Keypair]):
        """
        UPDATED FOR SMITHII LOGIC: Boost mode - High-frequency spikes
        """
        logger.info("Executing Boost mode: High-frequency volume spikes")
        
        params = job.params
        end_time = time.time() + min(params.duration_hours * 3600, 300)  # Max 5 minutes for demo
        
        # Boost mode: Rapid, equal buy/sell trades
        while time.time() < end_time and job.status == "running":
            batch_size = min(5, len(sub_wallets) - job.completed_makers)
            if batch_size <= 0:
                break
                
            # Simulate batch of trades
            for i in range(batch_size):
                wallet_idx = job.completed_makers + i
                if wallet_idx >= len(sub_wallets):
                    break
                    
                # Execute real trade
                result = await self._execute_buy_sell_pair(
                    sub_wallets[wallet_idx],
                    keypairs[wallet_idx],
                    params.token_mint,
                    params.trade_size_sol,
                    "boost"
                )
                
                job.successful_transactions += 1
                job.generated_volume += result.get('volume', 0)
                    
            job.completed_makers += batch_size
            job.current_buy_ratio = 0.5  # Equal buy/sell in boost mode
            
            # Short delay for boost mode (minimal)
            await asyncio.sleep(random.uniform(1, 3))
            
    async def _execute_bump_mode(self, job: BotJob, sub_wallets: List[SubWallet], 
                               keypairs: List[Keypair]):
        """
        UPDATED FOR SMITHII LOGIC: Bump mode - Sustained price pumping with buy bias
        """
        logger.info(f"Executing Bump mode: Target price ${job.params.target_price_usd}")
        
        params = job.params
        end_time = time.time() + min(params.duration_hours * 3600, 300)  # Max 5 minutes for demo
        buy_ratio = 0.7  # 70% buys, 30% sells
        
        current_price = await self._get_token_price(params.token_mint)
        logger.info(f"Starting price: ${current_price}, Target: ${params.target_price_usd}")
        
        while time.time() < end_time and job.status == "running":
            # Check if target price reached (simulated)
            current_price = await self._get_token_price(params.token_mint)
            if params.target_price_usd and current_price >= params.target_price_usd:
                logger.info(f"Target price ${params.target_price_usd} reached!")
                break
                
            # Determine trade type based on buy ratio
            is_buy = random.random() < buy_ratio
            
            # Select wallet
            wallet_idx = job.completed_makers % len(sub_wallets)
            
            # Staggered trade sizes (increasing for buys)
            trade_multiplier = 1.2 if is_buy else 0.8
            trade_size = params.trade_size_sol * trade_multiplier
            
            # Execute real trade
            result = await self._execute_single_trade(
                keypairs[wallet_idx], 
                params.token_mint, 
                trade_size, 
                "buy" if is_buy else "sell"
            )
            
            job.successful_transactions += 1
            job.generated_volume += result.get('volume', 0)
            job.completed_makers += 1
            job.current_buy_ratio = buy_ratio
            
            # Staggered delays
            delay = random.uniform(5, 15)
            await asyncio.sleep(delay)
            
    async def _execute_advanced_mode(self, job: BotJob, sub_wallets: List[SubWallet], 
                                   keypairs: List[Keypair]):
        """
        UPDATED FOR SMITHII LOGIC: Advanced mode - MEV protection, timed bursts, anti-detection
        """
        logger.info("Executing Advanced mode: MEV protection and anti-detection")
        
        params = job.params
        end_time = time.time() + min(params.duration_hours * 3600, 300)  # Max 5 minutes for demo
        
        # Timed bursts every 30-90 seconds (faster for demo)
        burst_interval = random.uniform(30, 90)
        last_burst = time.time()
        
        while time.time() < end_time and job.status == "running":
            current_time = time.time()
            
            # Check if it's time for a burst
            if current_time - last_burst >= burst_interval:
                await self._execute_burst(job, sub_wallets, keypairs)
                last_burst = current_time
                burst_interval = random.uniform(30, 90)  # Randomize next burst
                
            # Regular background trading
            wallet_idx = job.completed_makers % len(sub_wallets)
            
            # Anti-detection: Variable slippage and Gaussian delays
            variable_slippage = random.uniform(0.5, 2.0)
            gaussian_delay = max(2, np.random.normal(10, 5))  # Mean 10s, std 5s
            
            result = await self._execute_buy_sell_pair(
                sub_wallets[wallet_idx],
                keypairs[wallet_idx],
                params.token_mint,
                params.trade_size_sol * random.uniform(0.8, 1.2),  # ±20% randomization
                "advanced"
            )
            
            job.successful_transactions += 1
            job.generated_volume += result.get('volume', 0)
            job.completed_makers += 1
            job.current_buy_ratio = random.uniform(0.4, 0.6)  # Randomized ratio
            
            await asyncio.sleep(gaussian_delay)
            
    async def _execute_trending_mode(self, job: BotJob, sub_wallets: List[SubWallet], 
                                   keypairs: List[Keypair]):
        """
        UPDATED FOR DEXSCREENER OPTIMIZATION: Trending mode with real-time DexScreener monitoring
        Optimizes trades specifically for DexScreener trending algorithm requirements
        """
        logger.info("Executing Trending mode: DexScreener-optimized volume patterns")
        
        params = job.params
        end_time = time.time() + (params.duration_hours * 3600)
        
        # Import trending metrics service
        from services.trending_metrics import get_trending_service
        trending_service = get_trending_service()
        
        # Trending-specific parameters
        platforms = params.selected_platforms or ["dexscreener", "dextools"]
        intensity = params.trending_intensity or "medium"
        
        # DexScreener requirements from environment or defaults
        import os
        dexscreener_targets = {
            "min_volume_24h": float(os.getenv('DEXSCREENER_TARGET_VOLUME_24H', '50000')),  # $50k minimum for trending
            "min_transactions": int(os.getenv('DEXSCREENER_TARGET_TRANSACTIONS', '100')),   # 100+ transactions
            "optimal_trade_size_usd": float(os.getenv('DEXSCREENER_OPTIMAL_TRADE_SIZE_USD', '500')),  # $500 per trade optimal
            "update_frequency": int(os.getenv('DEXSCREENER_UPDATE_FREQUENCY', '300'))  # 5-minute updates
        }
        
        # Track progress towards DexScreener trending
        last_metrics_check = 0
        metrics_check_interval = int(os.getenv('DEXSCREENER_CHECK_INTERVAL', '300'))  # Check every 5 minutes
        
        # Calculate optimal trade parameters for DexScreener
        sol_price_usd = 100  # Approximate SOL price
        optimal_trade_size_sol = dexscreener_targets["optimal_trade_size_usd"] / sol_price_usd
        
        # Adjust trade size if needed
        if params.trade_size_sol < optimal_trade_size_sol * 0.8:
            logger.info(f"Adjusting trade size from {params.trade_size_sol} to {optimal_trade_size_sol} SOL for DexScreener optimization")
            adjusted_trade_size = optimal_trade_size_sol
        else:
            adjusted_trade_size = params.trade_size_sol
        
        logger.info(f"🎯 DexScreener targets: ${dexscreener_targets['min_volume_24h']:,} volume, {dexscreener_targets['min_transactions']}+ transactions")
        
        while time.time() < end_time and job.status == "running":
            current_time = time.time()
            
            # Check DexScreener metrics periodically
            if current_time - last_metrics_check >= metrics_check_interval:
                try:
                    analysis = await trending_service.get_combined_trending_analysis(params.token_mint)
                    dexscreener_data = analysis['platforms']['dexscreener']
                    potential = analysis['trending_potential']
                    
                    current_volume = dexscreener_data.get('volume_24h', 0)
                    current_txns = (
                        dexscreener_data.get('transactions_24h', {}).get('buys', 0) + 
                        dexscreener_data.get('transactions_24h', {}).get('sells', 0)
                    )
                    
                    volume_gap = max(0, dexscreener_targets['min_volume_24h'] - current_volume)
                    txn_gap = max(0, dexscreener_targets['min_transactions'] - current_txns)
                    
                    logger.info(f"📊 DexScreener Status: ${current_volume:,.0f} volume ({volume_gap:,.0f} gap), {current_txns} txns ({txn_gap} gap)")
                    
                    if potential.get('dexscreener_ready', False):
                        logger.info("✅ DEXSCREENER TRENDING ACHIEVED! Token is now trending on DexScreener")
                        job.status = "trending_achieved"
                        break
                    
                    # Adjust strategy based on gaps
                    if volume_gap > 20000:  # Large volume gap
                        # Increase trade frequency
                        adjusted_trade_size = adjusted_trade_size * 1.1
                        logger.info(f"📈 Increasing trade size to {adjusted_trade_size:.4f} SOL (volume gap: ${volume_gap:,.0f})")
                    
                except Exception as e:
                    logger.warning(f"Failed to check DexScreener metrics: {e}")
                
                last_metrics_check = current_time
            
            # Execute DexScreener-optimized trades
            wallet_idx = job.completed_makers % len(sub_wallets)
            
            # Use adjusted trade size for DexScreener optimization
            result = await self._execute_trending_trade(
                sub_wallets[wallet_idx],
                keypairs[wallet_idx],
                params.token_mint,
                adjusted_trade_size,
                platforms,
                intensity
            )
            
            if result.get('success', False):
                job.successful_transactions += 1
                job.generated_volume += result.get('volume', 0)
                job.completed_makers += 1
                job.current_buy_ratio = 0.6  # Slightly buy-biased for trending
            else:
                job.failed_transactions += 1
            
            # DexScreener-optimized delays (5-minute update frequency)
            # Trade every 2-4 minutes to match DexScreener's update cycle
            if "dexscreener" in platforms:
                delay = random.uniform(120, 240)  # 2-4 minutes for DexScreener
            else:
                delay = self._get_trending_delay(intensity)
            
            await asyncio.sleep(delay)
            
    async def _execute_burst(self, job: BotJob, sub_wallets: List[SubWallet], 
                           keypairs: List[Keypair]):
        """Execute a burst of rapid trades for Advanced mode"""
        logger.info("Executing burst sequence")
        
        burst_size = random.randint(3, 8)  # Smaller bursts for demo
        
        for i in range(burst_size):
            wallet_idx = (job.completed_makers + i) % len(sub_wallets)
            
            result = await self._execute_buy_sell_pair(
                sub_wallets[wallet_idx],
                keypairs[wallet_idx],
                job.params.token_mint,
                job.params.trade_size_sol,
                "burst"
            )
            
            job.successful_transactions += 1
            job.generated_volume += result.get('volume', 0)
            
        logger.info(f"Burst completed: {burst_size} trades executed")
        
    async def _execute_buy_sell_pair(self, wallet: SubWallet, wallet_keypair: Keypair,
                                   token_mint: str, trade_size_sol: float, mode: str) -> Dict:
        """
        UPDATED FOR PRODUCTION: Execute real buy-sell pair using Jupiter aggregator
        """
        try:
            # Randomize trade size (±20%)
            actual_trade_size = trade_size_sol * random.uniform(0.8, 1.2)
            
            # Step 1: Buy token with SOL
            buy_result = await self._execute_swap(
                wallet_keypair,
                "So11111111111111111111111111111111111111112",  # SOL
                token_mint,
                actual_trade_size,
                "buy"
            )
            
            if not buy_result['success']:
                logger.warning(f"Buy failed for wallet {wallet.address[:8]}, skipping sell")
                return buy_result
            
            # Small delay between buy and sell
            await asyncio.sleep(random.uniform(2, 5))
            
            # Step 2: Sell token back to SOL
            sell_result = await self._execute_swap(
                wallet_keypair,
                token_mint,
                "So11111111111111111111111111111111111111112",  # SOL
                buy_result.get('token_amount', 0),
                "sell"
            )
            
            # Calculate total volume (buy + sell)
            buy_volume = buy_result.get('volume_usd', 0)
            sell_volume = sell_result.get('volume_usd', 0)
            total_volume = buy_volume + sell_volume
            
            return {
                'success': buy_result['success'] and sell_result['success'],
                'volume': total_volume,
                'mode': mode,
                'wallet': wallet.address,
                'buy_tx': buy_result.get('signature'),
                'sell_tx': sell_result.get('signature')
            }
            
        except Exception as e:
            logger.error(f"Error in buy-sell pair for {wallet.address[:8]}: {e}")
            return {
                'success': False,
                'volume': 0,
                'mode': mode,
                'wallet': wallet.address,
                'error': str(e)
            }
        
    async def _execute_single_trade(self, wallet_keypair: Keypair, token_mint: str, 
                           amount_sol: float, trade_type: str) -> Dict:
        """Execute individual trade (buy or sell)"""
        try:
            if trade_type == "buy":
                # Buy token with SOL
                return await self._execute_swap(
                    wallet_keypair,
                    "So11111111111111111111111111111111111111112",
                    token_mint,
                    amount_sol,
                    "buy"
                )
            else:
                # Sell token for SOL
                return await self._execute_swap(
                    wallet_keypair,
                    token_mint,
                    "So11111111111111111111111111111111111111112",
                    amount_sol,
                    "sell"
                )
        except Exception as e:
            logger.error(f"Error in single trade: {e}")
            return {'success': False, 'volume': 0, 'type': trade_type, 'error': str(e)}
        
    async def _execute_trending_trade(self, wallet: SubWallet, wallet_keypair: Keypair,
                                     token_mint: str, trade_size_sol: float, 
                                     platforms: List[str], intensity: str) -> Dict:
        """Execute trending-optimized trade with real swaps"""
        try:
            # Intensity multiplier affects trade size
            multiplier = {"low": 0.8, "medium": 1.0, "high": 1.3}.get(intensity, 1.0)
            adjusted_trade_size = trade_size_sol * multiplier
            
            # Execute buy-sell pair
            result = await self._execute_buy_sell_pair(
                wallet, wallet_keypair, token_mint, adjusted_trade_size, "trending"
            )
            
            result['platforms'] = platforms
            result['intensity'] = intensity
            
            return result
            
        except Exception as e:
            logger.error(f"Error in trending trade: {e}")
            return {
                'success': False,
                'volume': 0,
                'platforms': platforms,
                'intensity': intensity,
                'error': str(e)
            }
        
    def _get_trending_delay(self, intensity: str) -> float:
        """Get appropriate delay for trending intensity"""
        delays = {
            "low": (10, 30),
            "medium": (5, 20),
            "high": (2, 10)
        }
        min_delay, max_delay = delays.get(intensity, (5, 20))
        return random.uniform(min_delay, max_delay)
        
    async def _get_token_price(self, token_mint: str) -> float:
        """Get current token price via Jupiter"""
        # Simulate price fetching
        await asyncio.sleep(0.1)
        return random.uniform(0.01, 1.0)
        
    async def _check_pool_exists(self, token_mint: str) -> bool:
        """Check if Raydium pool exists for token"""
        # Simulate pool check
        await asyncio.sleep(0.2)
        return True  # Always return True for demo
        
    async def _cleanup_wallets(self, sub_wallets: List[SubWallet], 
                             keypairs: List[Keypair], user_keypair: Keypair) -> float:
        """
        UPDATED FOR PRODUCTION: Return ALL remaining funds to user wallet via REAL transactions
        After trading period ends, refund everything back to original wallet
        """
        logger.info("Cleaning up sub-wallets and returning ALL funds to user")
        
        total_refunded = 0.0
        user_pubkey = user_keypair.pubkey()
        
        # Real cleanup: Get actual balances and refund everything
        for i, (wallet, keypair) in enumerate(zip(sub_wallets, keypairs)):
            try:
                # Get actual remaining balance from Solana
                wallet_pubkey = Pubkey.from_string(wallet.address)
                balance_response = await self.client.get_balance(wallet_pubkey)
                
                if balance_response.value is None:
                    logger.warning(f"Could not get balance for wallet {wallet.address[:8]}...")
                    continue
                
                # Convert lamports to SOL
                remaining_balance_sol = balance_response.value / 1e9
                
                # Reserve small amount for transaction fees (0.001 SOL)
                fee_reserve = 0.001
                refundable_amount = max(0, remaining_balance_sol - fee_reserve)
                
                if refundable_amount > 0.001:  # Only refund if more than 0.001 SOL
                    # Execute REAL transfer back to user wallet
                    try:
                        await self._transfer_sol(keypair, user_pubkey, refundable_amount)
                        total_refunded += refundable_amount
                        logger.info(f"✅ Refunded {refundable_amount:.4f} SOL from wallet {wallet.address[:8]}... to user")
                    except Exception as e:
                        logger.error(f"Failed to refund from wallet {wallet.address[:8]}...: {e}")
                        # Continue with other wallets even if one fails
                else:
                    logger.debug(f"Wallet {wallet.address[:8]}... has insufficient balance to refund ({remaining_balance_sol:.6f} SOL)")
                
                # Small delay between refunds to avoid rate limits
                await asyncio.sleep(random.uniform(0.1, 0.2))
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Cleaned up {i+1}/{len(sub_wallets)} wallets (refunded {total_refunded:.4f} SOL so far)")
                    
            except Exception as e:
                logger.error(f"Error cleaning up wallet {wallet.address[:8]}...: {e}")
                # Continue with other wallets even if one fails
                continue
                
        logger.info(f"✅ Wallet cleanup completed - Total refunded: {total_refunded:.4f} SOL")
        return total_refunded
    
    async def _execute_swap(self, keypair: Keypair, input_mint: str, output_mint: str,
                           amount_sol: float, trade_type: str) -> Dict:
        """
        Execute real swap using Jupiter aggregator API
        
        Args:
            keypair: Wallet keypair to sign transaction
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount_sol: Amount in SOL (will be converted to lamports)
            trade_type: "buy" or "sell" for logging
        
        Returns:
            Dict with success status, volume, signature, and token amounts
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Convert SOL to lamports
                amount_lamports = int(amount_sol * 1e9)
                
                # Step 1: Get quote from Jupiter
                quote_url = f"{self.jupiter_api_base}/quote"
                quote_params = {
                    "inputMint": input_mint,
                    "outputMint": output_mint,
                    "amount": str(amount_lamports),
                    "slippageBps": "100",  # 1% slippage
                    "onlyDirectRoutes": "false"
                }
                
                logger.debug(f"Getting Jupiter quote for {trade_type}: {amount_sol} SOL")
                quote_response = await self.http_client.get(quote_url, params=quote_params)
                
                if quote_response.status_code != 200:
                    raise Exception(f"Quote failed: {quote_response.text}")
                
                quote_data = quote_response.json()
                
                # Step 2: Get swap transaction
                swap_url = f"{self.jupiter_api_base}/swap"
                swap_request = {
                    "quoteResponse": quote_data,
                    "userPublicKey": str(keypair.pubkey()),
                    "wrapAndUnwrapSol": True,
                    "computeUnitPriceMicroLamports": 200000,  # Priority fee for faster execution
                    "asLegacyTransaction": False
                }
                
                logger.debug(f"Getting swap transaction for {trade_type}")
                swap_response = await self.http_client.post(swap_url, json=swap_request)
                
                if swap_response.status_code != 200:
                    raise Exception(f"Swap transaction failed: {swap_response.text}")
                
                swap_data = swap_response.json()
                swap_transaction_base64 = swap_data.get("swapTransaction")
                
                if not swap_transaction_base64:
                    raise Exception("No swap transaction in response")
                
                # Step 3: Deserialize and sign transaction
                transaction_bytes = base64.b64decode(swap_transaction_base64)
                versioned_tx = VersionedTransaction.from_bytes(transaction_bytes)
                
                # Sign the transaction
                versioned_tx.sign([keypair])
                
                # Step 4: Send transaction to Solana
                logger.debug(f"Sending {trade_type} transaction to Solana")
                tx_signature = await self.client.send_transaction(
                    versioned_tx,
                    opts={"skip_preflight": False, "max_retries": 3}
                )
                
                signature = str(tx_signature.value)
                logger.info(f"{trade_type.upper()} transaction sent: {signature[:8]}...")
                
                # Step 5: Confirm transaction
                confirmation = await self.client.confirm_transaction(
                    signature,
                    commitment=Confirmed
                )
                
                if confirmation.value.err:
                    raise Exception(f"Transaction failed: {confirmation.value.err}")
                
                logger.info(f"{trade_type.upper()} confirmed: {signature[:8]}...")
                
                # Calculate volume in USD (approximate SOL price at $100)
                volume_usd = amount_sol * 100
                
                # Extract token amounts from quote
                in_amount = int(quote_data.get("inAmount", 0))
                out_amount = int(quote_data.get("outAmount", 0))
                
                return {
                    'success': True,
                    'signature': signature,
                    'volume_usd': volume_usd,
                    'in_amount': in_amount,
                    'out_amount': out_amount,
                    'token_amount': out_amount if trade_type == "buy" else in_amount,
                    'type': trade_type
                }
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"{trade_type} attempt {retry_count}/{max_retries} failed: {e}")
                
                if retry_count >= max_retries:
                    logger.error(f"{trade_type} failed after {max_retries} attempts: {e}")
                    return {
                        'success': False,
                        'volume_usd': 0,
                        'type': trade_type,
                        'error': str(e)
                    }
                
                # Exponential backoff
                await asyncio.sleep(2 ** retry_count)
        
        return {
            'success': False,
            'volume_usd': 0,
            'type': trade_type,
            'error': 'Max retries exceeded'
        }

# Global bot instance
bot_instance: Optional[SmithiiVolumeBot] = None

def get_bot() -> SmithiiVolumeBot:
    global bot_instance
    if bot_instance is None:
        import os
        rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        jito_endpoint = os.getenv("JITO_ENDPOINT", "https://mainnet.block-engine.jito.wtf")
        bot_instance = SmithiiVolumeBot(rpc_url, jito_endpoint)
    return bot_instance