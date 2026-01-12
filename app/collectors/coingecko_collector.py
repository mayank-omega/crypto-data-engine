import logging
from datetime import datetime, timedelta
from typing import List, Dict
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.collectors.base import BaseCollector
from app.models.market_data import MarketMetrics
from app.config import get_settings
from app.cache.redis_cache import cache

logger = logging.getLogger(__name__)
settings = get_settings()


class CoinGeckoCollector(BaseCollector):
    """Collector for CoinGecko market data."""
    
    def __init__(self):
        super().__init__("CoinGeckoCollector")
        
        self.base_url = "https://api.coingecko.com/api/v3"
        self.headers = {}
        
        if settings.COINGECKO_API_KEY:
            self.headers["x-cg-pro-api-key"] = settings.COINGECKO_API_KEY
        
        # Symbol to CoinGecko ID mapping
        self.symbol_to_id = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum",
            "BNBUSDT": "binancecoin",
            "ADAUSDT": "cardano",
            "DOGEUSDT": "dogecoin",
            "XRPUSDT": "ripple",
            "DOTUSDT": "polkadot",
            "UNIUSDT": "uniswap",
            "LINKUSDT": "chainlink",
            "LTCUSDT": "litecoin",
            "SOLUSDT": "solana",
            "MATICUSDT": "matic-network",
            "AVAXUSDT": "avalanche-2",
        }
        
        logger.info("CoinGecko client initialized")
    
    async def collect(self, db: AsyncSession, symbols: List[str]) -> int:
        """
        Collect market metrics from CoinGecko.
        
        Args:
            db: Database session
            symbols: List of trading symbols
            
        Returns:
            Number of records collected
        """
        total_records = 0
        
        try:
            # Get coin IDs for symbols
            coin_ids = [self.symbol_to_id.get(s) for s in symbols if s in self.symbol_to_id]
            
            if not coin_ids:
                logger.warning("No valid CoinGecko coin IDs found for symbols")
                return 0
            
            # Collect market data for each coin
            for coin_id in coin_ids:
                try:
                    metrics = await self._collect_coin_metrics(db, coin_id)
                    if metrics:
                        total_records += 1
                    
                except Exception as e:
                    logger.error(f"Error collecting metrics for {coin_id}: {e}")
                    continue
            
            logger.info(f"CoinGecko collected {total_records} records")
            
        except Exception as e:
            logger.error(f"CoinGecko collection error: {e}")
            raise
        
        return total_records
    
    async def collect_historical(
        self,
        db: AsyncSession,
        symbols: List[str],
        days: int = 365
    ) -> int:
        """
        CoinGecko free tier doesn't support bulk historical data.
        This method is a placeholder for pro tier implementation.
        
        Args:
            db: Database session
            symbols: List of trading symbols
            days: Number of days to collect
            
        Returns:
            Number of records collected
        """
        logger.info("CoinGecko historical collection not implemented for free tier")
        return 0
    
    async def _collect_coin_metrics(
        self,
        db: AsyncSession,
        coin_id: str
    ) -> bool:
        """Collect detailed metrics for a coin."""
        await self.acquire_rate_limit("coingecko")
        
        try:
            async with httpx.AsyncClient() as client:
                # Get coin data
                response = await client.get(
                    f"{self.base_url}/coins/{coin_id}",
                    headers=self.headers,
                    params={
                        "localization": "false",
                        "tickers": "false",
                        "market_data": "true",
                        "community_data": "true",
                        "developer_data": "true",
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"CoinGecko API error: {response.status_code}")
                    return False
                
                data = response.json()
                
                # Extract market data
                market_data = data.get("market_data", {})
                community_data = data.get("community_data", {})
                developer_data = data.get("developer_data", {})
                
                # Find symbol for this coin
                symbol = None
                for sym, cid in self.symbol_to_id.items():
                    if cid == coin_id:
                        symbol = sym
                        break
                
                if not symbol:
                    logger.warning(f"No symbol found for coin_id {coin_id}")
                    return False
                
                # Create metrics record
                metrics = MarketMetrics(
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    market_cap=market_data.get("market_cap", {}).get("usd"),
                    market_cap_rank=data.get("market_cap_rank"),
                    fully_diluted_valuation=market_data.get("fully_diluted_valuation", {}).get("usd"),
                    circulating_supply=market_data.get("circulating_supply"),
                    total_supply=market_data.get("total_supply"),
                    max_supply=market_data.get("max_supply"),
                    developer_score=data.get("developer_score"),
                    community_score=data.get("community_score"),
                    liquidity_score=data.get("liquidity_score"),
                    public_interest_score=data.get("public_interest_score"),
                    metadata={
                        "ath": market_data.get("ath", {}).get("usd"),
                        "ath_date": market_data.get("ath_date", {}).get("usd"),
                        "atl": market_data.get("atl", {}).get("usd"),
                        "atl_date": market_data.get("atl_date", {}).get("usd"),
                        "twitter_followers": community_data.get("twitter_followers"),
                        "reddit_subscribers": community_data.get("reddit_subscribers"),
                        "github_stars": developer_data.get("stars"),
                        "github_forks": developer_data.get("forks"),
                    }
                )
                
                db.add(metrics)
                await db.commit()
                
                # Cache metrics
                cache_key = f"market_metrics:{symbol}"
                await cache.set(cache_key, {
                    "symbol": symbol,
                    "market_cap": metrics.market_cap,
                    "market_cap_rank": metrics.market_cap_rank,
                    "timestamp": datetime.utcnow().isoformat(),
                }, ttl=300)
                
                logger.info(f"Collected CoinGecko metrics for {symbol}")
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error collecting CoinGecko data for {coin_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error collecting CoinGecko data for {coin_id}: {e}")
            return False
    
    async def get_trending_coins(self) -> List[Dict]:
        """Get trending coins from CoinGecko."""
        await self.acquire_rate_limit("coingecko")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search/trending",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"CoinGecko trending API error: {response.status_code}")
                    return []
                
                data = response.json()
                coins = data.get("coins", [])
                
                trending = []
                for item in coins:
                    coin = item.get("item", {})
                    trending.append({
                        "id": coin.get("id"),
                        "name": coin.get("name"),
                        "symbol": coin.get("symbol"),
                        "market_cap_rank": coin.get("market_cap_rank"),
                        "price_btc": coin.get("price_btc"),
                    })
                
                # Cache trending
                await cache.set("trending_coins", trending, ttl=3600)
                
                return trending
                
        except Exception as e:
            logger.error(f"Error getting trending coins: {e}")
            return []
    
    async def get_global_market_data(self) -> Dict:
        """Get global cryptocurrency market data."""
        await self.acquire_rate_limit("coingecko")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/global",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"CoinGecko global API error: {response.status_code}")
                    return {}
                
                data = response.json()
                global_data = data.get("data", {})
                
                result = {
                    "total_market_cap": global_data.get("total_market_cap", {}).get("usd"),
                    "total_volume": global_data.get("total_volume", {}).get("usd"),
                    "market_cap_percentage": global_data.get("market_cap_percentage", {}),
                    "active_cryptocurrencies": global_data.get("active_cryptocurrencies"),
                    "markets": global_data.get("markets"),
                    "market_cap_change_percentage_24h": global_data.get("market_cap_change_percentage_24h_usd"),
                }
                
                # Cache global data
                await cache.set("global_market_data", result, ttl=300)
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting global market data: {e}")
            return {}