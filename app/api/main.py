"""FastAPI application factory and safe application error mapping."""

import logging
from collections.abc import Callable
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.dependencies import ApiServices, build_default_services
from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.resume import router as resume_router
from app.core.exceptions import (
    BatchAnalysisError,
    ConfigurationError,
    GapAnalysisError,
    JobGroundingError,
    JobPilotError,
    MatchCalculationError,
    ModelCallError,
    ResumeGroundingError,
    ResumeReadError,
    RetrievalError,
    StructuredOutputError,
)
from app.core.logging import configure_logging, log_event

logger = configure_logging()


def create_app(
    services: ApiServices | None = None,
    *,
    services_factory: Callable[[], ApiServices] = build_default_services,
) -> FastAPI:
    application = FastAPI(title="JobPilot API", version="1.0.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.state.services = services
    application.state.services_factory = services_factory
    application.include_router(resume_router)
    application.include_router(jobs_router)
    application.include_router(agent_router)
    application.include_router(health_router)

    @application.middleware("http")
    async def request_logging(request: Request, call_next):
        started = perf_counter()
        request_id = request.headers.get("x-request-id", "")[:64] or None
        try:
            response = await call_next(request)
        except Exception as exc:
            log_event(
                logger,
                "api.request.failed",
                level=logging.ERROR,
                request_id=request_id,
                node=request.url.path,
                status="failed",
                duration_ms=round((perf_counter() - started) * 1000, 2),
                error_type=type(exc).__name__,
            )
            raise
        log_event(
            logger,
            "api.request.completed",
            request_id=request_id,
            node=request.url.path,
            status="success" if response.status_code < 400 else "failed",
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return response

    @application.exception_handler(JobPilotError)
    async def handle_jobpilot_error(_request: Request, exc: JobPilotError) -> JSONResponse:
        status = _status_for(exc)
        return JSONResponse(
            status_code=status,
            content={
                "detail": {
                    "code": type(exc).__name__,
                    "message": str(exc),
                }
            },
        )

    return application


def _status_for(exc: JobPilotError) -> int:
    if isinstance(exc, ConfigurationError):
        return 503
    if isinstance(exc, ResumeReadError):
        return 413 if "exceeds the 5 MB" in str(exc) else 400
    if isinstance(
        exc,
        (ModelCallError, StructuredOutputError, ResumeGroundingError, JobGroundingError),
    ):
        return 502
    if isinstance(
        exc,
        (MatchCalculationError, GapAnalysisError, BatchAnalysisError, RetrievalError),
    ):
        return 500
    return 400


app = create_app()
