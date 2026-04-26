import traceback
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import SystemError


async def log_system_error(
    db: AsyncSession,
    source: str,
    lead_id: Optional[UUID],
    error: Exception,
) -> None:
    """
    Persistence for pipeline or system failures.
    Ensures errors are logged to the DB for Ops visibility.
    """
    entry = SystemError(
        source=source,
        lead_id=lead_id,
        error_type=type(error).__name__,
        message=str(error),
        detail={"traceback": traceback.format_exc()},
    )
    db.add(entry)
    await db.commit()
