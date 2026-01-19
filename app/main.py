from fastapi import FastAPI, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Optional

from app.config import get_settings
from app.database import init_db, close_db
from app.cache.redis_cache import cache
from app.utils.logger import setup_logging
from app.api.v1 import market_data, websocket
from app.collectors.binance_collector import BinanceCollector
from app.collectors.coingecko_collector import CoinGeckoCollector
from app.collectors.onchain_collector import OnChainCollector

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize collectors
binance_collector = BinanceCollector()
coingecko_collector = CoinGeckoCollector()
onchain_collector = OnChainCollector()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting crypto-data-engine...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Connect to Redis
        await cache.connect()
        logger.info("Redis connected")
        
        logger.info("Application started successfully")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down crypto-data-engine...")
    
    try:
        # Stop collectors
        await binance_collector.stop_collection_loop()
        await coingecko_collector.stop_collection_loop()
        await onchain_collector.stop_collection_loop()
        
        # Close connections
        await cache.disconnect()
        await close_db()
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade crypto market data collection engine",
    lifespan=lifespan
)

# Serve static files
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/dashboard")
async def dashboard():
    """Serve the dashboard HTML"""
    return FileResponse("app/static/dashboard.html")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Include routers
app.include_router(
    market_data.router,
    prefix=f"{settings.API_V1_PREFIX}/market",
    tags=["Market Data"]
)
app.include_router(
    websocket.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["WebSocket"]
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database
        db_status = "healthy"
        try:
            from app.database import engine
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
            logger.error(f"Database health check failed: {e}")
        
        # Check Redis
        redis_status = "healthy"
        try:
            await cache.redis_client.ping()
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
            logger.error(f"Redis health check failed: {e}")
        
        return {
            "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.APP_VERSION,
            "database": db_status,
            "redis": redis_status,
            "collectors": {
                "binance": binance_collector.get_status(),
                "coingecko": coingecko_collector.get_status(),
                "onchain": onchain_collector.get_status(),
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs"
    }


# Collector management endpoints
@app.post("/api/v1/collectors/start")
async def start_collectors(symbols: Optional[list[str]] = Body(None)):
    """Start data collectors."""
    # Use symbols from request body, or fall back to settings, or use default
    if symbols is None:
        symbols = settings.symbols_list  # Use from config
    
    # Log what symbols we're using
    logger.info(f"Starting collectors with symbols: {symbols}")
    
    try:
        # Start collectors in background
        import asyncio
        from app.database import async_session_factory
        
        async def run_collectors():
            async with async_session_factory() as session:
                # Start Binance collector
                asyncio.create_task(
                    binance_collector.start_collection_loop(session, symbols)
                )
                
                # Start CoinGecko collector
                asyncio.create_task(
                    coingecko_collector.start_collection_loop(session, symbols, interval_seconds=300)
                )
                
                # Start OnChain collector
                asyncio.create_task(
                    onchain_collector.start_collection_loop(session, symbols, interval_seconds=600)
                )
        
        asyncio.create_task(run_collectors())
        
        return {
            "status": "success",
            "message": "Collectors started",
            "symbols": symbols,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting collectors: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/api/v1/collectors/stop")
async def stop_collectors():
    """Stop data collectors."""
    try:
        await binance_collector.stop_collection_loop()
        await coingecko_collector.stop_collection_loop()
        await onchain_collector.stop_collection_loop()
        
        return {
            "status": "success",
            "message": "Collectors stopped",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error stopping collectors: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/api/v1/collectors/status")
async def get_collectors_status():
    """Get status of all collectors."""
    return {
        "binance": binance_collector.get_status(),
        "coingecko": coingecko_collector.get_status(),
        "onchain": onchain_collector.get_status(),
        "timestamp": datetime.utcnow().isoformat()
    }


# Metrics endpoint
if settings.ENABLE_METRICS:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response
    
    request_count = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
    request_duration = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"])
    
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        """Metrics collection middleware."""
        import time
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        return response
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )