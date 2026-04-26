from fastapi import FastAPI, HTTPException
from app.db.connection import test_connection
from app.api.routes.intake import router as intake_router
from app.api.routes.workflow import router as workflow_router

app = FastAPI(title="LocationHQ API")

app.include_router(intake_router, prefix="/api/v1", tags=["intake"])
app.include_router(workflow_router, prefix="/api/v1", tags=["workflow"])

@app.on_event("startup")
async def startup_event() -> None:
    await test_connection()

@app.get("/health")
async def health_check() -> dict[str, str]:
    try:
        await test_connection()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {exc}") from exc
    return {"status": "ok", "db": "connected"}
