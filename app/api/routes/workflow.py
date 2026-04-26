from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LHQException
from app.db.session import get_db
from app.models.core import Lead
from app.pipelines.intake_pipeline import run_intake_pipeline
from app.services.core.workflow_engine import WorkflowEngine

router = APIRouter()


@router.post("/leads/{lead_id}/transition")
async def transition_lead(lead_id: UUID, new_state: str, trigger: str, actor: str = "api", db: AsyncSession = Depends(get_db)):
    engine = WorkflowEngine(db)
    try:
        result = await engine.transition(lead_id=lead_id, target_state=new_state, trigger=trigger, actor=actor)
        await db.commit()
        return result
    except LHQException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error during transition")


@router.post("/internal/retry/{lead_id}")
async def retry_pipeline(lead_id: UUID, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Manually re-trigger the intake pipeline for a lead.
    """
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Lead not found")

    background_tasks.add_task(run_intake_pipeline, lead_id)
    return {"status": "retry_enqueued", "lead_id": str(lead_id)}
