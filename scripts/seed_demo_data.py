import asyncio
import uuid
from app.db.connection import AsyncSessionLocal
from app.models.core import Location
from sqlalchemy import select

async def seed():
    async with AsyncSessionLocal() as db:
        # Check if default location exists
        default_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        res = await db.execute(select(Location).where(Location.id == default_id))
        if not res.scalar_one_or_none():
            print("Creating default location for demo...")
            loc = Location(
                id=default_id,
                name="Iconic Warehouse Studio",
                type="Industrial",
                address="123 Production Lane, London, E1 6QL",
                available=True,
                metadata_={"description": "Standard high-ceiling studio for demo purposes."}
            )
            db.add(loc)
            await db.commit()
            print("Default location created.")
        else:
            print("Default location already exists.")

if __name__ == "__main__":
    asyncio.run(seed())
