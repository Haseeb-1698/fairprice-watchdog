import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import Base
from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """
    Create all database tables before tests run and drop them after.
    This fixture runs automatically for all tests.
    """
    # Create async engine for test database
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Drop all tables after tests complete
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

# Made with Bob
