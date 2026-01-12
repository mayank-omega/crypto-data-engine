# See artifact: crypto_test_api
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import OHLCV, Ticker


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "database" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "version" in data


@pytest.mark.asyncio
async def test_get_ohlcv(client: AsyncClient, test_session: AsyncSession, sample_ohlcv_data):
    """Test GET OHLCV endpoint."""
    # Create test data
    ohlcv = OHLCV(**sample_ohlcv_data)
    test_session.add(ohlcv)
    await test_session.commit()
    
    # Test endpoint
    response = await client.get(f"/api/v1/market/ohlcv/{sample_ohlcv_data['symbol']}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["symbol"] == sample_ohlcv_data["symbol"]


@pytest.mark.asyncio
async def test_get_ohlcv_not_found(client: AsyncClient):
    """Test GET OHLCV endpoint with non-existent symbol."""
    response = await client.get("/api/v1/market/ohlcv/NONEXISTENT")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_ticker(client: AsyncClient, test_session: AsyncSession, sample_ticker_data):
    """Test GET ticker endpoint."""
    # Create test data
    ticker = Ticker(**sample_ticker_data)
    test_session.add(ticker)
    await test_session.commit()
    
    # Test endpoint
    response = await client.get(f"/api/v1/market/ticker/{sample_ticker_data['symbol']}")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == sample_ticker_data["symbol"]
    assert data["last_price"] == sample_ticker_data["last_price"]


@pytest.mark.asyncio
async def test_get_ticker_not_found(client: AsyncClient):
    """Test GET ticker endpoint with non-existent symbol."""
    response = await client.get("/api/v1/market/ticker/NONEXISTENT")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_all_tickers(client: AsyncClient, test_session: AsyncSession, sample_ticker_data):
    """Test GET all tickers endpoint."""
    # Create test data
    ticker = Ticker(**sample_ticker_data)
    test_session.add(ticker)
    await test_session.commit()
    
    # Test endpoint
    response = await client.get("/api/v1/market/tickers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_available_symbols(client: AsyncClient, test_session: AsyncSession, sample_ticker_data):
    """Test GET available symbols endpoint."""
    # Create test data
    ticker = Ticker(**sample_ticker_data)
    test_session.add(ticker)
    await test_session.commit()
    
    # Test endpoint
    response = await client.get("/api/v1/market/symbols")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert sample_ticker_data["symbol"] in data


@pytest.mark.asyncio
async def test_collectors_status(client: AsyncClient):
    """Test collectors status endpoint."""
    response = await client.get("/api/v1/collectors/status")
    assert response.status_code == 200
    data = response.json()
    assert "binance" in data
    assert "coingecko" in data
    assert "onchain" in data


@pytest.mark.asyncio
async def test_ohlcv_pagination(client: AsyncClient, test_session: AsyncSession, sample_ohlcv_data):
    """Test OHLCV pagination."""
    # Create multiple test records
    for i in range(10):
        ohlcv = OHLCV(**{**sample_ohlcv_data, "close": 50000.0 + i})
        test_session.add(ohlcv)
    await test_session.commit()
    
    # Test with limit
    response = await client.get(
        f"/api/v1/market/ohlcv/{sample_ohlcv_data['symbol']}?limit=5"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5