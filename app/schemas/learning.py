"""Retrieval and learning contracts; retrieval scores are not probabilities."""

from pydantic import Field

from app.schemas.common import Contract, NonEmptyText, NonNegativeInt


class RetrievedDocument(Contract):
    doc_id: NonEmptyText
    chunk_id: NonEmptyText
    content: NonEmptyText
    source: NonEmptyText
    score: float | None = Field(default=None, allow_inf_nan=False)


class LearningTask(Contract):
    skill: NonEmptyText
    priority: int = Field(ge=1, le=3, strict=True)
    objective: NonEmptyText
    actions: list[NonEmptyText] = Field(min_length=1)
    deliverable: NonEmptyText
    source_chunk_ids: list[NonEmptyText] = Field(min_length=1)
    estimated_hours: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class LearningPlan(Contract):
    job_index: NonNegativeInt
    tasks: list[LearningTask] = Field(default_factory=list)
    warnings: list[NonEmptyText] = Field(default_factory=list)
