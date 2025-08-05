import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from contextlib import asynccontextmanager
import os

try:
    from backend.config import settings
    from backend.models.database_models import Base
except ImportError:
    from config import settings
    from models.database_models import Base

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing database connections and operations"""

    def __init__(self):
        self.engine = None
        self.async_session_maker = None
        self._initialized = False

    async def initialize(self):
        """Initialize the database connection"""
        if self._initialized:
            return

        try:
            database_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)

            if database_url.startswith("postgresql://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+asyncpg://", 1)

            # Create async engine
            self.engine = create_async_engine(
                database_url,
                echo=False,
                poolclass=NullPool,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            # Create async session maker
            self.async_session_maker = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Test the connection
            async with self.engine.begin() as conn:
                await conn.run_sync(lambda sync_conn: None)

            self._initialized = True
            logger.info("Database service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing database service: {str(e)}")
            raise

    async def create_tables(self):
        """Create all database tables"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session"""
        if not self._initialized:
            await self.initialize()

        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self):
        """Close the database connection"""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connection closed")

    async def health_check(self) -> bool:
        """Check if database is healthy"""
        try:
            if not self._initialized:
                await self.initialize()

            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False


database_service = DatabaseService()
