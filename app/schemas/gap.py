"""Gaps are supported by JD evidence, not invented candidate facts."""

from typing import Literal

from pydantic import Field

from app.schemas.common import Contract, EvidenceRef, NonEmptyText


class SkillGap(Contract):
    skill: NonEmptyText
    requirement_type: Literal["required", "preferred"]
    reason: NonEmptyText
    evidence_status: Literal["not_mentioned", "insufficient"]
    jd_evidence: list[EvidenceRef] = Field(min_length=1)
    priority: int = Field(ge=1, le=3, strict=True)
