# See artifact: crypto_conftest
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

from app.main import app
from app.database import Base, get_db
from app.config import get_settings
from app.cache.redis_cache import cache

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://cryptouser:cryptopass@localhost:5432/crypto_data_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    
    async def override_get_db():
        yield test_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_cache():
    """Setup test Redis cache."""
    # In production tests, you would connect to a test Redis instance
    # For now, we'll mock it
    yield cache


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing."""
    from datetime import datetime
    return {
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "timeframe": "1h",
        "timestamp": datetime.utcnow(),
        "open": 50000.0,
        "high": 51000.0,
        "low": 49500.0,
        "close": 50500.0,
        "volume": 1000.0,
        "quote_volume": 50000000.0,
        "trades_count": 5000
    }


@pytest.fixture
def sample_ticker_data():
    """Sample ticker data for testing."""
    from datetime import datetime
    return {
        "symbol": "BTCUSDT",
        "exchange": "binance",
        "timestamp": datetime.utcnow(),
        "last_price": 50500.0,
        "bid_price": 50499.0,
        "ask_price": 50501.0,
        "volume_24h": 10000.0,
        "price_change_24h": 500.0,
        "price_change_percent_24h": 1.0
    }