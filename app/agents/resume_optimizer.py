"""Create minimal resume wording suggestions from existing candidate evidence only."""

from app.business.matching_engine import match_key
from app.schemas.candidate import CandidateProfile
from app.schemas.gap import SkillGap
from app.schemas.job import JobProfile
from app.schemas.report import ResumeSuggestion
from app.utils.resume_files import normalize_text


class ResumeOptimizer:
    def optimize(
        self,
        candidate: CandidateProfile,
        job: JobProfile,
        gaps: list[SkillGap],
    ) -> list[ResumeSuggestion]:
        if not candidate.evidence:
            return []
        candidate_skills = {match_key(skill): skill for skill in candidate.skills}
        target_skills = job.required_skills + job.preferred_skills
        # Resolve each requirement to the candidate's own spelling once.  A JD
        # OCR artifact such as `Pos tman` then still finds `Postman` in the
        # resume, and the candidate wording is what gets quoted back, so the
        # suggestion never echoes a mangled JD spelling.
        supported: dict[str, str] = {}
        for skill in target_skills:
            candidate_skill = candidate_skills.get(match_key(skill))
            if candidate_skill is not None:
                supported.setdefault(match_key(skill), candidate_skill)
        if not supported:
            return []

        suggestions: list[ResumeSuggestion] = []
        used_quotes: set[str] = set()
        for item in candidate.evidence:
            mentioned = [
                candidate_skill
                for candidate_skill in supported.values()
                if normalize_text(candidate_skill) in normalize_text(item.quote)
            ]
            if not mentioned or normalize_text(item.quote) in used_quotes:
                continue
            used_quotes.add(normalize_text(item.quote))
            focus = ", ".join(mentioned)
            suggestions.append(
                ResumeSuggestion(
                    original_text=item.quote,
                    suggested_text=f"{item.quote} | 相关技能：{focus}",
                    reason="突出简历中有依据、且为岗位要求的技能；缺失的技能未作为经验展示。",
                    candidate_evidence=[item],
                    questions_to_confirm=["补充可量化成果前，请先与原始数据核实。"],
                )
            )
        return suggestions
