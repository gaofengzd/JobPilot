"""Batch counts and denominators are explicit."""

import math
from typing import Self

from pydantic import Field, model_validator

from app.schemas.common import Contract, NonEmptyText, NonNegativeInt, Ratio


class SkillFrequency(Contract):
    skill: NonEmptyText
    required_count: NonNegativeInt
    preferred_count: NonNegativeInt
    any_count: NonNegativeInt
    ratio: Ratio
    candidate_has_evidence: bool

    @model_validator(mode="after")
    def union_bounds(self) -> Self:
        if (
            not max(self.required_count, self.preferred_count)
            <= self.any_count
            <= (self.required_count + self.preferred_count)
        ):
            raise ValueError("any_count must be the union count")
        return self


class BatchStatistics(Contract):
    total_jobs: NonNegativeInt
    valid_jobs: NonNegativeInt
    failed_jobs: NonNegativeInt
    frequencies: list[SkillFrequency] = Field(default_factory=list)
    high_frequency_missing_skills: list[NonEmptyText] = Field(default_factory=list)

    @model_validator(mode="after")
    def counts_and_ratios(self) -> Self:
        if self.valid_jobs + self.failed_jobs != self.total_jobs:
            raise ValueError("valid_jobs + failed_jobs must equal total_jobs")
        names = [f.skill.casefold() for f in self.frequencies]
        if len(names) != len(set(names)):
            raise ValueError("Frequency skills must be unique")
        for item in self.frequencies:
            if item.any_count > self.valid_jobs:
                raise ValueError("Skill counts exceed valid_jobs")
            expected = item.any_count / self.valid_jobs if self.valid_jobs else 0.0
            if not math.isclose(item.ratio, expected, abs_tol=1e-8):
                raise ValueError("Skill ratio must use valid_jobs as denominator")
        missing = [s.casefold() for s in self.high_frequency_missing_skills]
        possible = {f.skill.casefold() for f in self.frequencies if not f.candidate_has_evidence}
        if len(missing) != len(set(missing)) or not set(missing) <= possible:
            raise ValueError("Missing skills must be unique and lack candidate evidence")
        return self
