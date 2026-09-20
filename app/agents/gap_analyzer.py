"""Build deterministic, JD-grounded skill gaps from a match result."""

from typing import Literal

from app.business.matching_engine import normalize_skill
from app.core.exceptions import GapAnalysisError
from app.schemas.common import EvidenceRef
from app.schemas.gap import SkillGap
from app.schemas.job import JobProfile
from app.schemas.match import MatchResult
from app.utils.resume_files import normalize_text


class GapAnalyzer:
    """Translate missing match partitions into evidence-backed gaps."""

    def analyze(self, job: JobProfile, match: MatchResult) -> list[SkillGap]:
        if job.job_index != match.job_index:
            raise GapAnalysisError("Job and match indexes must be equal.")
        return self._build(
            job, match.missing_required_skills, "required", priority=1
        ) + self._build(job, match.missing_preferred_skills, "preferred", priority=2)

    @staticmethod
    def _build(
        job: JobProfile,
        missing_skills: list[str],
        requirement_type: Literal["required", "preferred"],
        *,
        priority: int,
    ) -> list[SkillGap]:
        requirements = {
            normalize_skill(skill): skill for skill in getattr(job, f"{requirement_type}_skills")
        }
        result: list[SkillGap] = []
        for skill in missing_skills:
            canonical = normalize_skill(skill)
            if canonical not in requirements:
                raise GapAnalysisError("Match contains a missing skill absent from the JD profile.")
            evidence = _evidence_for_skill(job.evidence, requirements[canonical])
            if not evidence:
                raise GapAnalysisError(f"Missing {requirement_type} skill lacks JD evidence.")
            result.append(
                SkillGap(
                    skill=requirements[canonical],
                    requirement_type=requirement_type,
                    reason=f"Resume does not mention this {requirement_type} JD skill.",
                    evidence_status="not_mentioned",
                    jd_evidence=evidence,
                    priority=priority,
                )
            )
        return result


def _evidence_for_skill(evidence: list[EvidenceRef], skill: str) -> list[EvidenceRef]:
    needle = normalize_text(skill)
    return [item for item in evidence if needle in normalize_text(item.quote)]
