from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status

from app.database import get_db
from app.cache.redis_cache import cache
from app.config import get_settings

settings = get_settings()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_db():
        yield session


async def get_cache():
    """Get cache dependency."""
    return cache


def verify_api_key(api_key: str = None) -> bool:
    """
    Verify API key for authenticated endpoints.
    
    Args:
        api_key: API key from request
        
    Returns:
        Verification status
        
    Raises:
        HTTPException: If API key is invalid
    """
    # In production, implement proper API key verification
    # This is a placeholder
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    return True