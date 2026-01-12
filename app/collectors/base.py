from abc import ABC, abstractmethod
import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseCollector(ABC):
    """Base class for all data collectors."""
    
    def __init__(self, name: str):
        """
        Initialize collector.
        
        Args:
            name: Collector name
        """
        self.name = name
        self.is_running = False
        self.collection_task: Optional[asyncio.Task] = None
        self.retry_count = 0
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY_SECONDS
        
        logger.info(f"Initialized {self.name} collector")
    
    @abstractmethod
    async def collect(self, db: AsyncSession, symbols: List[str]) -> int:
        """
        Collect data for given symbols.
        
        Args:
            db: Database session
            symbols: List of trading symbols
            
        Returns:
            Number of records collected
        """
        pass
    
    @abstractmethod
    async def collect_historical(
        self,
        db: AsyncSession,
        symbols: List[str],
        days: int = 365
    ) -> int:
        """
        Collect historical data.
        
        Args:
            db: Database session
            symbols: List of trading symbols
            days: Number of days to collect
            
        Returns:
            Number of records collected
        """
        pass
    
    async def start_collection_loop(
        self,
        db: AsyncSession,
        symbols: List[str],
        interval_seconds: Optional[int] = None
    ) -> None:
        """
        Start continuous data collection loop.
        
        Args:
            db: Database session
            symbols: List of trading symbols
            interval_seconds: Collection interval
        """
        if self.is_running:
            logger.warning(f"{self.name} collector already running")
            return
        
        self.is_running = True
        interval = interval_seconds or settings.COLLECTION_INTERVAL_SECONDS
        
        logger.info(f"Starting {self.name} collection loop (interval: {interval}s)")
        
        while self.is_running:
            try:
                records = await self.collect(db, symbols)
                logger.info(f"{self.name} collected {records} records")
                self.retry_count = 0
                
            except Exception as e:
                self.retry_count += 1
                logger.error(f"{self.name} collection error: {e}")
                
                if self.retry_count >= self.max_retries:
                    logger.error(f"{self.name} max retries reached, stopping")
                    self.is_running = False
                    break
                
                await asyncio.sleep(self.retry_delay)
                continue
            
            await asyncio.sleep(interval)
    
    async def stop_collection_loop(self) -> None:
        """Stop data collection loop."""
        if not self.is_running:
            logger.warning(f"{self.name} collector not running")
            return
        
        logger.info(f"Stopping {self.name} collection loop")
        self.is_running = False
        
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
    
    async def acquire_rate_limit(self, limiter_name: str) -> None:
        """
        Acquire rate limit permission.
        
        Args:
            limiter_name: Rate limiter name
        """
        await rate_limiter.acquire(limiter_name)
    
    def get_status(self) -> dict:
        """Get collector status."""
        return {
            "name": self.name,
            "is_running": self.is_running,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }