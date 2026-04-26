from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.middlewares.request_logger import RequestLoggerMiddleware
from app.api.routes.auth import router as auth_router
from app.api.routes.client import router as client_router
from app.api.routes.intake import router as intake_router
from app.api.routes.ops import router as ops_router
from app.api.routes.workflow import router as workflow_router
from app.core.logging import setup_logging
from app.core.scheduler import start_scheduler, stop_scheduler
from app.db.connection import test_connection
from app.db.session import get_db

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await test_connection()
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


app = FastAPI(title="LocationHQ API", lifespan=lifespan)
app.add_middleware(RequestLoggerMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import structlog

    from app.core.error_logger import log_system_error
    from app.db.session import get_async_session

    logger = structlog.get_logger("global_exception_handler")
    logger.exception("Unhandled exception", url=str(request.url), error=str(exc))

    try:
        async with get_async_session() as db:
            await log_system_error(db, "GlobalExceptionHandler", None, exc)
    except Exception as inner_e:
        logger.error("Failed to log system error", error=str(inner_e))

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root():
    return {
        "status": "online",
        "system": "LocationHQ API",
        "version": "v1.0",
        "documentation": "/docs"
    }


app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(intake_router, prefix="/api/v1", tags=["intake"])
app.include_router(workflow_router, prefix="/api/v1", tags=["workflow"])
app.include_router(client_router, prefix="/api/v1/client", tags=["client"])
app.include_router(ops_router, prefix="/api/v1/ops", tags=["ops"])


@app.get("/health")
async def health_check(db=Depends(get_db)) -> dict:
    checks = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        await db.execute(text("SELECT vector_dims('[1,2,3]'::vector)"))
        checks["pgvector"] = "ok"
    except Exception:
        checks["pgvector"] = "unavailable"

    return {"status": "ok", "checks": checks}
