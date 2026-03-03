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