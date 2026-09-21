"""Complete workflow state shared by the Day 7 LangGraph nodes."""

from typing import Literal, TypedDict
from uuid import uuid4

from app.schemas.batch import BatchStatistics
from app.schemas.candidate import CandidateProfile
from app.schemas.gap import SkillGap
from app.schemas.input import InternalInput
from app.schemas.job import JobProfile
from app.schemas.learning import LearningPlan, RetrievedDocument
from app.schemas.match import MatchResult
from app.schemas.report import FinalReport, ResumeSuggestion


class JobPilotState(TypedDict):
    resume_path: str | None
    resume_text: str | None
    raw_jobs: list[str]
    candidate_profile: CandidateProfile | None
    job_profiles: list[JobProfile]
    match_results: list[MatchResult]
    selected_job_index: int | None
    skill_gaps: list[SkillGap]
    retrieved_context: list[RetrievedDocument]
    learning_plan: LearningPlan | None
    resume_suggestions: list[ResumeSuggestion]
    batch_statistics: BatchStatistics | None
    final_report: FinalReport | None
    errors: list[str]
    retry_count: int
    request_id: str
    status: Literal["running", "success", "partial", "failed"]
    job_errors: dict[int, str]
    repair_target: str | None
    validation_issues: list[str]
    need_advice: bool


def create_initial_state(
    *,
    raw_jobs: list[str],
    resume_text: str | None = None,
    resume_path: str | None = None,
    selected_job_index: int = 0,
    need_advice: bool = True,
    max_jobs: int = 20,
) -> JobPilotState:
    if not 1 <= max_jobs <= 20:
        raise ValueError("max_jobs must be between 1 and 20")
    validated = InternalInput(
        resume_path=resume_path,
        resume_text=resume_text,
        raw_jobs=raw_jobs,
        selected_job_index=selected_job_index,
        need_advice=need_advice,
    )
    if len(validated.raw_jobs) > max_jobs:
        raise ValueError(f"Batch exceeds max_jobs={max_jobs}")
    return JobPilotState(
        resume_path=validated.resume_path,
        resume_text=validated.resume_text,
        raw_jobs=list(validated.raw_jobs),
        candidate_profile=None,
        job_profiles=[],
        match_results=[],
        selected_job_index=validated.selected_job_index,
        skill_gaps=[],
        retrieved_context=[],
        learning_plan=None,
        resume_suggestions=[],
        batch_statistics=None,
        final_report=None,
        errors=[],
        retry_count=0,
        request_id=str(uuid4()),
        status="running",
        job_errors={},
        repair_target=None,
        validation_issues=[],
        need_advice=validated.need_advice,
    )
