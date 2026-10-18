"""Build deterministic, JD-grounded skill gaps from a match result."""

from typing import Literal

from app.business.matching_engine import match_key
from app.core.exceptions import GapAnalysisError
from app.schemas.common import EvidenceRef
from app.schemas.gap import SkillGap
from app.schemas.job import JobProfile
from app.schemas.match import MatchResult
from app.utils.resume_files import mentions_term, normalize_text


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
            match_key(skill): skill for skill in getattr(job, f"{requirement_type}_skills")
        }
        result: list[SkillGap] = []
        for skill in missing_skills:
            canonical = match_key(skill)
            if canonical not in requirements:
                raise GapAnalysisError("Match contains a missing skill absent from the JD profile.")
            evidence = _evidence_for_skill(job.evidence, requirements[canonical])
            if not evidence:
                raise GapAnalysisError(f"Missing {requirement_type} skill lacks JD evidence.")
            label = "必需" if requirement_type == "required" else "加分"
            result.append(
                SkillGap(
                    skill=requirements[canonical],
                    requirement_type=requirement_type,
                    reason=f"简历中未提及该岗位{label}技能。",
                    evidence_status="not_mentioned",
                    jd_evidence=evidence,
                    priority=priority,
                )
            )
        return result


def _evidence_for_skill(evidence: list[EvidenceRef], skill: str) -> list[EvidenceRef]:
    """Return the quotes that support ``skill``.

    ``mentions_term`` is the predicate the Reflection validator uses, so matching
    with it keeps attachment and validation consistent -- a gap can no longer be
    attached by a lenient test and then rejected by a stricter one, which is what
    drove the repair loop into ``finalize_reflection_failure``.

    The plain normalized substring test is kept as a fallback.  It only widens
    which quote counts as support, so the "lacks JD evidence" contract keeps its
    previous reach and can never fail on a quote it accepted before.
    """
    strict = [item for item in evidence if mentions_term(item.quote, skill)]
    if strict:
        return strict
    needle = normalize_text(skill)
    return [item for item in evidence if needle in normalize_text(item.quote)]
