from typing import AsyncGenerator
from app.db.connection import AsyncSessionLocal

async def get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session
