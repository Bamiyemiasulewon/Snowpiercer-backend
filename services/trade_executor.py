import asyncio
import uuid
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from models import (
    TradeExecutionRequest, TradeExecutionResponse, TradeStatus, TradeUpdate,
    SwapQuoteRequest, TradeHistoryEntry, ExecutionSummary
)
from services.jupiter import JupiterService
from services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self, jupiter_service: JupiterService):
        self.jupiter_service = jupiter_service
        # In-memory storage for active executions
        self.active_executions: Dict[str, Dict] = {}
        # Trade history storage (in production, this would be a database)
        self.trade_history: List[TradeHistoryEntry] = []
        self.execution_summaries: List[ExecutionSummary] = []
        
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
                    buy_result = await self._execute_single_trade(
                        execution_id=execution_id,
                        trade_number=trade_num,
                        trade_type="buy",
                        input_mint=SOL_MINT,
                        output_mint=request.tokenMint,
                        amount_sol=request.tradeSizeSol,
                        slippage_bps=request.slippageBps,
                        wallet_pubkey=request.walletPublicKey
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
                        wallet_pubkey=request.walletPublicKey
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
        wallet_pubkey: str = None
    ) -> Dict:
        """Execute a single trade (buy or sell)"""
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
            
            # Get quote and transaction
            swap_response = await self.jupiter_service.get_swap_quote_and_transaction(swap_request)
            
            # In a real implementation, you would:
            # 1. Sign the transaction with the wallet's private key
            # 2. Send the transaction to the Solana network
            # 3. Wait for confirmation
            # 4. Parse the transaction results
            
            # For now, we'll simulate the trade execution
            simulated_result = self._simulate_trade_execution(swap_response, trade_type)
            
            # Record trade in history
            trade_entry = TradeHistoryEntry(
                executionId=execution_id,
                timestamp=datetime.utcnow().isoformat(),
                tokenMint=output_mint if trade_type == "buy" else input_mint,
                tradeType=trade_type,
                amount=amount_sol if amount_sol else amount_tokens / 1_000_000_000,
                price=simulated_result.get("price"),
                fees=simulated_result.get("fees", 0),
                status="completed",
                txSignature=simulated_result.get("signature")
            )
            
            self.trade_history.append(trade_entry)
            
            return {
                "success": True,
                "output_amount": swap_response.outputAmount,
                "fees": simulated_result.get("fees", 0),
                "signature": simulated_result.get("signature"),
                "price_impact": swap_response.priceImpact
            }
            
        except Exception as e:
            logger.error(f"Trade execution error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _simulate_trade_execution(self, swap_response, trade_type: str) -> Dict:
        """Simulate trade execution results"""
        # Generate fake transaction signature
        fake_signature = ''.join(random.choices('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz', k=88))
        
        # Estimate fees (0.1-0.3% + gas)
        estimated_fees = random.uniform(0.001, 0.003)  # SOL
        
        # Simulate execution price
        base_price = 100.0  # Mock price
        price_variation = random.uniform(-0.02, 0.02)  # ±2% variation
        execution_price = base_price * (1 + price_variation)
        
        return {
            "signature": fake_signature,
            "fees": estimated_fees,
            "price": execution_price,
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
        """Get wallet SOL balance (simulated)"""
        # In a real implementation, you would query the Solana RPC
        # For now, return a simulated balance
        return random.uniform(5.0, 50.0)  # Random balance between 5-50 SOL
    
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