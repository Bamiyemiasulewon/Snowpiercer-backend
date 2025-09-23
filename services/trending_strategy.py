import asyncio
import random
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

from models import TradeExecutionRequest, SwapQuoteRequest
from services.jupiter import JupiterService

logger = logging.getLogger(__name__)

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

@dataclass
class TrendingConfig:
    platform: TrendingPlatform
    intensity: TrendingIntensity
    target_volume_24h: float  # Target 24h volume in USD
    target_transactions: int  # Target transaction count
    price_impact_tolerance: float  # Maximum price impact per trade
    time_window_hours: int  # Time window to achieve targets
    use_multiple_wallets: bool  # Simulate multiple traders
    include_failed_txs: bool  # Include some failed transactions for realism

class TrendingStrategy:
    """
    Advanced trending strategy service for DEX platforms
    
    This service implements sophisticated trading patterns that trigger
    trending algorithms on major DEX tracking platforms.
    """
    
    def __init__(self, jupiter_service: JupiterService):
        self.jupiter_service = jupiter_service
        self.platform_requirements = self._initialize_platform_requirements()
        
    def _initialize_platform_requirements(self) -> Dict[TrendingPlatform, Dict[str, Any]]:
        """Initialize platform-specific trending requirements"""
        return {
            TrendingPlatform.DEXSCREENER: {
                "min_volume_1h": 5000,      # Minimum $5K volume for 1h trending
                "min_volume_24h": 50000,    # Minimum $50K volume for 24h trending
                "min_transactions": 100,     # Minimum transactions
                "optimal_trade_size": 500,   # Optimal individual trade size
                "update_frequency": 300,     # 5-minute data updates
                "trending_algorithm": "volume_weighted_momentum",
                "key_metrics": ["volume_24h", "price_change_24h", "transactions", "holders"]
            },
            TrendingPlatform.DEXTOOLS: {
                "min_volume_1h": 3000,      # Lower barrier for initial trending
                "min_volume_24h": 25000,    # $25K for strong trending
                "min_transactions": 75,      # Minimum transactions
                "optimal_trade_size": 300,   # Smaller trades preferred
                "update_frequency": 180,     # 3-minute updates
                "trending_algorithm": "transaction_velocity",
                "key_metrics": ["volume_1h", "tx_count", "unique_traders", "momentum"]
            },
            TrendingPlatform.JUPITER: {
                "min_volume_1h": 2000,      # Integrated with Jupiter aggregator
                "min_volume_24h": 15000,    # Lower requirements as it's our primary DEX
                "min_transactions": 50,      # Focus on quality over quantity
                "optimal_trade_size": 1000,  # Larger trades show confidence
                "update_frequency": 120,     # 2-minute updates
                "trending_algorithm": "routing_popularity",
                "key_metrics": ["routing_volume", "swap_frequency", "liquidity_depth"]
            },
            TrendingPlatform.BIRDEYE: {
                "min_volume_1h": 4000,
                "min_volume_24h": 35000,
                "min_transactions": 80,
                "optimal_trade_size": 400,
                "update_frequency": 240,     # 4-minute updates
                "trending_algorithm": "social_volume_blend",
                "key_metrics": ["volume_24h", "social_mentions", "holder_growth"]
            },
            TrendingPlatform.SOLSCAN: {
                "min_volume_1h": 1000,      # Lower barrier, more technical audience
                "min_volume_24h": 10000,
                "min_transactions": 30,
                "optimal_trade_size": 200,
                "update_frequency": 60,      # Real-time updates
                "trending_algorithm": "network_activity",
                "key_metrics": ["transaction_volume", "program_interactions", "account_activity"]
            }
        }
    
    def calculate_trending_parameters(self, config: TrendingConfig) -> Dict[str, Any]:
        """Calculate optimal trading parameters for trending"""
        platform_req = self.platform_requirements.get(config.platform, 
                                                     self.platform_requirements[TrendingPlatform.DEXSCREENER])
        
        # Base calculations
        total_minutes = config.time_window_hours * 60
        target_volume = config.target_volume_24h
        target_txs = config.target_transactions
        
        # Intensity multipliers
        intensity_multipliers = {
            TrendingIntensity.ORGANIC: {"volume": 1.0, "speed": 1.0, "randomness": 0.8},
            TrendingIntensity.AGGRESSIVE: {"volume": 1.5, "speed": 2.0, "randomness": 0.3},
            TrendingIntensity.STEALTH: {"volume": 0.7, "speed": 0.5, "randomness": 1.2},
            TrendingIntensity.VIRAL: {"volume": 2.0, "speed": 3.0, "randomness": 0.2}
        }
        
        multiplier = intensity_multipliers[config.intensity]
        
        # Calculate trading pattern
        avg_trade_size = (target_volume / target_txs) * multiplier["volume"]
        trade_interval = (total_minutes / target_txs) / multiplier["speed"]
        randomness_factor = multiplier["randomness"]
        
        # Platform-specific optimizations
        optimal_trade_size = platform_req["optimal_trade_size"]
        if abs(avg_trade_size - optimal_trade_size) > optimal_trade_size * 0.5:
            # Adjust trade count and size for platform optimization
            target_txs = int(target_volume / optimal_trade_size)
            avg_trade_size = optimal_trade_size
            trade_interval = total_minutes / target_txs
        
        return {
            "target_transactions": target_txs,
            "average_trade_size_usd": avg_trade_size,
            "trade_interval_minutes": trade_interval,
            "randomness_factor": randomness_factor,
            "price_impact_limit": config.price_impact_tolerance,
            "platform_requirements": platform_req,
            "burst_patterns": self._calculate_burst_patterns(config, platform_req),
            "timing_strategy": self._calculate_timing_strategy(config, platform_req)
        }
    
    def _calculate_burst_patterns(self, config: TrendingConfig, platform_req: Dict) -> List[Dict]:
        """Calculate burst trading patterns for maximum trending impact"""
        patterns = []
        update_frequency = platform_req["update_frequency"]
        
        if config.intensity in [TrendingIntensity.AGGRESSIVE, TrendingIntensity.VIRAL]:
            # Create burst patterns aligned with platform update cycles
            burst_count = max(1, config.time_window_hours * 60 // update_frequency)
            
            for i in range(int(burst_count)):
                burst_start = i * update_frequency
                burst_duration = min(30, update_frequency // 2)  # 30min max burst
                burst_intensity = random.uniform(1.5, 3.0) if config.intensity == TrendingIntensity.VIRAL else random.uniform(1.2, 2.0)
                
                patterns.append({
                    "start_minute": burst_start,
                    "duration_minutes": burst_duration,
                    "intensity_multiplier": burst_intensity,
                    "trade_size_multiplier": burst_intensity * 0.8,
                    "frequency_multiplier": burst_intensity * 1.2
                })
        
        return patterns
    
    def _calculate_timing_strategy(self, config: TrendingConfig, platform_req: Dict) -> Dict:
        """Calculate optimal timing strategy for platform algorithms"""
        now = datetime.utcnow()
        
        # Platform-specific optimal timing
        timing_strategies = {
            TrendingPlatform.DEXSCREENER: {
                "optimal_start_hours": [13, 14, 15, 16, 17],  # UTC peak hours
                "avoid_hours": [2, 3, 4, 5, 6],               # Low activity hours
                "weekend_multiplier": 0.7,
                "pre_trending_buildup": 60  # Build volume 1h before peak
            },
            TrendingPlatform.DEXTOOLS: {
                "optimal_start_hours": [14, 15, 16, 17, 18],
                "avoid_hours": [1, 2, 3, 4, 5, 6],
                "weekend_multiplier": 0.8,
                "pre_trending_buildup": 30
            },
            TrendingPlatform.JUPITER: {
                "optimal_start_hours": [12, 13, 14, 15, 16, 17, 18, 19],  # Longer window
                "avoid_hours": [2, 3, 4, 5],
                "weekend_multiplier": 0.9,
                "pre_trending_buildup": 45
            }
        }
        
        default_strategy = timing_strategies.get(config.platform, timing_strategies[TrendingPlatform.DEXSCREENER])
        
        current_hour = now.hour
        is_weekend = now.weekday() >= 5
        
        # Calculate timing adjustments
        timing_multiplier = 1.0
        if current_hour in default_strategy["avoid_hours"]:
            timing_multiplier *= 0.5
        elif current_hour in default_strategy["optimal_start_hours"]:
            timing_multiplier *= 1.3
        
        if is_weekend:
            timing_multiplier *= default_strategy["weekend_multiplier"]
        
        return {
            **default_strategy,
            "current_timing_multiplier": timing_multiplier,
            "recommended_start": current_hour in default_strategy["optimal_start_hours"],
            "delay_recommendation": 0 if current_hour in default_strategy["optimal_start_hours"] else 
                                  min(default_strategy["optimal_start_hours"]) - current_hour if current_hour < min(default_strategy["optimal_start_hours"]) else 
                                  24 + min(default_strategy["optimal_start_hours"]) - current_hour
        }
    
    async def generate_trending_trades(self, 
                                     token_mint: str,
                                     config: TrendingConfig,
                                     wallet_pubkey: str) -> List[Dict]:
        """Generate optimized trade sequence for trending"""
        
        params = self.calculate_trending_parameters(config)
        trades = []
        
        SOL_MINT = "So11111111111111111111111111111111111111112"
        LAMPORTS_PER_SOL = 1_000_000_000
        
        total_trades = params["target_transactions"]
        base_interval = params["trade_interval_minutes"] * 60  # Convert to seconds
        randomness = params["randomness_factor"]
        
        # Get current token price for volume calculations
        try:
            sample_quote = await self.jupiter_service.get_quote(SwapQuoteRequest(
                inputMint=SOL_MINT,
                outputMint=token_mint,
                amount=int(0.1 * LAMPORTS_PER_SOL),  # 0.1 SOL sample
                slippageBps=50
            ))
            
            # Estimate token price in USD (rough calculation)
            sol_price = 100  # Approximate SOL price in USD
            token_per_sol = int(sample_quote.get("outAmount", 1)) / LAMPORTS_PER_SOL
            
        except Exception as e:
            logger.warning(f"Could not get token price, using defaults: {e}")
            sol_price = 100
            token_per_sol = 1000000  # Default assumption
        
        current_time = 0
        
        for i in range(total_trades):
            # Calculate trade size with variation
            base_trade_size_usd = params["average_trade_size_usd"]
            size_variation = random.uniform(0.3, 1.7) * randomness
            trade_size_usd = base_trade_size_usd * size_variation
            trade_size_sol = trade_size_usd / sol_price
            
            # Ensure minimum trade size
            trade_size_sol = max(0.001, min(10.0, trade_size_sol))
            
            # Apply burst patterns
            burst_multiplier = 1.0
            for burst in params["burst_patterns"]:
                if (burst["start_minute"] * 60 <= current_time <= 
                    (burst["start_minute"] + burst["duration_minutes"]) * 60):
                    burst_multiplier = burst["intensity_multiplier"]
                    break
            
            trade_size_sol *= burst_multiplier
            
            # Create trade pair (buy + sell)
            trades.extend([
                {
                    "timestamp": current_time,
                    "type": "buy",
                    "input_mint": SOL_MINT,
                    "output_mint": token_mint,
                    "amount_sol": trade_size_sol,
                    "slippage_bps": min(100, int(50 + burst_multiplier * 20)),
                    "priority": "high" if burst_multiplier > 1.5 else "normal",
                    "delay_after": random.uniform(2, 8)  # Delay before sell
                },
                {
                    "timestamp": current_time + random.uniform(2, 8),
                    "type": "sell",
                    "input_mint": token_mint,
                    "output_mint": SOL_MINT,
                    "amount_sol": trade_size_sol * 0.98,  # Account for slippage
                    "slippage_bps": min(100, int(50 + burst_multiplier * 20)),
                    "priority": "high" if burst_multiplier > 1.5 else "normal",
                    "delay_after": 0
                }
            ])
            
            # Calculate next trade timing
            interval_variation = random.uniform(0.5, 1.5) * randomness
            next_interval = base_interval * interval_variation / burst_multiplier
            current_time += next_interval
        
        # Sort trades by timestamp
        trades.sort(key=lambda x: x["timestamp"])
        
        # Add some organic randomization
        if config.intensity != TrendingIntensity.VIRAL:
            trades = self._add_organic_randomization(trades, randomness)
        
        # Add failed transactions for realism
        if config.include_failed_txs:
            trades = self._add_realistic_failures(trades)
        
        logger.info(f"Generated {len(trades)} trending trades for {config.platform.value} "
                   f"targeting ${config.target_volume_24h:.0f} volume over {config.time_window_hours}h")
        
        return trades
    
    def _add_organic_randomization(self, trades: List[Dict], randomness: float) -> List[Dict]:
        """Add organic-looking randomization to trading patterns"""
        if randomness < 0.5:
            return trades  # Skip for low randomness
        
        # Add some random small trades
        organic_trades = []
        for i, trade in enumerate(trades):
            organic_trades.append(trade)
            
            # Occasionally add micro-trades
            if random.random() < 0.1 * randomness and trade["type"] == "buy":
                micro_trade = trade.copy()
                micro_trade["amount_sol"] *= random.uniform(0.1, 0.3)
                micro_trade["timestamp"] += random.uniform(10, 60)
                organic_trades.append(micro_trade)
        
        # Add some random timing jitter
        for trade in organic_trades:
            jitter = random.uniform(-30, 30) * randomness
            trade["timestamp"] = max(0, trade["timestamp"] + jitter)
        
        organic_trades.sort(key=lambda x: x["timestamp"])
        return organic_trades
    
    def _add_realistic_failures(self, trades: List[Dict]) -> List[Dict]:
        """Add realistic transaction failures for organic appearance"""
        failure_rate = 0.02  # 2% failure rate
        failed_trades = []
        
        for trade in trades:
            if random.random() < failure_rate:
                failed_trade = trade.copy()
                failed_trade["will_fail"] = True
                failed_trade["failure_reason"] = random.choice([
                    "slippage_exceeded",
                    "insufficient_liquidity", 
                    "network_congestion",
                    "gas_price_too_low"
                ])
                failed_trades.append(failed_trade)
            else:
                failed_trades.append(trade)
        
        return failed_trades
    
    def estimate_trending_probability(self, config: TrendingConfig, current_metrics: Dict) -> Dict[str, float]:
        """Estimate probability of trending on each platform"""
        probabilities = {}
        
        for platform, requirements in self.platform_requirements.items():
            if config.platform != TrendingPlatform.ALL and config.platform != platform:
                continue
                
            # Calculate probability based on requirements
            volume_score = min(1.0, config.target_volume_24h / requirements["min_volume_24h"])
            tx_score = min(1.0, config.target_transactions / requirements["min_transactions"])
            
            # Intensity bonus
            intensity_bonus = {
                TrendingIntensity.ORGANIC: 0.8,
                TrendingIntensity.AGGRESSIVE: 1.1,
                TrendingIntensity.STEALTH: 0.9,
                TrendingIntensity.VIRAL: 1.3
            }[config.intensity]
            
            # Calculate final probability
            base_probability = (volume_score * 0.6 + tx_score * 0.4) * intensity_bonus
            
            # Apply current market conditions (placeholder)
            market_multiplier = random.uniform(0.8, 1.2)  # Simulate market conditions
            
            final_probability = min(0.95, base_probability * market_multiplier)
            probabilities[platform.value] = final_probability
        
        return probabilities
    
    def get_trending_recommendations(self, token_mint: str, current_volume: float = 0) -> List[Dict]:
        """Get trending strategy recommendations"""
        recommendations = []
        
        for platform in [TrendingPlatform.DEXSCREENER, TrendingPlatform.DEXTOOLS, TrendingPlatform.JUPITER]:
            req = self.platform_requirements[platform]
            
            # Calculate requirements
            volume_needed = max(0, req["min_volume_24h"] - current_volume)
            estimated_cost = volume_needed * 0.005  # Estimate 0.5% cost for volume generation
            
            recommendation = {
                "platform": platform.value,
                "volume_needed_24h": volume_needed,
                "estimated_cost_sol": estimated_cost / 100,  # Convert to SOL
                "minimum_transactions": req["min_transactions"],
                "recommended_intensity": TrendingIntensity.AGGRESSIVE if volume_needed > 30000 else TrendingIntensity.ORGANIC,
                "time_to_trend": "2-4 hours" if volume_needed < 10000 else "4-8 hours",
                "success_probability": min(0.9, (current_volume + volume_needed) / req["min_volume_24h"])
            }
            
            recommendations.append(recommendation)
        
        return sorted(recommendations, key=lambda x: x["estimated_cost_sol"])
    
    def calculate_multi_platform_costs(self, 
                                      platforms: List[TrendingPlatform], 
                                      intensity: TrendingIntensity,
                                      current_volume: float = 0) -> Dict[str, Any]:
        """
        Calculate costs and requirements for multiple platforms
        """
        platform_estimates = []
        total_cost_sol = 0
        total_volume_needed = 0
        total_transactions = 0
        
        # SOL price estimate for calculations
        sol_price_usd = 100  # Approximate SOL price
        
        for platform in platforms:
            if platform == TrendingPlatform.ALL:
                continue
                
            req = self.platform_requirements[platform]
            
            # Calculate volume needed above current volume
            volume_needed = max(0, req["min_volume_24h"] - current_volume)
            
            # Calculate cost (0.5% of volume as fees/slippage)
            cost_usd = volume_needed * 0.005
            cost_sol = cost_usd / sol_price_usd
            
            # Intensity multipliers for cost
            intensity_multipliers = {
                TrendingIntensity.ORGANIC: 1.0,
                TrendingIntensity.AGGRESSIVE: 1.2,
                TrendingIntensity.STEALTH: 0.8,
                TrendingIntensity.VIRAL: 1.5
            }
            
            cost_sol *= intensity_multipliers[intensity]
            
            # Success probability calculation
            base_probability = min(0.95, (current_volume + volume_needed) / req["min_volume_24h"])
            intensity_bonus = {
                TrendingIntensity.ORGANIC: 0.85,
                TrendingIntensity.AGGRESSIVE: 0.92,
                TrendingIntensity.STEALTH: 0.88,
                TrendingIntensity.VIRAL: 0.95
            }
            success_probability = min(0.98, base_probability * intensity_bonus[intensity])
            
            # Difficulty assessment
            if req["min_volume_24h"] >= 50000:
                difficulty = "high"
            elif req["min_volume_24h"] >= 25000:
                difficulty = "medium"
            else:
                difficulty = "low"
            
            # Time to trend estimation
            if volume_needed < 10000:
                time_to_trend = "2-4 hours"
            elif volume_needed < 30000:
                time_to_trend = "4-6 hours"
            else:
                time_to_trend = "6-8 hours"
            
            platform_estimate = {
                "platform": platform.value,
                "volumeRequired": volume_needed,
                "transactionsRequired": req["min_transactions"],
                "estimatedCostSOL": round(cost_sol, 3),
                "successProbability": round(success_probability, 2),
                "timeToTrend": time_to_trend,
                "difficulty": difficulty
            }
            
            platform_estimates.append(platform_estimate)
            total_cost_sol += cost_sol
            total_volume_needed = max(total_volume_needed, volume_needed)  # Use highest requirement
            total_transactions = max(total_transactions, req["min_transactions"])
        
        # Calculate overall success probability (conservative estimate)
        if len(platform_estimates) == 1:
            overall_success = platform_estimates[0]["successProbability"]
        else:
            # For multiple platforms, use average with slight penalty for complexity
            avg_success = sum(p["successProbability"] for p in platform_estimates) / len(platform_estimates)
            complexity_penalty = min(0.1, (len(platform_estimates) - 1) * 0.03)
            overall_success = max(0.5, avg_success - complexity_penalty)
        
        # Duration estimation
        max_duration = max([self._parse_duration(p["timeToTrend"]) for p in platform_estimates])
        if max_duration <= 4:
            duration_str = f"{max_duration}-{max_duration + 2} hours"
        else:
            duration_str = f"{max_duration}-{max_duration + 2} hours"
        
        # Generate recommendations
        recommendations = self._generate_multi_platform_recommendations(
            platform_estimates, intensity, total_cost_sol
        )
        
        return {
            "platform_estimates": platform_estimates,
            "total_cost_sol": round(total_cost_sol, 3),
            "total_volume_required": total_volume_needed,
            "total_transactions": total_transactions,
            "estimated_duration": duration_str,
            "overall_success_probability": round(overall_success, 2),
            "recommendations": recommendations
        }
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string and return average hours"""
        if "2-4" in duration_str:
            return 3
        elif "4-6" in duration_str:
            return 5
        elif "6-8" in duration_str:
            return 7
        else:
            return 4  # default
    
    def _generate_multi_platform_recommendations(self, 
                                               platform_estimates: List[Dict], 
                                               intensity: TrendingIntensity,
                                               total_cost: float) -> str:
        """Generate strategy recommendations for multi-platform trending"""
        recommendations = []
        
        # Cost-based recommendations
        if total_cost < 2:
            recommendations.append("✅ Budget-friendly strategy")
        elif total_cost < 5:
            recommendations.append("💰 Moderate investment required")
        else:
            recommendations.append("🏆 Premium strategy for maximum impact")
        
        # Platform-specific advice
        platform_names = [p["platform"] for p in platform_estimates]
        if "jupiter" in platform_names:
            recommendations.append("🎯 Jupiter trending is highly achievable")
        if "dexscreener" in platform_names:
            recommendations.append("🔥 DEXScreener trending provides maximum visibility")
        if len(platform_names) > 2:
            recommendations.append("🌟 Multi-platform strategy ensures widespread exposure")
        
        # Intensity-based advice
        if intensity == TrendingIntensity.VIRAL:
            recommendations.append("⚡ Viral mode: Expect rapid results but higher costs")
        elif intensity == TrendingIntensity.STEALTH:
            recommendations.append("🥷 Stealth mode: Lower detection risk, longer timeline")
        
        return " • ".join(recommendations)
