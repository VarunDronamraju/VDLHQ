from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from app.db.connection import test_connection
from app.api.routes.intake import router as intake_router
from app.api.routes.workflow import router as workflow_router
from app.core.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await test_connection()
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()

app = FastAPI(title="LocationHQ API", lifespan=lifespan)

app.include_router(intake_router, prefix="/api/v1", tags=["intake"])
app.include_router(workflow_router, prefix="/api/v1", tags=["workflow"])

@app.get("/health")
async def health_check() -> dict:
    try:
        await test_connection()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {exc}") from exc
    return {"status": "ok", "db": "connected"}
