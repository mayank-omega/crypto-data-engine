from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional
from datetime import datetime

from app.api.deps import get_db_session, get_cache
from app.models.market_data import OHLCV, Ticker, OrderBook, Trade, MarketMetrics
from app.schemas.market_data import (
    OHLCVResponse, TickerResponse, OrderBookResponse,
    TradeResponse, MarketMetricsResponse
)
from app.cache.redis_cache import RedisCache

router = APIRouter()


@router.get("/ohlcv/{symbol}", response_model=List[OHLCVResponse])
async def get_ohlcv(
    symbol: str,
    timeframe: str = Query("1h", description="Timeframe (1m, 5m, 15m, 1h, 4h, 1d)"),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_cache)
):
    """
    Get OHLCV candlestick data for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        timeframe: Candlestick timeframe
        start_time: Start timestamp (optional)
        end_time: End timestamp (optional)
        limit: Maximum number of records
        
    Returns:
        List of OHLCV records
    """
    # Try cache first
    cache_key = f"ohlcv:{symbol}:{timeframe}:{limit}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Build query
    query = select(OHLCV).where(
        and_(
            OHLCV.symbol == symbol,
            OHLCV.timeframe == timeframe
        )
    )
    
    if start_time:
        query = query.where(OHLCV.timestamp >= start_time)
    if end_time:
        query = query.where(OHLCV.timestamp <= end_time)
    
    query = query.order_by(desc(OHLCV.timestamp)).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    ohlcv_data = result.scalars().all()
    
    if not ohlcv_data:
        raise HTTPException(status_code=404, detail=f"No OHLCV data found for {symbol}")
    
    # Convert to response models
    response = [OHLCVResponse.model_validate(item) for item in ohlcv_data]
    
    # Cache results
    await cache.set(cache_key, [r.model_dump() for r in response], ttl=60)
    
    return response


@router.get("/ticker/{symbol}", response_model=TickerResponse)
async def get_ticker(
    symbol: str,
    db: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_cache)
):
    """
    Get latest ticker data for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        
    Returns:
        Latest ticker data
    """
    # Try cache first
    cache_key = f"ticker:{symbol}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Query database
    query = select(Ticker).where(Ticker.symbol == symbol).order_by(desc(Ticker.timestamp)).limit(1)
    result = await db.execute(query)
    ticker = result.scalar_one_or_none()
    
    if not ticker:
        raise HTTPException(status_code=404, detail=f"No ticker data found for {symbol}")
    
    response = TickerResponse.model_validate(ticker)
    
    # Cache result
    await cache.set(cache_key, response.model_dump(), ttl=30)
    
    return response


@router.get("/tickers", response_model=List[TickerResponse])
async def get_all_tickers(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_cache)
):
    """
    Get latest tickers for all symbols.
    
    Args:
        limit: Maximum number of tickers
        
    Returns:
        List of latest tickers
    """
    # Try cache first
    cache_key = f"tickers:all:{limit}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Get latest ticker for each symbol
    # This query gets the most recent ticker for each unique symbol
    subquery = (
        select(
            Ticker.symbol,
            select(Ticker.id)
            .where(Ticker.symbol == Ticker.symbol)
            .order_by(desc(Ticker.timestamp))
            .limit(1)
            .correlate(Ticker)
            .scalar_subquery()
            .label("latest_id")
        )
        .distinct(Ticker.symbol)
        .subquery()
    )
    
    query = select(Ticker).where(Ticker.id.in_(
        select(subquery.c.latest_id)
    )).limit(limit)
    
    result = await db.execute(query)
    tickers = result.scalars().all()
    
    response = [TickerResponse.model_validate(t) for t in tickers]
    
    # Cache results
    await cache.set(cache_key, [r.model_dump() for r in response], ttl=30)
    
    return response


@router.get("/orderbook/{symbol}", response_model=OrderBookResponse)
async def get_orderbook(
    symbol: str,
    db: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_cache)
):
    """
    Get latest order book for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        
    Returns:
        Latest order book
    """
    # Try cache first
    cache_key = f"orderbook:{symbol}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Query database
    query = select(OrderBook).where(OrderBook.symbol == symbol).order_by(desc(OrderBook.timestamp)).limit(1)
    result = await db.execute(query)
    orderbook = result.scalar_one_or_none()
    
    if not orderbook:
        raise HTTPException(status_code=404, detail=f"No order book found for {symbol}")
    
    response = OrderBookResponse.model_validate(orderbook)
    
    # Cache result
    await cache.set(cache_key, response.model_dump(), ttl=15)
    
    return response


@router.get("/trades/{symbol}", response_model=List[TradeResponse])
async def get_trades(
    symbol: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get recent trades for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        start_time: Start timestamp (optional)
        end_time: End timestamp (optional)
        limit: Maximum number of trades
        
    Returns:
        List of trades
    """
    # Build query
    query = select(Trade).where(Trade.symbol == symbol)
    
    if start_time:
        query = query.where(Trade.timestamp >= start_time)
    if end_time:
        query = query.where(Trade.timestamp <= end_time)
    
    query = query.order_by(desc(Trade.timestamp)).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    trades = result.scalars().all()
    
    if not trades:
        raise HTTPException(status_code=404, detail=f"No trades found for {symbol}")
    
    return [TradeResponse.model_validate(t) for t in trades]


@router.get("/market-metrics/{symbol}", response_model=MarketMetricsResponse)
async def get_market_metrics(
    symbol: str,
    db: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_cache)
):
    """
    Get latest market metrics for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        
    Returns:
        Latest market metrics
    """
    # Try cache first
    cache_key = f"market_metrics:{symbol}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Query database
    query = select(MarketMetrics).where(MarketMetrics.symbol == symbol).order_by(desc(MarketMetrics.timestamp)).limit(1)
    result = await db.execute(query)
    metrics = result.scalar_one_or_none()
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No market metrics found for {symbol}")
    
    response = MarketMetricsResponse.model_validate(metrics)
    
    # Cache result
    await cache.set(cache_key, response.model_dump(), ttl=300)
    
    return response


@router.get("/symbols", response_model=List[str])
async def get_available_symbols(
    db: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_cache)
):
    """
    Get list of available trading symbols.
    
    Returns:
        List of symbols
    """
    # Try cache first
    cache_key = "available_symbols"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Query distinct symbols from tickers table
    query = select(Ticker.symbol).distinct()
    result = await db.execute(query)
    symbols = [row[0] for row in result.all()]
    
    if not symbols:
        return []
    
    # Cache results
    await cache.set(cache_key, symbols, ttl=3600)
    
    return symbols