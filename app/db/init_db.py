import asyncio

from sqlalchemy import text

from app.db.connection import engine
from app.models import core as core_models  # Imported so SQLAlchemy model metadata is registered.
from app.models.base import Base

_ = core_models


async def init_db():
    print("Initializing database (Async)...")
    async with engine.begin() as conn:
        # 1. Enable pgvector extension
        print("Enabling pgvector extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        # 2. Drop existing tables
        print("Dropping existing tables...")
        await conn.run_sync(Base.metadata.drop_all)

        # 3. Create all tables
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)

        # 4. Create vector index
        print("Creating vector index on locations...")
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS idx_locations_embedding
            ON locations
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 50);
        """
            )
        )

    print("Database initialization complete.")


if __name__ == "__main__":
    asyncio.run(init_db())
