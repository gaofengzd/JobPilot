"""Complete JobPilot workflow endpoint."""

import logging
from time import perf_counter

from fastapi import APIRouter, Depends

from app.api.dependencies import ApiServices, get_services
from app.core.logging import log_event
from app.graph.state import create_initial_state
from app.schemas.input import AgentInput
from app.schemas.report import FinalReport

logger = logging.getLogger("jobpilot")

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=FinalReport)
def run_agent(
    payload: AgentInput,
    services: ApiServices = Depends(get_services),
) -> FinalReport:
    state = create_initial_state(
        resume_text=payload.resume_text,
        raw_jobs=payload.raw_jobs,
        selected_job_index=payload.selected_job_index,
        need_advice=payload.need_advice,
    )
    started = perf_counter()
    log_event(
        logger,
        "workflow.started",
        request_id=state["request_id"],
        node="agent.run",
        status="running",
    )
    try:
        result = services.workflow.invoke(state)
    except Exception as exc:
        log_event(
            logger,
            "workflow.failed",
            level=logging.ERROR,
            request_id=state["request_id"],
            node="workflow",
            status="failed",
            duration_ms=round((perf_counter() - started) * 1000, 2),
            error_type=type(exc).__name__,
        )
        raise
    report = result["final_report"]
    log_event(
        logger,
        "workflow.completed",
        request_id=state["request_id"],
        node="workflow",
        status=report.status,
        duration_ms=round((perf_counter() - started) * 1000, 2),
    )
    return report
