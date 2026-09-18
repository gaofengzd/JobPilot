"""Report contracts and cross-object integrity, without generating advice."""

from typing import Literal, Self

from pydantic import Field, model_validator

from app.schemas.batch import BatchStatistics
from app.schemas.candidate import CandidateProfile
from app.schemas.common import Contract, EvidenceRef, NonEmptyText, NonNegativeInt
from app.schemas.gap import SkillGap
from app.schemas.job import JobProfile
from app.schemas.learning import LearningPlan, RetrievedDocument
from app.schemas.match import MatchResult


class ResumeSuggestion(Contract):
    original_text: NonEmptyText
    suggested_text: NonEmptyText
    reason: NonEmptyText
    candidate_evidence: list[EvidenceRef] = Field(min_length=1)
    questions_to_confirm: list[NonEmptyText] = Field(default_factory=list)


class FinalReport(Contract):
    request_id: NonEmptyText
    status: Literal["success", "partial", "failed"]
    candidate_profile: CandidateProfile | None = None
    job_profiles: list[JobProfile] = Field(default_factory=list)
    match_results: list[MatchResult] = Field(default_factory=list)
    selected_job_index: NonNegativeInt | None = None
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    retrieved_context: list[RetrievedDocument] = Field(default_factory=list)
    learning_plan: LearningPlan | None = None
    resume_suggestions: list[ResumeSuggestion] = Field(default_factory=list)
    batch_statistics: BatchStatistics | None = None
    job_errors: dict[NonNegativeInt, str] = Field(default_factory=dict)
    errors: list[NonEmptyText] = Field(default_factory=list)
    warnings: list[NonEmptyText] = Field(default_factory=list)
    schema_version: Literal["1.0"] = "1.0"

    @model_validator(mode="after")
    def references_are_consistent(self) -> Self:
        jobs = {job.job_index: job for job in self.job_profiles}
        indexes = [m.job_index for m in self.match_results]
        if len(jobs) != len(self.job_profiles) or len(set(indexes)) != len(indexes):
            raise ValueError("Job and match indexes must be unique")
        if not set(indexes) <= jobs.keys():
            raise ValueError("Match references an unknown job")
        if jobs.keys() & self.job_errors.keys():
            raise ValueError("Parsed jobs and parsing errors cannot share an index")
        for match in self.match_results:
            job = jobs[match.job_index]
            for kind in ("required", "preferred"):
                expected = {s.casefold() for s in getattr(job, f"{kind}_skills")}
                actual = {
                    s.casefold()
                    for s in (
                        getattr(match, f"matched_{kind}_skills")
                        + getattr(match, f"missing_{kind}_skills")
                    )
                }
                if actual != expected:
                    raise ValueError("Match partitions must cover the corresponding JD skills")
        detailed = bool(self.skill_gaps or self.learning_plan or self.resume_suggestions)
        if detailed and self.selected_job_index not in jobs:
            raise ValueError("Detail output needs a valid selected job")
        if self.learning_plan and self.learning_plan.job_index != self.selected_job_index:
            raise ValueError("Learning plan must belong to the selected job")
        chunks = [d.chunk_id for d in self.retrieved_context]
        if len(chunks) != len(set(chunks)):
            raise ValueError("Retrieved chunk IDs must be unique")
        if self.learning_plan:
            for task in self.learning_plan.tasks:
                if not set(task.source_chunk_ids) <= set(chunks):
                    raise ValueError("Learning task references an unknown chunk")
        if self.batch_statistics:
            batch = self.batch_statistics
            if batch.valid_jobs != len(jobs) or batch.failed_jobs != len(self.job_errors):
                raise ValueError("Batch counts must match report jobs and errors")
            if any(i >= batch.total_jobs for i in (*jobs, *self.job_errors)):
                raise ValueError("Job index exceeds batch input range")
        if self.status == "success":
            if self.candidate_profile is None or not jobs or set(indexes) != jobs.keys():
                raise ValueError("Success requires candidate, jobs and all matches")
            if self.errors or self.job_errors or self.selected_job_index not in jobs:
                raise ValueError("Success cannot contain errors or an invalid selection")
        return self
