from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.core.workflow_engine import WorkflowEngine
from app.core.exceptions import LHQException

router = APIRouter()

@router.post("/leads/{lead_id}/transition")
async def transition_lead(
    lead_id: UUID, 
    new_state: str, 
    trigger: str, 
    actor: str = "api",
    db: AsyncSession = Depends(get_db)
):
    engine = WorkflowEngine(db)
    try:
        result = await engine.transition(
            lead_id=lead_id,
            target_state=new_state,
            trigger=trigger,
            actor=actor
        )
        return result
    except LHQException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error during transition")
