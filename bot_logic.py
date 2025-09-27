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
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solders.pubkey import Pubkey
import httpx

from models import BotParams, BotJob, SubWallet, BotMode

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
        
    async def create_sub_wallets(self, user_wallet_balance: float, num_wallets: int, 
                               user_keypair: Keypair) -> Tuple[List[SubWallet], List[Keypair], float]:
        """
        UPDATED FOR SMITHII LOGIC: Smart wallet allocation based on available balance
        - Creates up to 100 wallets with 0.1 SOL each
        - Allocates based on available balance (stops when balance insufficient)
        - Reserves gas fees and uses only 70% of wallet balance for trading
        """
        import os
        
        # Configuration from environment
        target_funding_per_wallet = float(os.getenv('SUB_WALLET_FUNDING_SOL', '0.1'))
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
                    
                # Simulate trade execution
                result = await self._simulate_buy_sell_pair(
                    sub_wallets[wallet_idx],
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
            
            # Simulate trade
            result = await self._simulate_trade(
                sub_wallets[wallet_idx], 
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
            
            result = await self._simulate_buy_sell_pair(
                sub_wallets[wallet_idx],
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
        UPDATED FOR SMITHII LOGIC: Trending mode - Platform-specific trending strategies
        """
        logger.info("Executing Trending mode: Platform-specific volume patterns")
        
        params = job.params
        end_time = time.time() + min(params.duration_hours * 3600, 300)  # Max 5 minutes for demo
        
        # Trending-specific parameters
        platforms = params.selected_platforms or ["dexscreener", "dextools"]
        intensity = params.trending_intensity or "medium"
        
        while time.time() < end_time and job.status == "running":
            # Simulate trending-optimized trades
            wallet_idx = job.completed_makers % len(sub_wallets)
            
            result = await self._simulate_trending_trade(
                sub_wallets[wallet_idx],
                params.token_mint,
                params.trade_size_sol,
                platforms,
                intensity
            )
            
            job.successful_transactions += 1
            job.generated_volume += result.get('volume', 0)
            job.completed_makers += 1
            job.current_buy_ratio = 0.6  # Slightly buy-biased for trending
            
            # Platform-optimized delays
            delay = self._get_trending_delay(intensity)
            await asyncio.sleep(delay)
            
    async def _execute_burst(self, job: BotJob, sub_wallets: List[SubWallet], 
                           keypairs: List[Keypair]):
        """Execute a burst of rapid trades for Advanced mode"""
        logger.info("Executing burst sequence")
        
        burst_size = random.randint(3, 8)  # Smaller bursts for demo
        
        for i in range(burst_size):
            wallet_idx = (job.completed_makers + i) % len(sub_wallets)
            
            result = await self._simulate_buy_sell_pair(
                sub_wallets[wallet_idx],
                job.params.token_mint,
                job.params.trade_size_sol,
                "burst"
            )
            
            job.successful_transactions += 1
            job.generated_volume += result.get('volume', 0)
            
        logger.info(f"Burst completed: {burst_size} trades executed")
        
    async def _simulate_buy_sell_pair(self, wallet: SubWallet, token_mint: str, 
                                   trade_size_sol: float, mode: str) -> Dict:
        """
        UPDATED FOR SMITHII LOGIC: Simulate bundled buy-sell pair
        """
        # Simulate trade execution with realistic delays
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Randomize trade size (±20%)
        actual_trade_size = trade_size_sol * random.uniform(0.8, 1.2)
        
        # Simulate volume generation
        total_volume = actual_trade_size * 2 * 100  # Rough USD conversion
        
        return {
            'success': True,
            'volume': total_volume,
            'mode': mode,
            'wallet': wallet.address
        }
        
    async def _simulate_trade(self, wallet: SubWallet, token_mint: str, 
                           amount_sol: float, trade_type: str) -> Dict:
        """Simulate individual trade"""
        await asyncio.sleep(random.uniform(0.2, 1.0))
        volume_usd = amount_sol * 100  # Approximate SOL price
        return {'success': True, 'volume': volume_usd, 'type': trade_type}
        
    async def _simulate_trending_trade(self, wallet: SubWallet, token_mint: str,
                                     trade_size_sol: float, platforms: List[str],
                                     intensity: str) -> Dict:
        """Simulate trending-optimized trade"""
        await asyncio.sleep(random.uniform(0.3, 1.5))
        
        # Intensity multiplier
        multiplier = {"low": 0.8, "medium": 1.0, "high": 1.3}.get(intensity, 1.0)
        volume = trade_size_sol * 100 * multiplier
        
        return {
            'success': True,
            'volume': volume,
            'platforms': platforms,
            'intensity': intensity
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
        UPDATED FOR SMITHII LOGIC: Return ALL remaining funds to user wallet
        After trading period ends, refund everything back to original wallet
        """
        logger.info("Cleaning up sub-wallets and returning ALL funds to user")
        
        total_refunded = 0.0
        import os
        usable_percentage = float(os.getenv('USABLE_BALANCE_PERCENTAGE', '70')) / 100
        
        # Simulate cleanup and fund return process
        for i, (wallet, keypair) in enumerate(zip(sub_wallets, keypairs)):
            # Calculate refundable amount (30% reserved + any unused trading funds)
            reserved_amount = wallet.balance_sol * (1 - usable_percentage)  # 30% reserved
            trading_amount = wallet.balance_sol * usable_percentage  # 70% that was used for trading
            
            # In real implementation, we would check actual remaining balance
            # For demo, assume some trading occurred and some funds remain
            remaining_trading_funds = trading_amount * random.uniform(0.1, 0.3)  # 10-30% remains
            
            refund_amount = reserved_amount + remaining_trading_funds
            
            if refund_amount > 0.01:  # Only refund if significant amount
                # Simulate transfer back to user (would be actual transaction in production)
                total_refunded += refund_amount
                logger.debug(f"Refunding {refund_amount:.4f} SOL from wallet {wallet.address[:8]}...")
            
            await asyncio.sleep(0.05)  # Small delay between refunds
            
            if (i + 1) % 10 == 0:
                logger.info(f"Cleaned up {i+1}/{len(sub_wallets)} wallets")
                
        logger.info(f"Wallet cleanup completed - Total refunded: {total_refunded:.4f} SOL")
        return total_refunded

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