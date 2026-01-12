# See artifact: crypto_schemas
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any


class OHLCVBase(BaseModel):
    """Base OHLCV schema."""
    symbol: str
    exchange: str = "binance"
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: Optional[float] = None
    trades_count: Optional[int] = None


class OHLCVCreate(OHLCVBase):
    """Schema for creating OHLCV records."""
    pass


class OHLCVResponse(OHLCVBase):
    """Schema for OHLCV API responses."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class TickerBase(BaseModel):
    """Base ticker schema."""
    symbol: str
    exchange: str = "binance"
    timestamp: datetime
    last_price: float
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_volume: Optional[float] = None
    ask_volume: Optional[float] = None
    volume_24h: Optional[float] = None
    quote_volume_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_percent_24h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None


class TickerCreate(TickerBase):
    """Schema for creating ticker records."""
    pass


class TickerResponse(TickerBase):
    """Schema for ticker API responses."""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class OrderBookBase(BaseModel):
    """Base order book schema."""
    symbol: str
    exchange: str = "binance"
    timestamp: datetime
    bids: List[List[float]]  # [[price, volume], ...]
    asks: List[List[float]]  # [[price, volume], ...]
    bid_ask_spread: Optional[float] = None
    total_bid_volume: Optional[float] = None
    total_ask_volume: Optional[float] = None


class OrderBookCreate(OrderBookBase):
    """Schema for creating order book records."""
    pass


class OrderBookResponse(OrderBookBase):
    """Schema for order book API responses."""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TradeBase(BaseModel):
    """Base trade schema."""
    symbol: str
    exchange: str = "binance"
    trade_id: str
    timestamp: datetime
    price: float
    volume: float
    quote_volume: Optional[float] = None
    side: Optional[str] = None
    is_buyer_maker: Optional[bool] = None


class TradeCreate(TradeBase):
    """Schema for creating trade records."""
    pass


class TradeResponse(TradeBase):
    """Schema for trade API responses."""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MarketMetricsBase(BaseModel):
    """Base market metrics schema."""
    symbol: str
    timestamp: datetime
    market_cap: Optional[float] = None
    market_cap_rank: Optional[int] = None
    fully_diluted_valuation: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    developer_score: Optional[float] = None
    community_score: Optional[float] = None
    liquidity_score: Optional[float] = None
    public_interest_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class MarketMetricsCreate(MarketMetricsBase):
    """Schema for creating market metrics records."""
    pass


class MarketMetricsResponse(MarketMetricsBase):
    """Schema for market metrics API responses."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class OnChainMetricsBase(BaseModel):
    """Base on-chain metrics schema."""
    symbol: str
    blockchain: str
    timestamp: datetime
    active_addresses: Optional[int] = None
    transaction_count: Optional[int] = None
    transaction_volume: Optional[float] = None
    average_transaction_value: Optional[float] = None
    hash_rate: Optional[float] = None
    difficulty: Optional[float] = None
    block_height: Optional[int] = None
    fees_total: Optional[float] = None
    fees_mean: Optional[float] = None
    fees_median: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class OnChainMetricsCreate(OnChainMetricsBase):
    """Schema for creating on-chain metrics records."""
    pass


class OnChainMetricsResponse(OnChainMetricsBase):
    """Schema for on-chain metrics API responses."""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    """Pagination parameters."""
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


class MarketDataQuery(BaseModel):
    """Query parameters for market data."""
    symbol: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timeframe: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    database: str
    redis: str


class WSMessage(BaseModel):
    """WebSocket message format."""
    type: str  # ticker, ohlcv, orderbook, trade
    data: Dict[str, Any]
    timestamp: datetime