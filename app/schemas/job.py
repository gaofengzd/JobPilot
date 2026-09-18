"""A job retains its original input index."""

from typing import Self

from pydantic import Field, model_validator

from app.schemas.common import Contract, EvidenceRef, NonEmptyText, NonNegativeInt


class JobProfile(Contract):
    job_index: NonNegativeInt
    title: NonEmptyText
    company: NonEmptyText | None = None
    required_skills: list[NonEmptyText] = Field(default_factory=list)
    preferred_skills: list[NonEmptyText] = Field(default_factory=list)
    responsibilities: list[NonEmptyText] = Field(default_factory=list)
    education_requirement: NonEmptyText | None = None
    experience_requirement: NonEmptyText | None = None
    keywords: list[NonEmptyText] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def distinct_requirements(self) -> Self:
        required = [s.casefold() for s in self.required_skills]
        preferred = [s.casefold() for s in self.preferred_skills]
        if len(set(required)) != len(required) or len(set(preferred)) != len(preferred):
            raise ValueError("Duplicate skills must be normalized before validation")
        if set(required) & set(preferred):
            raise ValueError("Required and preferred skills must be disjoint")
        return self
