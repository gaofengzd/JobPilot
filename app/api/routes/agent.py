"""Complete JobPilot workflow endpoint."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import ApiServices, get_services
from app.graph.state import create_initial_state
from app.schemas.input import AgentInput
from app.schemas.report import FinalReport

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=FinalReport)
def run_agent(
    payload: AgentInput,
    services: ApiServices = Depends(get_services),
) -> FinalReport:
    if len(payload.raw_jobs) > services.settings.max_jobs:
        raise HTTPException(
            status_code=422,
            detail=f"Batch exceeds max_jobs={services.settings.max_jobs}",
        )
    state = create_initial_state(
        resume_text=payload.resume_text,
        raw_jobs=payload.raw_jobs,
        selected_job_index=payload.selected_job_index,
        need_advice=payload.need_advice,
        max_jobs=services.settings.max_jobs,
    )
    result = services.workflow.invoke(state)
    return result["final_report"]
