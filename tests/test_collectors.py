# See artifact: crypto_test_collectors
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.binance_collector import BinanceCollector
from app.collectors.coingecko_collector import CoinGeckoCollector
from app.collectors.onchain_collector import OnChainCollector


@pytest.mark.asyncio
async def test_binance_collector_init():
    """Test Binance collector initialization."""
    collector = BinanceCollector()
    assert collector.name == "BinanceCollector"
    assert collector.is_running == False
    assert collector.client is not None


@pytest.mark.asyncio
async def test_coingecko_collector_init():
    """Test CoinGecko collector initialization."""
    collector = CoinGeckoCollector()
    assert collector.name == "CoinGeckoCollector"
    assert collector.is_running == False
    assert len(collector.symbol_to_id) > 0


@pytest.mark.asyncio
async def test_onchain_collector_init():
    """Test OnChain collector initialization."""
    collector = OnChainCollector()
    assert collector.name == "OnChainCollector"
    assert collector.is_running == False
    assert len(collector.symbol_to_blockchain) > 0


@pytest.mark.asyncio
async def test_collector_status():
    """Test collector status method."""
    collector = BinanceCollector()
    status = collector.get_status()
    
    assert "name" in status
    assert "is_running" in status
    assert "retry_count" in status
    assert status["name"] == "BinanceCollector"
    assert status["is_running"] == False


@pytest.mark.asyncio
async def test_binance_collector_collect_mock(test_session: AsyncSession):
    """Test Binance collector with mocked data."""
    collector = BinanceCollector()
    
    # Mock the Binance client
    mock_ticker = {
        'symbol': 'BTCUSDT',
        'lastPrice': '50000.0',
        'bidPrice': '49999.0',
        'askPrice': '50001.0',
        'volume': '1000.0',
        'quoteVolume': '50000000.0',
        'priceChange': '500.0',
        'priceChangePercent': '1.0',
        'highPrice': '51000.0',
        'lowPrice': '49500.0'
    }
    
    with patch.object(collector.client, 'get_ticker', return_value=[mock_ticker]):
        records = await collector._collect_tickers(test_session, ["BTCUSDT"])
        assert records >= 0


@pytest.mark.asyncio
async def test_coingecko_symbol_mapping():
    """Test CoinGecko symbol to ID mapping."""
    collector = CoinGeckoCollector()
    
    assert collector.symbol_to_id.get("BTCUSDT") == "bitcoin"
    assert collector.symbol_to_id.get("ETHUSDT") == "ethereum"
    assert collector.symbol_to_id.get("NONEXISTENT") is None


@pytest.mark.asyncio
async def test_onchain_blockchain_mapping():
    """Test OnChain symbol to blockchain mapping."""
    collector = OnChainCollector()
    
    assert collector.symbol_to_blockchain.get("BTCUSDT") == "bitcoin"
    assert collector.symbol_to_blockchain.get("ETHUSDT") == "ethereum"
    assert collector.symbol_to_blockchain.get("NONEXISTENT") is None


@pytest.mark.asyncio
async def test_collector_rate_limiting():
    """Test collector rate limiting."""
    collector = BinanceCollector()
    
    # This should not raise an exception
    await collector.acquire_rate_limit("binance")


@pytest.mark.asyncio
async def test_binance_collector_stop():
    """Test stopping Binance collector."""
    collector = BinanceCollector()
    collector.is_running = True
    
    await collector.stop_collection_loop()
    assert collector.is_running == False