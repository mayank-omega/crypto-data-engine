import logging
from datetime import datetime, timedelta
from typing import List, Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from app.collectors.base import BaseCollector
from app.models.market_data import OHLCV, Ticker, OrderBook, Trade
from app.schemas.market_data import (
    OHLCVCreate, TickerCreate, OrderBookCreate, TradeCreate
)
from app.config import get_settings
from app.cache.redis_cache import cache

logger = logging.getLogger(__name__)
settings = get_settings()


class BinanceCollector(BaseCollector):
    """Collector for Binance exchange data."""
    
    def __init__(self):
        super().__init__("BinanceCollector")
        
        # Initialize Binance client
        self.client = Client(
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_API_SECRET,
            testnet=settings.BINANCE_TESTNET
        )
        
        self.timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        logger.info("Binance client initialized")
    
    async def collect(self, db: AsyncSession, symbols: List[str]) -> int:
        """
        Collect real-time data from Binance.
        
        Args:
            db: Database session
            symbols: List of trading symbols
            
        Returns:
            Number of records collected
        """
        total_records = 0
        
        try:
            # Collect tickers
            ticker_records = await self._collect_tickers(db, symbols)
            total_records += ticker_records
            
            # Collect order books
            orderbook_records = await self._collect_orderbooks(db, symbols)
            total_records += orderbook_records
            
            # Collect recent trades
            trade_records = await self._collect_trades(db, symbols)
            total_records += trade_records
            
            # Collect OHLCV for short timeframes
            ohlcv_records = await self._collect_ohlcv(db, symbols, ["1m", "5m"])
            total_records += ohlcv_records
            
            logger.info(f"Binance collected {total_records} records")
            
        except Exception as e:
            logger.error(f"Binance collection error: {e}")
            raise
        
        return total_records
    
    async def collect_historical(
        self,
        db: AsyncSession,
        symbols: List[str],
        days: int = 365
    ) -> int:
        """
        Collect historical OHLCV data from Binance.
        
        Args:
            db: Database session
            symbols: List of trading symbols
            days: Number of days to collect
            
        Returns:
            Number of records collected
        """
        total_records = 0
        
        try:
            for symbol in symbols:
                for timeframe in self.timeframes:
                    records = await self._collect_historical_ohlcv(
                        db, symbol, timeframe, days
                    )
                    total_records += records
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.5)
            
            logger.info(f"Binance historical collected {total_records} records")
            
        except Exception as e:
            logger.error(f"Binance historical collection error: {e}")
            raise
        
        return total_records
    
    async def _collect_tickers(
        self,
        db: AsyncSession,
        symbols: List[str]
    ) -> int:
        """Collect ticker data."""
        await self.acquire_rate_limit("binance")
        
        try:
            # Get 24h ticker data for all symbols
            tickers = await asyncio.to_thread(self.client.get_ticker)
            
            if not tickers:
                return 0
            
            # Filter for our symbols
            symbol_set = set(symbols)
            filtered_tickers = [t for t in tickers if t['symbol'] in symbol_set]
            
            # Store in database and cache
            records_created = 0
            for ticker_data in filtered_tickers:
                try:
                    ticker = Ticker(
                        symbol=ticker_data['symbol'],
                        exchange="binance",
                        timestamp=datetime.utcnow(),
                        last_price=float(ticker_data['lastPrice']),
                        bid_price=float(ticker_data['bidPrice']) if ticker_data.get('bidPrice') else None,
                        ask_price=float(ticker_data['askPrice']) if ticker_data.get('askPrice') else None,
                        volume_24h=float(ticker_data['volume']) if ticker_data.get('volume') else None,
                        quote_volume_24h=float(ticker_data['quoteVolume']) if ticker_data.get('quoteVolume') else None,
                        price_change_24h=float(ticker_data['priceChange']) if ticker_data.get('priceChange') else None,
                        price_change_percent_24h=float(ticker_data['priceChangePercent']) if ticker_data.get('priceChangePercent') else None,
                        high_24h=float(ticker_data['highPrice']) if ticker_data.get('highPrice') else None,
                        low_24h=float(ticker_data['lowPrice']) if ticker_data.get('lowPrice') else None,
                    )
                    db.add(ticker)
                    records_created += 1
                    
                    # Cache ticker data
                    cache_key = f"ticker:{ticker_data['symbol']}"
                    await cache.set(cache_key, {
                        "symbol": ticker_data['symbol'],
                        "price": float(ticker_data['lastPrice']),
                        "timestamp": datetime.utcnow().isoformat(),
                    }, ttl=60)
                    
                except Exception as e:
                    logger.error(f"Error processing ticker {ticker_data.get('symbol')}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"Stored {records_created} tickers")
            return records_created
            
        except BinanceAPIException as e:
            logger.error(f"Binance API error collecting tickers: {e}")
            return 0
    
    async def _collect_orderbooks(
        self,
        db: AsyncSession,
        symbols: List[str]
    ) -> int:
        """Collect order book data."""
        records_created = 0
        
        for symbol in symbols:
            try:
                await self.acquire_rate_limit("binance")
                
                # Get order book
                orderbook_data = await asyncio.to_thread(
                    self.client.get_order_book,
                    symbol=symbol,
                    limit=100
                )
                
                # Calculate metrics
                bids = [[float(price), float(qty)] for price, qty in orderbook_data['bids']]
                asks = [[float(price), float(qty)] for price, qty in orderbook_data['asks']]
                
                bid_ask_spread = asks[0][0] - bids[0][0] if bids and asks else None
                total_bid_volume = sum(bid[1] for bid in bids)
                total_ask_volume = sum(ask[1] for ask in asks)
                
                orderbook = OrderBook(
                    symbol=symbol,
                    exchange="binance",
                    timestamp=datetime.utcnow(),
                    bids=bids,
                    asks=asks,
                    bid_ask_spread=bid_ask_spread,
                    total_bid_volume=total_bid_volume,
                    total_ask_volume=total_ask_volume,
                )
                db.add(orderbook)
                records_created += 1
                
                # Cache order book
                cache_key = f"orderbook:{symbol}"
                await cache.set(cache_key, {
                    "symbol": symbol,
                    "bids": bids[:10],  # Top 10
                    "asks": asks[:10],
                    "spread": bid_ask_spread,
                    "timestamp": datetime.utcnow().isoformat(),
                }, ttl=30)
                
            except Exception as e:
                logger.error(f"Error collecting orderbook for {symbol}: {e}")
                continue
        
        await db.commit()
        return records_created
    
    async def _collect_trades(
        self,
        db: AsyncSession,
        symbols: List[str]
    ) -> int:
        """Collect recent trades."""
        records_created = 0
        
        for symbol in symbols:
            try:
                await self.acquire_rate_limit("binance")
                
                # Get recent trades
                trades_data = await asyncio.to_thread(
                    self.client.get_recent_trades,
                    symbol=symbol,
                    limit=100
                )
                
                for trade_data in trades_data:
                    try:
                        # Check if trade already exists
                        trade_id = str(trade_data['id'])
                        stmt = select(Trade).where(
                            Trade.exchange == "binance",
                            Trade.trade_id == trade_id
                        )
                        result = await db.execute(stmt)
                        existing = result.scalar_one_or_none()
                        
                        if existing:
                            continue
                        
                        trade = Trade(
                            symbol=symbol,
                            exchange="binance",
                            trade_id=trade_id,
                            timestamp=datetime.fromtimestamp(trade_data['time'] / 1000),
                            price=float(trade_data['price']),
                            volume=float(trade_data['qty']),
                            quote_volume=float(trade_data['quoteQty']) if 'quoteQty' in trade_data else None,
                            is_buyer_maker=trade_data.get('isBuyerMaker', False),
                        )
                        db.add(trade)
                        records_created += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing trade {trade_data.get('id')}: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"Error collecting trades for {symbol}: {e}")
                continue
        
        await db.commit()
        return records_created
    
    async def _collect_ohlcv(
        self,
        db: AsyncSession,
        symbols: List[str],
        timeframes: List[str]
    ) -> int:
        """Collect OHLCV data for specified timeframes."""
        records_created = 0
        
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    await self.acquire_rate_limit("binance")
                    
                    # Get klines (candlesticks)
                    klines = await asyncio.to_thread(
                        self.client.get_klines,
                        symbol=symbol,
                        interval=timeframe,
                        limit=10
                    )
                    
                    for kline in klines:
                        try:
                            timestamp = datetime.fromtimestamp(kline[0] / 1000)
                            
                            # Check if record exists
                            stmt = select(OHLCV).where(
                                OHLCV.symbol == symbol,
                                OHLCV.timeframe == timeframe,
                                OHLCV.timestamp == timestamp
                            )
                            result = await db.execute(stmt)
                            existing = result.scalar_one_or_none()
                            
                            if existing:
                                continue
                            
                            ohlcv = OHLCV(
                                symbol=symbol,
                                exchange="binance",
                                timeframe=timeframe,
                                timestamp=timestamp,
                                open=float(kline[1]),
                                high=float(kline[2]),
                                low=float(kline[3]),
                                close=float(kline[4]),
                                volume=float(kline[5]),
                                quote_volume=float(kline[7]),
                                trades_count=int(kline[8]),
                            )
                            db.add(ohlcv)
                            records_created += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing kline: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Error collecting OHLCV for {symbol} {timeframe}: {e}")
                    continue
        
        await db.commit()
        return records_created
    
    async def _collect_historical_ohlcv(
        self,
        db: AsyncSession,
        symbol: str,
        timeframe: str,
        days: int
    ) -> int:
        """Collect historical OHLCV data."""
        await self.acquire_rate_limit("binance")
        
        try:
            # Calculate start time
            start_time = datetime.utcnow() - timedelta(days=days)
            start_ms = int(start_time.timestamp() * 1000)
            
            # Get historical klines
            klines = await asyncio.to_thread(
                self.client.get_historical_klines,
                symbol=symbol,
                interval=timeframe,
                start_str=start_ms
            )
            
            records_created = 0
            for kline in klines:
                try:
                    timestamp = datetime.fromtimestamp(kline[0] / 1000)
                    
                    # Check if record exists
                    stmt = select(OHLCV).where(
                        OHLCV.symbol == symbol,
                        OHLCV.timeframe == timeframe,
                        OHLCV.timestamp == timestamp
                    )
                    result = await db.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        continue
                    
                    ohlcv = OHLCV(
                        symbol=symbol,
                        exchange="binance",
                        timeframe=timeframe,
                        timestamp=timestamp,
                        open=float(kline[1]),
                        high=float(kline[2]),
                        low=float(kline[3]),
                        close=float(kline[4]),
                        volume=float(kline[5]),
                        quote_volume=float(kline[7]),
                        trades_count=int(kline[8]),
                    )
                    db.add(ohlcv)
                    records_created += 1
                    
                except Exception as e:
                    logger.error(f"Error processing historical kline: {e}")
                    continue
            
            await db.commit()
            logger.info(f"Collected {records_created} historical records for {symbol} {timeframe}")
            return records_created
            
        except BinanceAPIException as e:
            logger.error(f"Binance API error collecting historical data: {e}")
            return 0