import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

def _load_env_file() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

def _normalize_postgres_url(url: str) -> str:
    # Convert to asyncpg for Async SQLAlchemy
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    # asyncpg parameter normalization
    if "sslmode=" in url:
        # replace sslmode=require with ssl=require or similar
        # For simplicity, we'll just handle the common 'require'
        url = url.replace("sslmode=require", "ssl=require")
        url = url.replace("sslmode=disable", "ssl=disable")
    
    # Strip parameters asyncpg doesn't support
    unsupported_params = ["channel_binding=require", "channel_binding=disable", "channel_binding=prefer"]
    for param in unsupported_params:
        if param in url:
            url = url.replace(param, "")
    
    # Clean up trailing ? or &
    url = url.rstrip("&").rstrip("?")
    url = url.replace("?&", "?").replace("&&", "&")
    
    return url

_load_env_file()

raw_postgres_url = os.getenv("POSTGRES_URL")
if not raw_postgres_url:
    raise RuntimeError("POSTGRES_URL is not set")

DATABASE_URL = _normalize_postgres_url(raw_postgres_url)

# create_async_engine for async I/O
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

# AsyncSession for database operations
AsyncSessionLocal = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def test_connection() -> bool:
    from sqlalchemy import text
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True
