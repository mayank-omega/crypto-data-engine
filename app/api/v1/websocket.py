# See artifact: crypto_websocket
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Set, Dict
import asyncio
import json
import logging
from datetime import datetime

from app.api.deps import get_db_session
from app.models.market_data import Ticker, OHLCV, OrderBook
from app.cache.redis_cache import cache
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, channel: str):
        """Connect client to a channel."""
        await websocket.accept()
        async with self.lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)
        logger.info(f"Client connected to channel: {channel}")
    
    async def disconnect(self, websocket: WebSocket, channel: str):
        """Disconnect client from a channel."""
        async with self.lock:
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)
                if not self.active_connections[channel]:
                    del self.active_connections[channel]
        logger.info(f"Client disconnected from channel: {channel}")
    
    async def broadcast(self, channel: str, message: dict):
        """Broadcast message to all clients in a channel."""
        if channel not in self.active_connections:
            return
        
        # Create list to avoid modification during iteration
        connections = list(self.active_connections[channel])
        disconnected = []
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        if disconnected:
            async with self.lock:
                for conn in disconnected:
                    self.active_connections[channel].discard(conn)
    
    def get_connection_count(self, channel: str = None) -> int:
        """Get number of active connections."""
        if channel:
            return len(self.active_connections.get(channel, set()))
        return sum(len(conns) for conns in self.active_connections.values())


manager = ConnectionManager()


@router.websocket("/ws/ticker/{symbol}")
async def websocket_ticker(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time ticker updates.
    
    Args:
        websocket: WebSocket connection
        symbol: Trading symbol to subscribe to
    """
    channel = f"ticker:{symbol}"
    await manager.connect(websocket, channel)
    
    try:
        # Send initial data
        ticker_data = await cache.get(f"ticker:{symbol}")
        if ticker_data:
            await websocket.send_json({
                "type": "ticker",
                "data": ticker_data,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Keep connection alive and send updates
        while True:
            try:
                # Wait for client messages (ping/pong)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_HEARTBEAT_INTERVAL
                )
                
                # Handle client messages
                if data == "ping":
                    await websocket.send_text("pong")
                
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Check for updates in cache
            ticker_data = await cache.get(f"ticker:{symbol}")
            if ticker_data:
                await websocket.send_json({
                    "type": "ticker",
                    "data": ticker_data,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, channel)


@router.websocket("/ws/ohlcv/{symbol}/{timeframe}")
async def websocket_ohlcv(websocket: WebSocket, symbol: str, timeframe: str):
    """
    WebSocket endpoint for real-time OHLCV updates.
    
    Args:
        websocket: WebSocket connection
        symbol: Trading symbol
        timeframe: Candlestick timeframe
    """
    channel = f"ohlcv:{symbol}:{timeframe}"
    await manager.connect(websocket, channel)
    
    try:
        # Send initial data
        cache_key = f"ohlcv:{symbol}:{timeframe}:10"
        ohlcv_data = await cache.get(cache_key)
        if ohlcv_data:
            await websocket.send_json({
                "type": "ohlcv",
                "data": ohlcv_data,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_HEARTBEAT_INTERVAL
                )
                
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Check for updates
            ohlcv_data = await cache.get(cache_key)
            if ohlcv_data:
                await websocket.send_json({
                    "type": "ohlcv",
                    "data": ohlcv_data,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, channel)


@router.websocket("/ws/orderbook/{symbol}")
async def websocket_orderbook(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time order book updates.
    
    Args:
        websocket: WebSocket connection
        symbol: Trading symbol
    """
    channel = f"orderbook:{symbol}"
    await manager.connect(websocket, channel)
    
    try:
        # Send initial data
        orderbook_data = await cache.get(f"orderbook:{symbol}")
        if orderbook_data:
            await websocket.send_json({
                "type": "orderbook",
                "data": orderbook_data,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_HEARTBEAT_INTERVAL
                )
                
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Check for updates
            orderbook_data = await cache.get(f"orderbook:{symbol}")
            if orderbook_data:
                await websocket.send_json({
                    "type": "orderbook",
                    "data": orderbook_data,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, channel)


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection statistics."""
    return {
        "total_connections": manager.get_connection_count(),
        "channels": {
            channel: len(connections)
            for channel, connections in manager.active_connections.items()
        }
    }