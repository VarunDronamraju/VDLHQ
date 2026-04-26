from fastapi import FastAPI, HTTPException

from app.db.connection import test_connection

from app.api.routes.intake import router as intake_router

app = FastAPI()

app.include_router(intake_router, prefix="/api/v1", tags=["intake"])


@app.on_event("startup")
def startup_event() -> None:
    test_connection()


@app.get("/health")
def health_check() -> dict[str, str]:
    try:
        test_connection()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {exc}") from exc
    return {"status": "ok", "db": "connected"}
