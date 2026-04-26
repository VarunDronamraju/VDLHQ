import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Bind request_id to structured logger for this request
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Log request start
        logger.info("Request started", method=request.method, url=str(request.url))

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
            )
            return response
        except Exception as e:
            logger.exception("Request failed", method=request.method, url=str(request.url), error=str(e))
            from app.core.error_logger import log_system_error
            from app.db.session import get_async_session

            async with get_async_session() as db:
                await log_system_error(db, "RequestLoggerMiddleware", None, e)
            raise
        finally:
            structlog.contextvars.clear_contextvars()
