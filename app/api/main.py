"""FastAPI application factory and safe application error mapping."""

from collections.abc import Callable

from fastapi import FastAPI, Request
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


def create_app(
    services: ApiServices | None = None,
    *,
    services_factory: Callable[[], ApiServices] = build_default_services,
) -> FastAPI:
    application = FastAPI(title="JobPilot API", version="1.0.0")
    application.state.services = services
    application.state.services_factory = services_factory
    application.include_router(resume_router)
    application.include_router(jobs_router)
    application.include_router(agent_router)
    application.include_router(health_router)

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
