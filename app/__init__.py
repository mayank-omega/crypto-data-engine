# app/__init__.py
"""Crypto Data Engine - Production-grade market data collection service."""

__version__ = "1.0.0"
__author__ = "Crypto Trading Platform Team"

# app/models/__init__.py
"""Database models."""

from app.models.market_data import (
    OHLCV,
    Ticker,
    OrderBook,
    Trade,
    MarketMetrics,
    OnChainMetrics,
    DataCollectionStatus
)

__all__ = [
    "OHLCV",
    "Ticker",
    "OrderBook",
    "Trade",
    "MarketMetrics",
    "OnChainMetrics",
    "DataCollectionStatus"
]

# app/schemas/__init__.py
"""Pydantic schemas for API validation."""

from app.schemas.market_data import (
    OHLCVCreate,
    OHLCVResponse,
    TickerCreate,
    TickerResponse,
    OrderBookCreate,
    OrderBookResponse,
    TradeCreate,
    TradeResponse,
    MarketMetricsCreate,
    MarketMetricsResponse,
    OnChainMetricsCreate,
    OnChainMetricsResponse,
    PaginationParams,
    MarketDataQuery,
    HealthCheckResponse,
    WSMessage
)

__all__ = [
    "OHLCVCreate",
    "OHLCVResponse",
    "TickerCreate",
    "TickerResponse",
    "OrderBookCreate",
    "OrderBookResponse",
    "TradeCreate",
    "TradeResponse",
    "MarketMetricsCreate",
    "MarketMetricsResponse",
    "OnChainMetricsCreate",
    "OnChainMetricsResponse",
    "PaginationParams",
    "MarketDataQuery",
    "HealthCheckResponse",
    "WSMessage"
]

# app/api/__init__.py
"""API routes."""

# app/api/v1/__init__.py
"""API v1 routes."""

# app/collectors/__init__.py
"""Data collectors."""

from app.collectors.binance_collector import BinanceCollector
from app.collectors.coingecko_collector import CoinGeckoCollector
from app.collectors.onchain_collector import OnChainCollector

__all__ = [
    "BinanceCollector",
    "CoinGeckoCollector",
    "OnChainCollector"
]

# app/cache/__init__.py
"""Cache management."""

from app.cache.redis_cache import cache, RedisCache

__all__ = ["cache", "RedisCache"]

# app/utils/__init__.py
"""Utility functions."""

from app.utils.logger import setup_logging
from app.utils.rate_limiter import rate_limiter

__all__ = ["setup_logging", "rate_limiter"]

# tests/__init__.py
"""Test suite for crypto-data-engine."""

# alembic/versions/__init__.py
"""Database migrations."""