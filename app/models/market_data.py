# See artifact: crypto_models
from sqlalchemy import Column, String, Float, DateTime, Integer, Index, BigInteger, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base


class OHLCV(Base):
    """OHLCV (Open, High, Low, Close, Volume) candlestick data."""
    
    __tablename__ = "ohlcv"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, default="binance")
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    quote_volume = Column(Float)
    trades_count = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp', unique=True),
        Index('idx_timestamp_symbol', 'timestamp', 'symbol'),
    )


class Ticker(Base):
    """Real-time ticker data."""
    
    __tablename__ = "tickers"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, default="binance")
    
    timestamp = Column(DateTime, nullable=False, index=True)
    last_price = Column(Float, nullable=False)
    bid_price = Column(Float)
    ask_price = Column(Float)
    bid_volume = Column(Float)
    ask_volume = Column(Float)
    
    volume_24h = Column(Float)
    quote_volume_24h = Column(Float)
    price_change_24h = Column(Float)
    price_change_percent_24h = Column(Float)
    
    high_24h = Column(Float)
    low_24h = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )


class OrderBook(Base):
    """Order book snapshots."""
    
    __tablename__ = "order_books"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, default="binance")
    
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Store bids/asks as JSON
    bids = Column(JSONB, nullable=False)  # [[price, volume], ...]
    asks = Column(JSONB, nullable=False)  # [[price, volume], ...]
    
    # Aggregated metrics
    bid_ask_spread = Column(Float)
    total_bid_volume = Column(Float)
    total_ask_volume = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_orderbook_symbol_timestamp', 'symbol', 'timestamp'),
    )


class Trade(Base):
    """Individual trades."""
    
    __tablename__ = "trades"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(50), nullable=False, default="binance")
    
    trade_id = Column(String(100), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    quote_volume = Column(Float)
    
    side = Column(String(10))  # buy/sell
    is_buyer_maker = Column(Boolean)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_trade_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_trade_id', 'exchange', 'trade_id', unique=True),
    )


class MarketMetrics(Base):
    """Market-wide metrics and metadata."""
    
    __tablename__ = "market_metrics"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # CoinGecko data
    market_cap = Column(Float)
    market_cap_rank = Column(Integer)
    fully_diluted_valuation = Column(Float)
    circulating_supply = Column(Float)
    total_supply = Column(Float)
    max_supply = Column(Float)
    
    # Social metrics
    developer_score = Column(Float)
    community_score = Column(Float)
    liquidity_score = Column(Float)
    public_interest_score = Column(Float)
    
    # Additional metadata - RENAMED from 'metadata' to 'market_metadata'
    market_metadata = Column(JSONB)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_metrics_symbol_timestamp', 'symbol', 'timestamp'),
    )


class OnChainMetrics(Base):
    """On-chain blockchain metrics."""
    
    __tablename__ = "onchain_metrics"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    blockchain = Column(String(50), nullable=False)
    
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Network metrics
    active_addresses = Column(Integer)
    transaction_count = Column(Integer)
    transaction_volume = Column(Float)
    average_transaction_value = Column(Float)
    
    # Mining/Staking metrics
    hash_rate = Column(Float)
    difficulty = Column(Float)
    block_height = Column(Integer)
    
    # Economic metrics
    fees_total = Column(Float)
    fees_mean = Column(Float)
    fees_median = Column(Float)
    
    # Additional data - RENAMED from 'metadata' to 'chain_metadata'
    chain_metadata = Column(JSONB)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_onchain_symbol_timestamp', 'symbol', 'timestamp'),
    )


class DataCollectionStatus(Base):
    """Track data collection jobs and their status."""
    
    __tablename__ = "data_collection_status"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    collector_name = Column(String(100), nullable=False, index=True)
    symbol = Column(String(20), index=True)
    
    status = Column(String(20), nullable=False)  # running, completed, failed
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    
    records_collected = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Additional data - RENAMED from 'metadata' to 'collection_metadata'
    collection_metadata = Column(JSONB)
    
    __table_args__ = (
        Index('idx_collection_status', 'collector_name', 'status', 'started_at'),
    )