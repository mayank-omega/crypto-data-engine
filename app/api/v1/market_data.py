# See artifact: crypto_api_market_data
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

# Add these endpoints to the END of your app/api/v1/market_data.py file

from datetime import timedelta
from fastapi.responses import StreamingResponse
import csv
from io import StringIO


@router.get("/ticker/{symbol}/latest")
async def get_latest_ticker(
    symbol: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get latest ticker for a symbol (simplified version).
    
    Args:
        symbol: Trading symbol (e.g., BTCUSDT)
        
    Returns:
        Latest ticker data in simple format
    """
    query = select(Ticker).where(
        Ticker.symbol == symbol
    ).order_by(desc(Ticker.timestamp)).limit(1)
    
    result = await db.execute(query)
    ticker = result.scalar_one_or_none()
    
    if not ticker:
        return {"error": "No data found"}
    
    return {
        "symbol": ticker.symbol,
        "price": float(ticker.last_price) if ticker.last_price else None,
        "bid": float(ticker.bid_price) if ticker.bid_price else None,
        "ask": float(ticker.ask_price) if ticker.ask_price else None,
        "volume_24h": float(ticker.volume_24h) if ticker.volume_24h else None,
        "change_24h": float(ticker.price_change_percent_24h) if ticker.price_change_percent_24h else None,
        "high_24h": float(ticker.high_24h) if ticker.high_24h else None,
        "low_24h": float(ticker.low_24h) if ticker.low_24h else None,
        "timestamp": ticker.timestamp.isoformat()
    }


@router.get("/trades/{symbol}/recent")
async def get_recent_trades(
    symbol: str,
    limit: int = Query(default=50, le=500),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get recent trades for a symbol (simplified version).
    
    Args:
        symbol: Trading symbol
        limit: Maximum number of trades
        
    Returns:
        List of recent trades
    """
    query = select(Trade).where(
        Trade.symbol == symbol
    ).order_by(desc(Trade.timestamp)).limit(limit)
    
    result = await db.execute(query)
    trades = result.scalars().all()
    
    return {
        "symbol": symbol,
        "count": len(trades),
        "trades": [
            {
                "timestamp": t.timestamp.isoformat(),
                "price": float(t.price) if t.price else None,
                "volume": float(t.volume) if t.volume else None,
                "is_buy": not t.is_buyer_maker if t.is_buyer_maker is not None else None
            }
            for t in trades
        ]
    }


@router.get("/analytics/{symbol}/summary")
async def get_symbol_summary(
    symbol: str,
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive summary for a symbol.
    
    Args:
        symbol: Trading symbol
        hours: Hours to look back (default 24, max 168)
        
    Returns:
        Comprehensive symbol summary
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Get latest ticker
    ticker_query = select(Ticker).where(
        Ticker.symbol == symbol
    ).order_by(desc(Ticker.timestamp)).limit(1)
    ticker_result = await db.execute(ticker_query)
    ticker = ticker_result.scalar_one_or_none()
    
    # Get trade volume
    trades_query = select(Trade).where(
        and_(Trade.symbol == symbol, Trade.timestamp >= cutoff_time)
    )
    trades_result = await db.execute(trades_query)
    trades = trades_result.scalars().all()
    
    # Calculate metrics
    total_volume = sum(float(t.volume) for t in trades if t.volume)
    buy_volume = sum(float(t.volume) for t in trades if t.volume and not t.is_buyer_maker)
    sell_volume = total_volume - buy_volume
    
    # Get price range
    prices = [float(t.price) for t in trades if t.price]
    price_high = max(prices) if prices else None
    price_low = min(prices) if prices else None
    
    return {
        "symbol": symbol,
        "current_price": float(ticker.last_price) if ticker and ticker.last_price else None,
        "price_change_24h": float(ticker.price_change_percent_24h) if ticker and ticker.price_change_percent_24h else None,
        "volume_24h": float(ticker.volume_24h) if ticker and ticker.volume_24h else None,
        f"trades_last_{hours}h": len(trades),
        f"volume_last_{hours}h": total_volume,
        f"high_last_{hours}h": price_high,
        f"low_last_{hours}h": price_low,
        "buy_sell_ratio": buy_volume / sell_volume if sell_volume > 0 else None,
        "buy_pressure": (buy_volume / total_volume * 100) if total_volume > 0 else None,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/export/{symbol}/csv")
async def export_to_csv(
    symbol: str,
    timeframe: str = Query(default="1h", description="Timeframe"),
    days: int = Query(default=7, ge=1, le=365),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Export OHLCV data to CSV file.
    
    Args:
        symbol: Trading symbol
        timeframe: Candlestick timeframe
        days: Number of days to export
        
    Returns:
        CSV file download
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    query = select(OHLCV).where(
        and_(
            OHLCV.symbol == symbol,
            OHLCV.timeframe == timeframe,
            OHLCV.timestamp >= cutoff
        )
    ).order_by(OHLCV.timestamp)
    
    result = await db.execute(query)
    data = result.scalars().all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'trades_count'])
    
    for d in data:
        writer.writerow([
            d.timestamp.isoformat(),
            float(d.open) if d.open else '',
            float(d.high) if d.high else '',
            float(d.low) if d.low else '',
            float(d.close) if d.close else '',
            float(d.volume) if d.volume else '',
            float(d.quote_volume) if d.quote_volume else '',
            d.trades_count if d.trades_count else ''
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={symbol}_{timeframe}_{days}d.csv"
        }
    )


@router.get("/compare")
async def compare_symbols(
    symbols: str = Query(..., description="Comma-separated symbols (e.g., BTCUSDT,ETHUSDT)"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Compare multiple symbols side by side.
    
    Args:
        symbols: Comma-separated list of symbols
        
    Returns:
        Comparison data for symbols
    """
    symbol_list = [s.strip().upper() for s in symbols.split(',')]
    
    results = []
    for symbol in symbol_list:
        query = select(Ticker).where(
            Ticker.symbol == symbol
        ).order_by(desc(Ticker.timestamp)).limit(1)
        
        result = await db.execute(query)
        ticker = result.scalar_one_or_none()
        
        if ticker:
            results.append({
                "symbol": symbol,
                "price": float(ticker.last_price) if ticker.last_price else None,
                "change_24h": float(ticker.price_change_percent_24h) if ticker.price_change_percent_24h else None,
                "volume_24h": float(ticker.volume_24h) if ticker.volume_24h else None,
                "timestamp": ticker.timestamp.isoformat()
            })
    
    return {
        "count": len(results),
        "symbols": results,
        "timestamp": datetime.utcnow().isoformat()
    }