"""Transport-only API contracts; core business schemas remain unchanged."""

from pydantic import Field, model_validator

from app.schemas.batch import BatchStatistics
from app.schemas.candidate import CandidateProfile
from app.schemas.common import Contract, NonEmptyText, NonNegativeInt
from app.schemas.job import JobProfile
from app.schemas.match import MatchResult


class JobAnalyzeRequest(Contract):
    jd_text: NonEmptyText
    job_index: NonNegativeInt = 0


class JobBatchRequest(Contract):
    raw_jobs: list[NonEmptyText] = Field(min_length=1)
    candidate_profile: CandidateProfile


class JobBatchResponse(Contract):
    job_profiles: list[JobProfile]
    match_results: list[MatchResult]
    batch_statistics: BatchStatistics
    job_errors: dict[NonNegativeInt, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def indexes_are_consistent(self):
        jobs = {item.job_index for item in self.job_profiles}
        matches = {item.job_index for item in self.match_results}
        if jobs != matches:
            raise ValueError("Every parsed job must have one match result")
        if jobs & self.job_errors.keys():
            raise ValueError("Successful and failed job indexes must be disjoint")
        if self.batch_statistics.valid_jobs != len(jobs):
            raise ValueError("Batch statistics must match successful jobs")
        return self
