# See artifact: crypto_migration
"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-01-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create OHLCV table
    op.create_table('ohlcv',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('exchange', sa.String(length=50), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False),
        sa.Column('quote_volume', sa.Float(), nullable=True),
        sa.Column('trades_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_symbol_timeframe_timestamp', 'ohlcv', ['symbol', 'timeframe', 'timestamp'], unique=True)
    op.create_index('idx_timestamp_symbol', 'ohlcv', ['timestamp', 'symbol'])
    op.create_index(op.f('ix_ohlcv_symbol'), 'ohlcv', ['symbol'])
    op.create_index(op.f('ix_ohlcv_timestamp'), 'ohlcv', ['timestamp'])

    # Create Tickers table
    op.create_table('tickers',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('exchange', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('last_price', sa.Float(), nullable=False),
        sa.Column('bid_price', sa.Float(), nullable=True),
        sa.Column('ask_price', sa.Float(), nullable=True),
        sa.Column('bid_volume', sa.Float(), nullable=True),
        sa.Column('ask_volume', sa.Float(), nullable=True),
        sa.Column('volume_24h', sa.Float(), nullable=True),
        sa.Column('quote_volume_24h', sa.Float(), nullable=True),
        sa.Column('price_change_24h', sa.Float(), nullable=True),
        sa.Column('price_change_percent_24h', sa.Float(), nullable=True),
        sa.Column('high_24h', sa.Float(), nullable=True),
        sa.Column('low_24h', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_symbol_timestamp', 'tickers', ['symbol', 'timestamp'])
    op.create_index(op.f('ix_tickers_symbol'), 'tickers', ['symbol'])
    op.create_index(op.f('ix_tickers_timestamp'), 'tickers', ['timestamp'])

    # Create OrderBooks table
    op.create_table('order_books',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('exchange', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('bids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('asks', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('bid_ask_spread', sa.Float(), nullable=True),
        sa.Column('total_bid_volume', sa.Float(), nullable=True),
        sa.Column('total_ask_volume', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_orderbook_symbol_timestamp', 'order_books', ['symbol', 'timestamp'])
    op.create_index(op.f('ix_order_books_symbol'), 'order_books', ['symbol'])
    op.create_index(op.f('ix_order_books_timestamp'), 'order_books', ['timestamp'])

    # Create Trades table
    op.create_table('trades',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('exchange', sa.String(length=50), nullable=False),
        sa.Column('trade_id', sa.String(length=100), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False),
        sa.Column('quote_volume', sa.Float(), nullable=True),
        sa.Column('side', sa.String(length=10), nullable=True),
        sa.Column('is_buyer_maker', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_trade_id', 'trades', ['exchange', 'trade_id'], unique=True)
    op.create_index('idx_trade_symbol_timestamp', 'trades', ['symbol', 'timestamp'])
    op.create_index(op.f('ix_trades_symbol'), 'trades', ['symbol'])
    op.create_index(op.f('ix_trades_timestamp'), 'trades', ['timestamp'])

    # Create MarketMetrics table
    op.create_table('market_metrics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('market_cap_rank', sa.Integer(), nullable=True),
        sa.Column('fully_diluted_valuation', sa.Float(), nullable=True),
        sa.Column('circulating_supply', sa.Float(), nullable=True),
        sa.Column('total_supply', sa.Float(), nullable=True),
        sa.Column('max_supply', sa.Float(), nullable=True),
        sa.Column('developer_score', sa.Float(), nullable=True),
        sa.Column('community_score', sa.Float(), nullable=True),
        sa.Column('liquidity_score', sa.Float(), nullable=True),
        sa.Column('public_interest_score', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_metrics_symbol_timestamp', 'market_metrics', ['symbol', 'timestamp'])
    op.create_index(op.f('ix_market_metrics_symbol'), 'market_metrics', ['symbol'])
    op.create_index(op.f('ix_market_metrics_timestamp'), 'market_metrics', ['timestamp'])

    # Create OnChainMetrics table
    op.create_table('onchain_metrics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('blockchain', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('active_addresses', sa.Integer(), nullable=True),
        sa.Column('transaction_count', sa.Integer(), nullable=True),
        sa.Column('transaction_volume', sa.Float(), nullable=True),
        sa.Column('average_transaction_value', sa.Float(), nullable=True),
        sa.Column('hash_rate', sa.Float(), nullable=True),
        sa.Column('difficulty', sa.Float(), nullable=True),
        sa.Column('block_height', sa.Integer(), nullable=True),
        sa.Column('fees_total', sa.Float(), nullable=True),
        sa.Column('fees_mean', sa.Float(), nullable=True),
        sa.Column('fees_median', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_onchain_symbol_timestamp', 'onchain_metrics', ['symbol', 'timestamp'])
    op.create_index(op.f('ix_onchain_metrics_symbol'), 'onchain_metrics', ['symbol'])
    op.create_index(op.f('ix_onchain_metrics_timestamp'), 'onchain_metrics', ['timestamp'])

    # Create DataCollectionStatus table
    op.create_table('data_collection_status',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('collector_name', sa.String(length=100), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('records_collected', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_collection_status', 'data_collection_status', ['collector_name', 'status', 'started_at'])
    op.create_index(op.f('ix_data_collection_status_collector_name'), 'data_collection_status', ['collector_name'])
    op.create_index(op.f('ix_data_collection_status_symbol'), 'data_collection_status', ['symbol'])


def downgrade() -> None:
    op.drop_table('data_collection_status')
    op.drop_table('onchain_metrics')
    op.drop_table('market_metrics')
    op.drop_table('trades')
    op.drop_table('order_books')
    op.drop_table('tickers')
    op.drop_table('ohlcv')