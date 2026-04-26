from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.db.connection import AsyncSessionLocal


async def get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_async_session():
    """
    Context manager for background tasks or standalone scripts.
    """
    async with AsyncSessionLocal() as session:
        yield session
