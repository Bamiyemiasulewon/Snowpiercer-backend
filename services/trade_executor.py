import asyncio
import uuid
import logging
import time
import random
import base64
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from models import (
    TradeExecutionRequest, TradeExecutionResponse, TradeStatus, TradeUpdate,
    SwapQuoteRequest, TradeHistoryEntry, ExecutionSummary
)
from services.jupiter import JupiterService
from services.websocket_manager import websocket_manager
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self, jupiter_service: JupiterService):
        self.jupiter_service = jupiter_service
        # In-memory storage for active executions
        self.active_executions: Dict[str, Dict] = {}
        # Trade history storage (in production, this would be a database)
        self.trade_history: List[TradeHistoryEntry] = []
        self.execution_summaries: List[ExecutionSummary] = []
        # Solana RPC client for real transaction execution
        rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.solana_client = AsyncClient(rpc_url)
        # Store wallet keypairs for executions (in production, use secure key management)
        self.wallet_keypairs: Dict[str, Keypair] = {}
        
    async def start_execution(self, request: TradeExecutionRequest) -> TradeExecutionResponse:
        """Start a new volume trading execution"""
        try:
            execution_id = str(uuid.uuid4())
            
            # Validate wallet and get balance
            wallet_balance = await self._get_wallet_balance(request.walletPublicKey)
            required_balance = request.tradeSizeSol * 2.1  # 2x trade size + 10% buffer for fees
            
            if wallet_balance < required_balance:
                return TradeExecutionResponse(
                    executionId=execution_id,
                    status=TradeStatus.FAILED,
                    message=f"Insufficient balance. Required: {required_balance:.4f} SOL, Available: {wallet_balance:.4f} SOL"
                )
            
            # Create execution record
            execution_data = {
                "id": execution_id,
                "request": request,
                "status": TradeStatus.PENDING,
                "start_time": datetime.utcnow(),
                "trades_completed": 0,
                "volume_generated": 0.0,
                "fees_spent": 0.0,
                "task": None,
                "last_update": datetime.utcnow()
            }
            
            self.active_executions[execution_id] = execution_data
            
            # Start the execution task
            task = asyncio.create_task(self._execute_volume_strategy(execution_id))
            execution_data["task"] = task
            
            logger.info(f"Started volume execution {execution_id} for wallet {request.walletPublicKey}")
            
            # Calculate estimated completion time
            estimated_completion = datetime.utcnow() + timedelta(minutes=request.durationMinutes)
            
            return TradeExecutionResponse(
                executionId=execution_id,
                status=TradeStatus.PENDING,
                message="Volume trading execution started",
                estimatedCompletionTime=estimated_completion.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error starting execution: {str(e)}")
            raise Exception(f"Failed to start execution: {str(e)}")
    
    async def stop_execution(self, execution_id: str) -> bool:
        """Stop an active execution"""
        if execution_id not in self.active_executions:
            return False
        
        execution_data = self.active_executions[execution_id]
        
        if execution_data["task"]:
            execution_data["task"].cancel()
        
        execution_data["status"] = TradeStatus.CANCELLED
        execution_data["end_time"] = datetime.utcnow()
        
        await websocket_manager.send_status_update(
            execution_id, 
            "cancelled",
            {"message": "Execution cancelled by user"}
        )
        
        logger.info(f"Stopped execution {execution_id}")
        return True
    
    async def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """Get current status of an execution"""
        if execution_id not in self.active_executions:
            return None
        
        execution_data = self.active_executions[execution_id]
        request = execution_data["request"]
        
        progress = (execution_data["trades_completed"] / request.numTrades) * 100
        
        return {
            "executionId": execution_id,
            "status": execution_data["status"],
            "progress": progress,
            "tradesCompleted": execution_data["trades_completed"],
            "totalTrades": request.numTrades,
            "volumeGenerated": execution_data["volume_generated"],
            "feesSpent": execution_data["fees_spent"],
            "startTime": execution_data["start_time"].isoformat(),
            "lastUpdate": execution_data["last_update"].isoformat()
        }
    
    async def _execute_volume_strategy(self, execution_id: str):
        """Execute the volume trading strategy"""
        execution_data = self.active_executions[execution_id]
        request = execution_data["request"]
        
        try:
            execution_data["status"] = TradeStatus.RUNNING
            await websocket_manager.send_status_update(
                execution_id, 
                "running",
                {"message": "Volume trading execution started"}
            )
            
            SOL_MINT = "So11111111111111111111111111111111111111112"
            LAMPORTS_PER_SOL = 1_000_000_000
            
            # Calculate timing
            total_duration_seconds = request.durationMinutes * 60
            base_delay = total_duration_seconds / request.numTrades
            
            # Execute trade pairs
            for trade_num in range(1, request.numTrades + 1):
                if execution_data["status"] == TradeStatus.CANCELLED:
                    break
                
                try:
                    # Calculate trade delay based on strategy
                    delay = self._calculate_trade_delay(base_delay, request.strategy)
                    
                    # Execute buy trade (SOL -> Token)
                    # Note: For real execution, wallet_keypair must be provided
                    # In production, this should come from secure key management or frontend signing
                    wallet_keypair = self.wallet_keypairs.get(request.walletPublicKey)
                    
                    buy_result = await self._execute_single_trade(
                        execution_id=execution_id,
                        trade_number=trade_num,
                        trade_type="buy",
                        input_mint=SOL_MINT,
                        output_mint=request.tokenMint,
                        amount_sol=request.tradeSizeSol,
                        slippage_bps=request.slippageBps,
                        wallet_pubkey=request.walletPublicKey,
                        wallet_keypair=wallet_keypair
                    )
                    
                    if not buy_result["success"]:
                        logger.error(f"Buy trade failed for execution {execution_id}: {buy_result['error']}")
                        continue
                    
                    # Small delay between buy and sell
                    await asyncio.sleep(random.uniform(2, 5))
                    
                    # Execute sell trade (Token -> SOL)
                    # Use the output amount from buy trade as input for sell
                    sell_amount_tokens = buy_result.get("output_amount", 0)
                    
                    sell_result = await self._execute_single_trade(
                        execution_id=execution_id,
                        trade_number=trade_num,
                        trade_type="sell",
                        input_mint=request.tokenMint,
                        output_mint=SOL_MINT,
                        amount_tokens=sell_amount_tokens,
                        slippage_bps=request.slippageBps,
                        wallet_pubkey=request.walletPublicKey,
                        wallet_keypair=wallet_keypair
                    )
                    
                    # Update execution progress
                    execution_data["trades_completed"] = trade_num
                    execution_data["volume_generated"] += request.tradeSizeSol * 2 * 100  # Rough USD estimate
                    execution_data["fees_spent"] += buy_result.get("fees", 0) + sell_result.get("fees", 0)
                    execution_data["last_update"] = datetime.utcnow()
                    
                    # Send progress update via WebSocket
                    progress = (trade_num / request.numTrades) * 100
                    estimated_remaining = int((request.numTrades - trade_num) * (base_delay / 60))
                    
                    trade_update = TradeUpdate(
                        executionId=execution_id,
                        tradeNumber=trade_num,
                        totalTrades=request.numTrades,
                        status=TradeStatus.RUNNING,
                        volumeGenerated=execution_data["volume_generated"],
                        feesSpent=execution_data["fees_spent"],
                        progress=progress,
                        lastTradeResult={
                            "buy": buy_result,
                            "sell": sell_result
                        },
                        estimatedTimeRemaining=estimated_remaining
                    )
                    
                    await websocket_manager.send_trade_update(execution_id, trade_update)
                    
                    logger.info(f"Execution {execution_id}: Completed trade pair {trade_num}/{request.numTrades}")
                    
                    # Wait before next trade pair
                    if trade_num < request.numTrades:
                        await asyncio.sleep(delay)
                        
                except asyncio.CancelledError:
                    execution_data["status"] = TradeStatus.CANCELLED
                    break
                except Exception as e:
                    logger.error(f"Error in trade pair {trade_num}: {str(e)}")
                    await websocket_manager.send_error(execution_id, f"Trade error: {str(e)}")
                    continue
            
            # Complete execution
            if execution_data["status"] != TradeStatus.CANCELLED:
                execution_data["status"] = TradeStatus.COMPLETED
                execution_data["end_time"] = datetime.utcnow()
                
                await websocket_manager.send_status_update(
                    execution_id,
                    "completed",
                    {
                        "message": "Volume trading execution completed successfully",
                        "totalTrades": execution_data["trades_completed"],
                        "volumeGenerated": execution_data["volume_generated"],
                        "feesSpent": execution_data["fees_spent"]
                    }
                )
                
                # Create execution summary
                self._create_execution_summary(execution_id)
            
            logger.info(f"Execution {execution_id} finished with status: {execution_data['status']}")
            
        except Exception as e:
            logger.error(f"Fatal error in execution {execution_id}: {str(e)}")
            execution_data["status"] = TradeStatus.FAILED
            execution_data["end_time"] = datetime.utcnow()
            await websocket_manager.send_error(execution_id, "Execution failed", str(e))
    
    async def _execute_single_trade(
        self, 
        execution_id: str,
        trade_number: int,
        trade_type: str,
        input_mint: str,
        output_mint: str,
        amount_sol: Optional[float] = None,
        amount_tokens: Optional[int] = None,
        slippage_bps: int = 50,
        wallet_pubkey: str = None,
        wallet_keypair: Optional[Keypair] = None
    ) -> Dict:
        """
        Execute a single trade (buy or sell) with REAL Jupiter swap execution
        
        Args:
            wallet_keypair: Optional Keypair for signing. If not provided, will try to get from wallet_keypairs dict.
                          For security, prefer passing keypair directly rather than storing on backend.
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Determine amount based on trade type
                if trade_type == "buy" and amount_sol:
                    amount = int(amount_sol * 1_000_000_000)  # Convert SOL to lamports
                elif trade_type == "sell" and amount_tokens:
                    amount = amount_tokens
                else:
                    return {"success": False, "error": "Invalid amount specified"}
                
                # Create swap quote request
                swap_request = SwapQuoteRequest(
                    inputMint=input_mint,
                    outputMint=output_mint,
                    amount=amount,
                    slippageBps=slippage_bps
                )
                
                # Get quote and transaction from Jupiter
                swap_response = await self.jupiter_service.get_swap_quote_and_transaction(swap_request)
                
                # Get wallet keypair for signing
                if wallet_keypair is None:
                    if wallet_pubkey and wallet_pubkey in self.wallet_keypairs:
                        wallet_keypair = self.wallet_keypairs[wallet_pubkey]
                    else:
                        # If no keypair available, we cannot sign the transaction
                        # In production, this would require frontend signing or secure key management
                        logger.warning(f"No keypair available for wallet {wallet_pubkey}, cannot execute real swap")
                        return {
                            "success": False,
                            "error": "Wallet keypair required for transaction signing. Use bot_logic for sub-wallet trades."
                        }
                
                # Execute REAL swap transaction
                swap_result = await self._execute_real_swap(
                    swap_response.swapTransaction,
                    wallet_keypair,
                    wallet_pubkey or str(wallet_keypair.pubkey()),
                    trade_type
                )
                
                if not swap_result["success"]:
                    logger.warning(f"Swap failed (attempt {retry_count + 1}/{max_retries}): {swap_result.get('error')}")
                    retry_count += 1
                    if retry_count < max_retries:
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                        continue
                    else:
                        return swap_result
                
                # Calculate fees (estimate based on transaction)
                estimated_fees = 0.000005  # Base fee ~5000 lamports
                if amount_sol:
                    estimated_fees += amount_sol * 0.001  # ~0.1% trading fee estimate
                
                # Calculate execution price (approximate)
                if trade_type == "buy" and amount_sol:
                    execution_price = (swap_response.outputAmount / amount) * 100  # Rough USD estimate
                else:
                    execution_price = (amount / swap_response.outputAmount) * 100  # Rough USD estimate
                
                # Record trade in history
                trade_entry = TradeHistoryEntry(
                    executionId=execution_id,
                    timestamp=datetime.utcnow().isoformat(),
                    tokenMint=output_mint if trade_type == "buy" else input_mint,
                    tradeType=trade_type,
                    amount=amount_sol if amount_sol else amount_tokens / 1_000_000_000,
                    price=execution_price,
                    fees=estimated_fees,
                    status="completed",
                    txSignature=swap_result.get("signature")
                )
                
                self.trade_history.append(trade_entry)
                
                logger.info(f"✅ Real swap executed: {trade_type} - TX: {swap_result.get('signature', 'N/A')[:16]}...")
                
                return {
                    "success": True,
                    "output_amount": swap_response.outputAmount,
                    "fees": estimated_fees,
                    "signature": swap_result.get("signature"),
                    "price_impact": swap_response.priceImpact,
                    "price": execution_price
                }
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Trade execution error (attempt {retry_count}/{max_retries}): {str(e)}")
                
                if retry_count >= max_retries:
                    return {"success": False, "error": str(e)}
                
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
        
        return {"success": False, "error": "Max retries exceeded"}
    
    async def _execute_real_swap(
        self,
        swap_transaction_base64: str,
        wallet_keypair: Keypair,
        wallet_pubkey: str,
        trade_type: str
    ) -> Dict:
        """
        Execute REAL Jupiter swap transaction on Solana network
        
        Args:
            swap_transaction_base64: Base64 encoded transaction from Jupiter
            wallet_keypair: Keypair to sign the transaction
            wallet_pubkey: Wallet public key for logging
            trade_type: "buy" or "sell" for logging
        
        Returns:
            Dict with success status, signature, and error if any
        """
        try:
            # Decode the transaction
            transaction_bytes = base64.b64decode(swap_transaction_base64)
            versioned_tx = VersionedTransaction.from_bytes(transaction_bytes)
            
            # Sign the transaction with wallet keypair
            versioned_tx.sign([wallet_keypair])
            
            # Send transaction to Solana network
            logger.info(f"Sending {trade_type} transaction to Solana network...")
            tx_signature = await self.solana_client.send_transaction(
                versioned_tx,
                opts={"skip_preflight": False, "max_retries": 3}
            )
            
            signature = str(tx_signature.value)
            logger.info(f"Transaction sent: {signature[:16]}... (type: {trade_type})")
            
            # Wait for confirmation
            logger.info(f"Waiting for confirmation of {trade_type} transaction...")
            confirmation = await self.solana_client.confirm_transaction(
                signature,
                commitment=Confirmed
            )
            
            if confirmation.value.err:
                error_msg = f"Transaction failed: {confirmation.value.err}"
                logger.error(f"{trade_type.upper()} transaction failed: {error_msg}")
                return {
                    "success": False,
                    "signature": signature,
                    "error": error_msg
                }
            
            logger.info(f"✅ {trade_type.upper()} transaction confirmed: {signature[:16]}...")
            
            return {
                "success": True,
                "signature": signature,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing real swap ({trade_type}): {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _calculate_trade_delay(self, base_delay: float, strategy: str) -> float:
        """Calculate delay between trades based on strategy"""
        if strategy == "aggressive":
            return random.uniform(base_delay * 0.7, base_delay * 1.1)
        elif strategy == "organic":
            return random.uniform(base_delay * 0.5, base_delay * 1.8)
        else:  # balanced
            return random.uniform(base_delay * 0.8, base_delay * 1.2)
    
    async def _get_wallet_balance(self, wallet_pubkey: str) -> float:
        """Get wallet SOL balance from Solana RPC"""
        try:
            pubkey = Pubkey.from_string(wallet_pubkey)
            response = await self.solana_client.get_balance(pubkey)
            
            if response.value is None:
                logger.warning(f"Could not get balance for wallet {wallet_pubkey}")
                return 0.0
            
            # Convert lamports to SOL
            balance_sol = response.value / 1_000_000_000
            logger.debug(f"Wallet {wallet_pubkey[:8]}... balance: {balance_sol:.4f} SOL")
            return balance_sol
            
        except Exception as e:
            logger.error(f"Error getting wallet balance for {wallet_pubkey}: {str(e)}")
            # Return 0 instead of random to avoid false positives
            return 0.0
    
    def _create_execution_summary(self, execution_id: str):
        """Create execution summary for completed execution"""
        execution_data = self.active_executions[execution_id]
        request = execution_data["request"]
        
        duration = execution_data.get("end_time", datetime.utcnow()) - execution_data["start_time"]
        efficiency = (execution_data["trades_completed"] / request.numTrades) * 100
        
        summary = ExecutionSummary(
            executionId=execution_id,
            walletPublicKey=request.walletPublicKey,
            tokenMint=request.tokenMint,
            startTime=execution_data["start_time"].isoformat(),
            endTime=execution_data.get("end_time", datetime.utcnow()).isoformat(),
            status=execution_data["status"],
            tradesCompleted=execution_data["trades_completed"],
            totalVolume=execution_data["volume_generated"],
            totalFees=execution_data["fees_spent"],
            efficiency=efficiency
        )
        
        self.execution_summaries.append(summary)
    
    def get_trade_history(self, execution_id: Optional[str] = None, page: int = 1, page_size: int = 50) -> List[TradeHistoryEntry]:
        """Get trade history with optional filtering"""
        history = self.trade_history
        
        if execution_id:
            history = [trade for trade in history if trade.executionId == execution_id]
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        
        return history[start:end]
    
    def get_execution_summaries(self) -> List[ExecutionSummary]:
        """Get all execution summaries"""
        return self.execution_summaries
    
    def get_active_executions(self) -> Dict[str, Dict]:
        """Get all active executions"""
        return {
            exec_id: {
                "id": exec_id,
                "status": data["status"],
                "trades_completed": data["trades_completed"],
                "start_time": data["start_time"].isoformat(),
                "request": data["request"].dict()
            }
            for exec_id, data in self.active_executions.items()
            if data["status"] in [TradeStatus.PENDING, TradeStatus.RUNNING, TradeStatus.PAUSED]
        }
    
    def register_wallet_keypair(self, wallet_pubkey: str, keypair: Keypair):
        """
        Register a wallet keypair for transaction signing
        
        WARNING: In production, use secure key management instead of storing keypairs in memory.
        This is only suitable for sub-wallets generated by the bot.
        """
        self.wallet_keypairs[wallet_pubkey] = keypair
        logger.info(f"Registered keypair for wallet {wallet_pubkey[:8]}...")
    
    def unregister_wallet_keypair(self, wallet_pubkey: str):
        """Remove a wallet keypair from memory"""
        if wallet_pubkey in self.wallet_keypairs:
            del self.wallet_keypairs[wallet_pubkey]
            logger.info(f"Unregistered keypair for wallet {wallet_pubkey[:8]}...")
    
    async def close(self):
        """Cleanup resources"""
        await self.solana_client.close()
        # Clear keypairs from memory
        self.wallet_keypairs.clear()
        logger.info("TradeExecutor closed and resources cleaned up")