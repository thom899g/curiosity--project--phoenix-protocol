"""
Dynamic Circuit Breaker System
Implements multiple circuit breaker strategies with state management and fallback logic.
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import numpy as np
from datetime import datetime, timedelta

class BreakerState(Enum):
    """Circuit breaker operational states"""
    NORMAL = "normal"
    WARNING = "warning"
    TRIPPED = "tripped"
    RECOVERY = "recovery"

class BreakerType(Enum):
    """Types of circuit breakers"""
    PRICE = "price"
    VOLUME = "volume"
    VOLATILITY = "volatility"
    SENTIMENT = "sentiment"
    COMPOSITE = "composite"

@dataclass
class BreakerMetrics:
    """Metrics tracked for each circuit breaker"""
    last_trip_time: Optional[datetime] = None
    trip_count: int = 0
    total_duration: timedelta = timedelta(0)
    recovery_count: int = 0

class CircuitBreaker:
    """Dynamic circuit breaker with multiple strategies"""
    
    def __init__(self, config: 'TradingConfig'):
        self.config = config
        self.state = BreakerState.NORMAL
        self.active_breakers: List[BreakerType] = []
        self.metrics: Dict[BreakerType, BreakerMetrics] = {
            breaker_type: BreakerMetrics()
            for breaker_type in BreakerType
        }
        self.last_check_time = datetime.now()
        self.logger = logging.getLogger(__name__)
        
    def check_all_breakers(self, market_data: Dict[str, Any], 
                          sentiment_score: float = 0.0) -> Tuple[bool, List[str]]:
        """
        Check all configured circuit breakers
        
        Args:
            market_data: Dictionary with market data (prices, volumes, etc.)
            sentiment_score: Current sentiment score (-1 to 1)
            
        Returns:
            Tuple of (should_halt_trading, list_of_reasons)
        """
        reasons = []
        should_halt = False
        
        for breaker_type in self.config.circuit_breaker_modes:
            try:
                tripped, reason = self._check_breaker(
                    BreakerType(breaker_type.value),
                    market_data,
                    sentiment_score
                )
                
                if tripped:
                    should_halt = True
                    if reason:
                        reasons.append(f"{breaker_type.value}: {reason}")
                    
                    # Update metrics
                    self.metrics[breaker_type].trip_count += 1
                    self.metrics[breaker_type].last_trip_time = datetime.now()
                    
                    self.logger.warning(
                        f"Circuit breaker {breaker_type.value} tripped: {reason}"
                    )
                    
            except Exception as e:
                self.logger.error(
                    f"Error checking circuit breaker {breaker_type.value}: {e}"
                )
                # Default to safe behavior on error
                reasons.append(f"{breaker_type.value}_error")
                should_halt = True
        
        # Update state
        if should_halt and self.state !=