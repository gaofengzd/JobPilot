"""Create minimal resume wording suggestions from existing candidate evidence only."""

from app.business.matching_engine import normalize_skill
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
        candidate_skills = {normalize_skill(skill): skill for skill in candidate.skills}
        target_skills = job.required_skills + job.preferred_skills
        supported = [skill for skill in target_skills if normalize_skill(skill) in candidate_skills]
        if not supported:
            return []

        suggestions: list[ResumeSuggestion] = []
        used_quotes: set[str] = set()
        for item in candidate.evidence:
            mentioned = [
                skill
                for skill in supported
                if normalize_text(candidate_skills[normalize_skill(skill)])
                in normalize_text(item.quote)
            ]
            if not mentioned or normalize_text(item.quote) in used_quotes:
                continue
            used_quotes.add(normalize_text(item.quote))
            focus = ", ".join(mentioned)
            suggestions.append(
                ResumeSuggestion(
                    original_text=item.quote,
                    suggested_text=f"{item.quote} | Relevant skills: {focus}",
                    reason=(
                        "Highlight resume-supported skills required by the job; "
                        "missing skills were not presented as experience."
                    ),
                    candidate_evidence=[item],
                    questions_to_confirm=[
                        "Add a measurable result only after confirming the source data."
                    ],
                )
            )
        return suggestions
