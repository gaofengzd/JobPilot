"""A job retains its original input index."""

from typing import Self

from pydantic import Field, model_validator

from app.schemas.common import Contract, EvidenceRef, NonEmptyText, NonNegativeInt


class JobProfile(Contract):
    job_index: NonNegativeInt
    title: NonEmptyText
    company: NonEmptyText | None = None
    required_skills: list[NonEmptyText] = Field(
        default_factory=list,
        description=(
            "Atomic skill names the JD requires: a tool, technology, language, "
            "method, or standard such as Jmeter, LoadRunner, Postman, or Python. "
            "One entry per skill, copied verbatim from the JD. Never put a whole "
            "requirement clause here, never a standard number on its own, and "
            "never a sentence that reports what the candidate can do."
        ),
    )
    preferred_skills: list[NonEmptyText] = Field(
        default_factory=list,
        description=(
            "Atomic skill names the JD marks as a plus, using the same one name "
            "per entry rule as required_skills."
        ),
    )
    responsibilities: list[NonEmptyText] = Field(
        default_factory=list,
        description=(
            "What the job does, copied verbatim from the JD. Requirement clauses "
            "that describe an ability belong here, not in the skill lists."
        ),
    )
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
