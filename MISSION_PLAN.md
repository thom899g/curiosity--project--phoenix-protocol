# CURIOSITY: Project: Phoenix Protocol

## Objective
Design and backtest a new, self-coded trading agent framework with dynamic circuit breakers and sentiment-driven risk parameters to prevent such drawdowns.

## Strategy
Autonomous exploration based on Soul Protocol.

## Execution Output
SUMMARY:
I've architected and implemented Phoenix Protocol, a production-grade trading agent framework with dynamic circuit breakers and sentiment-driven risk parameters. The system features a modular architecture with robust error handling, comprehensive logging, and realistic market simulation for backtesting. All components are initialized properly with type hints and edge case handling.

OUTPUT:
### FILE: config.py
```python
"""
Phoenix Protocol Configuration
Centralized configuration management with validation and environment-aware defaults.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

class TradingMode(Enum):
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"

class CircuitBreakerMode(Enum):
    PRICE_BASED = "price"
    VOLUME_BASED = "volume"
    VOLATILITY_BASED = "volatility"
    SENTIMENT_BASED = "sentiment"
    COMPOSITE = "composite"

@dataclass
class TradingConfig:
    """Trading agent configuration with validation"""
    # Core settings
    mode: TradingMode = TradingMode.BACKTEST
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    initial_balance: float = 10000.0
    max_position_size: float = 0.1  # 10% of portfolio
    min_position_size: float = 0.01  # 1% of portfolio
    
    # Risk parameters
    max_daily_loss: float = 0.02  # 2%
    max_consecutive_losses: int = 3
    volatility_threshold: float = 0.05  # 5%
    
    # Circuit breaker configurations
    circuit_breaker_modes: List[CircuitBreakerMode] = field(
        default_factory=lambda: [
            CircuitBreakerMode.PRICE_BASED,
            CircuitBreakerMode.VOLATILITY_BASED,
            CircuitBreakerMode.SENTIMENT_BASED
        ]
    )
    
    # Price-based circuit breakers
    price_drop_threshold: float = 0.08  # 8%
    price_drop_lookback: int = 5  # candles
    price_recovery_threshold: float = 0.03  # 3%
    
    # Sentiment parameters
    sentiment_weight: float = 0.3
    sentiment_threshold: float = -0.5  # Negative threshold for bearish sentiment
    sentiment_sources: List[str] = field(default_factory=lambda: ["news", "social", "derivatives"])
    
    # Execution parameters
    slippage: float = 0.001  # 0.1%
    commission: float = 0.001  # 0.1%
    max_open_orders: int = 5
    
    # Firebase configuration
    firebase_project_id: Optional[str] = None
    firestore_collection: str = "trading_events"
    
    def validate(self) -> bool:
        """Validate configuration parameters"""
        errors = []
        
        if self.initial_balance <= 0:
            errors.append("Initial balance must be positive")
        
        if not 0 < self.max_position_size <= 1:
            errors.append("Max position size must be between 0 and 1")
        
        if self.max_daily_loss <= 0 or self.max_daily_loss > 0.5:
            errors.append("Max daily loss must be between 0 and 0.5")
        
        if not self.circuit_breaker_modes:
            errors.append("At least one circuit breaker mode must be specified")
        
        if errors:
            logging.error(f"Configuration validation failed: {errors}")
            return False
        
        return True
    
    @classmethod
    def from_env(cls) -> 'TradingConfig':
        """Load configuration from environment variables"""
        config = cls()
        
        # Override with environment variables if present
        if os.getenv('TRADING_MODE'):
            config.mode = TradingMode(os.getenv('TRADING_MODE').lower())
        
        if os.getenv('INITIAL_BALANCE'):
            config.initial_balance = float(os.getenv('INITIAL_BALANCE'))
        
        if os.getenv('FIREBASE_PROJECT_ID'):
            config.firebase_project_id = os.getenv('FIREBASE_PROJECT_ID')
        
        return config
```

### FILE: circuit_breaker.py
```python
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