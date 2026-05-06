from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

# Aiven requires SSL: ?ssl=require in the URL
engine = create_async_engine(
    settings.database_url,
    pool_size=10,          # Tuned for concurrent scheduler + API traffic (max 20 connections)
    max_overflow=10,       # Allow burst to 20 total connections
    pool_recycle=1800,     # Recycle connections every 30 min — Aiven may close idle connections
    pool_pre_ping=True,    # Detect stale connections from Aiven
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI dependency for database sessions."""
    async with async_session() as session:
        yield session
