"""Validate computed values; this module does not compute a match score."""

import math
from typing import Self

from pydantic import Field, model_validator

from app.schemas.common import Contract, NonEmptyText, NonNegativeInt, Ratio


class MatchResult(Contract):
    job_index: NonNegativeInt
    matched_required_skills: list[NonEmptyText] = Field(default_factory=list)
    missing_required_skills: list[NonEmptyText] = Field(default_factory=list)
    matched_preferred_skills: list[NonEmptyText] = Field(default_factory=list)
    missing_preferred_skills: list[NonEmptyText] = Field(default_factory=list)
    required_skill_coverage: Ratio
    preferred_skill_coverage: Ratio
    project_similarity: Ratio
    evidence: list[NonEmptyText] = Field(default_factory=list)
    project_similarity_available: bool
    score: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    score_version: NonEmptyText = "1.0"

    @model_validator(mode="after")
    def check_partitions(self) -> Self:
        for kind in ("required", "preferred"):
            matched = [s.casefold() for s in getattr(self, f"matched_{kind}_skills")]
            missing = [s.casefold() for s in getattr(self, f"missing_{kind}_skills")]
            if len(set(matched)) != len(matched) or len(set(missing)) != len(missing):
                raise ValueError("Match lists must be deduplicated")
            if set(matched) & set(missing):
                raise ValueError("Matched and missing skills must be disjoint")
            total = len(matched) + len(missing)
            expected = len(matched) / total if total else 0.0
            if not math.isclose(getattr(self, f"{kind}_skill_coverage"), expected, abs_tol=1e-8):
                raise ValueError(f"{kind} coverage contradicts skill partitions")
        if not self.project_similarity_available and self.project_similarity != 0:
            raise ValueError("Unavailable project similarity must use 0.0")
        has_skills = any(
            (
                self.matched_required_skills,
                self.missing_required_skills,
                self.matched_preferred_skills,
                self.missing_preferred_skills,
            )
        )
        if not has_skills and not self.project_similarity_available and self.score is not None:
            raise ValueError("Score must be None when no dimension is available")
        return self
