"""Single and batch job analysis endpoints."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.api.contracts import JobAnalyzeRequest, JobBatchRequest, JobBatchResponse
from app.api.dependencies import ApiServices, get_services
from app.core.exceptions import JobPilotError
from app.schemas.job import JobProfile

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/analyze", response_model=JobProfile)
def analyze_job(
    payload: JobAnalyzeRequest,
    services: ApiServices = Depends(get_services),
) -> JobProfile:
    return services.jd_analyzer.analyze(
        payload.jd_text,
        job_index=payload.job_index,
        source_id=f"job:{payload.job_index}",
        request_id=str(uuid4()),
    )


@router.post("/batch", response_model=JobBatchResponse)
def analyze_batch(
    payload: JobBatchRequest,
    services: ApiServices = Depends(get_services),
) -> JobBatchResponse:
    if len(payload.raw_jobs) > services.settings.max_jobs:
        raise HTTPException(
            status_code=422,
            detail=f"Batch exceeds max_jobs={services.settings.max_jobs}",
        )
    request_id = str(uuid4())
    jobs = []
    errors: dict[int, str] = {}
    for index, text in enumerate(payload.raw_jobs):
        try:
            jobs.append(
                services.jd_analyzer.analyze(
                    text,
                    job_index=index,
                    source_id=f"job:{index}",
                    request_id=request_id,
                )
            )
        except JobPilotError as exc:
            errors[index] = str(exc)
    matches = [services.matching_engine.match(payload.candidate_profile, job) for job in jobs]
    statistics = services.batch_analyzer.analyze(
        payload.candidate_profile,
        jobs,
        total_jobs=len(payload.raw_jobs),
    )
    return JobBatchResponse(
        job_profiles=jobs,
        match_results=matches,
        batch_statistics=statistics,
        job_errors=errors,
    )
