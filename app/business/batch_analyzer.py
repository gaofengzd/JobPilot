"""Deterministic skill frequencies across successfully parsed jobs."""

from collections import defaultdict

from app.business.matching_engine import normalize_skill
from app.core.exceptions import BatchAnalysisError
from app.schemas.batch import BatchStatistics, SkillFrequency
from app.schemas.candidate import CandidateProfile
from app.schemas.job import JobProfile

HIGH_FREQUENCY_THRESHOLD = 0.5


class BatchAnalyzer:
    def __init__(self, high_frequency_threshold: float = HIGH_FREQUENCY_THRESHOLD) -> None:
        if not 0 <= high_frequency_threshold <= 1:
            raise BatchAnalysisError("High-frequency threshold must be between 0 and 1.")
        self.high_frequency_threshold = high_frequency_threshold

    def analyze(
        self,
        candidate: CandidateProfile,
        jobs: list[JobProfile],
        *,
        total_jobs: int,
    ) -> BatchStatistics:
        if isinstance(total_jobs, bool) or not isinstance(total_jobs, int) or total_jobs < 0:
            raise BatchAnalysisError("total_jobs must be a non-negative integer.")
        if len(jobs) > total_jobs:
            raise BatchAnalysisError("Valid jobs cannot exceed total_jobs.")
        indexes = [job.job_index for job in jobs]
        if len(indexes) != len(set(indexes)):
            raise BatchAnalysisError("Valid job indexes must be unique.")
        if any(index >= total_jobs for index in indexes):
            raise BatchAnalysisError("Valid job index exceeds the batch input range.")

        required_counts: dict[str, int] = defaultdict(int)
        preferred_counts: dict[str, int] = defaultdict(int)
        any_counts: dict[str, int] = defaultdict(int)
        labels: dict[str, str] = {}
        for job in jobs:
            required = _skill_set(job.required_skills, labels)
            preferred = _skill_set(job.preferred_skills, labels)
            for skill in required:
                required_counts[skill] += 1
            for skill in preferred:
                preferred_counts[skill] += 1
            for skill in required | preferred:
                any_counts[skill] += 1

        candidate_skills = {normalize_skill(skill) for skill in candidate.skills}
        valid_jobs = len(jobs)
        frequencies = [
            SkillFrequency(
                skill=labels[skill],
                required_count=required_counts[skill],
                preferred_count=preferred_counts[skill],
                any_count=any_counts[skill],
                ratio=any_counts[skill] / valid_jobs if valid_jobs else 0.0,
                candidate_has_evidence=skill in candidate_skills,
            )
            for skill in any_counts
        ]
        frequencies.sort(key=lambda item: (-item.any_count, item.skill.casefold()))
        return BatchStatistics(
            total_jobs=total_jobs,
            valid_jobs=valid_jobs,
            failed_jobs=total_jobs - valid_jobs,
            frequencies=frequencies,
            high_frequency_missing_skills=[
                item.skill
                for item in frequencies
                if item.ratio >= self.high_frequency_threshold and not item.candidate_has_evidence
            ],
        )


def _skill_set(skills: list[str], labels: dict[str, str]) -> set[str]:
    result: set[str] = set()
    for skill in skills:
        canonical = normalize_skill(skill)
        labels.setdefault(canonical, skill)
        result.add(canonical)
    return result
