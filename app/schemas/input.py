"""Request validation; filesystem paths are internal-only."""

from typing import Self

from pydantic import Field, model_validator

from app.schemas.common import Contract, NonEmptyText, NonNegativeInt


class AgentInput(Contract):
    resume_text: NonEmptyText
    raw_jobs: list[NonEmptyText] = Field(min_length=1)
    selected_job_index: NonNegativeInt = 0
    need_advice: bool = True

    @model_validator(mode="after")
    def selected_job_exists(self) -> Self:
        if self.selected_job_index >= len(self.raw_jobs):
            raise ValueError("selected_job_index exceeds raw_jobs")
        return self


class InternalInput(Contract):
    resume_path: NonEmptyText | None = None
    resume_text: NonEmptyText | None = None
    raw_jobs: list[NonEmptyText] = Field(min_length=1)
    selected_job_index: NonNegativeInt = 0
    need_advice: bool = True

    @model_validator(mode="after")
    def source_and_selection(self) -> Self:
        if (self.resume_path is None) == (self.resume_text is None):
            raise ValueError("Provide exactly one of resume_path or resume_text")
        if self.selected_job_index >= len(self.raw_jobs):
            raise ValueError("selected_job_index exceeds raw_jobs")
        return self
