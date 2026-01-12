import asyncio
import time
from typing import Dict
from collections import deque
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, rate: int, per: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            rate: Maximum number of requests
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        async with self.lock:
            current = time.time()
            time_passed = current - self.last_check
            self.last_check = current
            
            # Refill tokens
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            
            # Check if we have tokens
            if self.allowance < 1.0:
                sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                self.allowance = 0.0
            else:
                self.allowance -= 1.0


class SlidingWindowRateLimiter:
    """Sliding window rate limiter."""
    
    def __init__(self, max_requests: int, window_seconds: int = 60):
        """
        Initialize sliding window rate limiter.
        
        Args:
            max_requests: Maximum requests in window
            window_seconds: Window size in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        async with self.lock:
            now = time.time()
            
            # Remove old requests outside window
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()
            
            # Check if we can make request
            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest = self.requests[0]
                wait_time = (oldest + self.window_seconds) - now
                logger.warning(f"Rate limit reached, sleeping for {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                
                # Clean up again after sleep
                now = time.time()
                while self.requests and self.requests[0] < now - self.window_seconds:
                    self.requests.popleft()
            
            # Add current request
            self.requests.append(now)


class MultiRateLimiter:
    """Manage multiple rate limiters for different services."""
    
    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}
    
    def add_limiter(self, name: str, rate: int, per: int = 60) -> None:
        """
        Add a rate limiter.
        
        Args:
            name: Limiter name
            rate: Maximum requests
            per: Time period in seconds
        """
        self.limiters[name] = RateLimiter(rate, per)
        logger.info(f"Added rate limiter '{name}': {rate} requests per {per}s")
    
    async def acquire(self, name: str) -> None:
        """
        Acquire from named limiter.
        
        Args:
            name: Limiter name
        """
        if name not in self.limiters:
            logger.warning(f"Rate limiter '{name}' not found, creating default")
            self.add_limiter(name, 100, 60)
        
        await self.limiters[name].acquire()
    
    def get_limiter(self, name: str) -> RateLimiter:
        """Get limiter by name."""
        if name not in self.limiters:
            self.add_limiter(name, 100, 60)
        return self.limiters[name]


# Global rate limiter instance
rate_limiter = MultiRateLimiter()

# Add default limiters
rate_limiter.add_limiter("binance", 1200, 60)  # 1200 req/min
rate_limiter.add_limiter("coingecko", 50, 60)  # 50 req/min (free tier)
rate_limiter.add_limiter("onchain", 100, 60)  # 100 req/min