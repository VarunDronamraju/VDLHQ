from fastapi import FastAPI, HTTPException

from app.db.connection import test_connection

app = FastAPI()


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
