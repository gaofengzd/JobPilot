"""Day 5 grounded gaps and deterministic batch statistics."""

import pytest

from app.agents.gap_analyzer import GapAnalyzer
from app.business.batch_analyzer import BatchAnalyzer
from app.business.matching_engine import MatchingEngine
from app.core.exceptions import BatchAnalysisError, GapAnalysisError
from app.schemas.candidate import CandidateProfile
from app.schemas.common import EvidenceRef
from app.schemas.job import JobProfile
from app.schemas.match import MatchResult


def evidence(quote: str, line: int = 1) -> EvidenceRef:
    return EvidenceRef(source_id="job:sample", quote=quote, locator=f"line:{line}")


def job(
    index: int,
    required: list[str],
    preferred: list[str],
    *,
    with_evidence: bool = True,
) -> JobProfile:
    items = []
    if with_evidence:
        if required:
            items.append(evidence("Required skills: " + ", ".join(required)))
        if preferred:
            items.append(evidence("Preferred skills: " + ", ".join(preferred), 2))
    return JobProfile(
        job_index=index,
        title=f"Job {index}",
        required_skills=required,
        preferred_skills=preferred,
        evidence=items,
    )


def test_gap_analyzer_uses_match_partitions_and_jd_evidence():
    profile = job(2, ["Python", "SQL"], ["Docker"])
    match = MatchingEngine().match(CandidateProfile(skills=["Python"]), profile)

    gaps = GapAnalyzer().analyze(profile, match)

    assert [(gap.skill, gap.requirement_type, gap.priority) for gap in gaps] == [
        ("SQL", "required", 1),
        ("Docker", "preferred", 2),
    ]
    assert all(gap.evidence_status == "not_mentioned" for gap in gaps)
    assert gaps[0].jd_evidence[0].quote == "Required skills: Python, SQL"
    assert gaps[1].jd_evidence[0].quote == "Preferred skills: Docker"


def test_gap_evidence_lookup_preserves_the_original_alias_text():
    profile = job(0, ["Postgres"], [])
    match = MatchingEngine().match(CandidateProfile(), profile)
    assert GapAnalyzer().analyze(profile, match)[0].skill == "Postgres"


def test_gap_analyzer_returns_empty_when_no_skills_are_missing():
    profile = job(0, ["Python"], [])
    match = MatchingEngine().match(CandidateProfile(skills=["Python"]), profile)
    assert GapAnalyzer().analyze(profile, match) == []


def test_gap_analyzer_rejects_index_mismatch():
    profile = job(0, ["SQL"], [])
    match = MatchingEngine().match(CandidateProfile(), profile).model_copy(update={"job_index": 1})
    with pytest.raises(GapAnalysisError, match="indexes"):
        GapAnalyzer().analyze(profile, match)


def test_gap_analyzer_rejects_missing_jd_evidence():
    profile = job(0, ["SQL"], [], with_evidence=False)
    match = MatchingEngine().match(CandidateProfile(), profile)
    with pytest.raises(GapAnalysisError, match="lacks JD evidence"):
        GapAnalyzer().analyze(profile, match)


def test_gap_analyzer_rejects_skill_not_in_job_partition():
    profile = job(0, ["SQL"], [])
    match = MatchResult(
        job_index=0,
        missing_required_skills=["Docker"],
        required_skill_coverage=0,
        preferred_skill_coverage=0,
        project_similarity=0,
        project_similarity_available=False,
    )
    with pytest.raises(GapAnalysisError, match="absent"):
        GapAnalyzer().analyze(profile, match)


def test_batch_counts_each_canonical_skill_once_per_job_and_tracks_roles():
    jobs = [
        job(0, ["Python", "Python3", "SQL"], ["Docker"]),
        job(1, ["python"], ["SQL", "K8s"]),
        job(3, ["Kubernetes"], ["Docker"]),
    ]
    stats = BatchAnalyzer().analyze(CandidateProfile(skills=["PY", "Docker"]), jobs, total_jobs=4)

    assert (stats.total_jobs, stats.valid_jobs, stats.failed_jobs) == (4, 3, 1)
    by_skill = {item.skill: item for item in stats.frequencies}
    assert by_skill["Python"].model_dump() == {
        "skill": "Python",
        "required_count": 2,
        "preferred_count": 0,
        "any_count": 2,
        "ratio": pytest.approx(2 / 3),
        "candidate_has_evidence": True,
    }
    assert by_skill["SQL"].required_count == 1
    assert by_skill["SQL"].preferred_count == 1
    assert by_skill["SQL"].any_count == 2
    assert by_skill["K8s"].any_count == 2
    assert by_skill["K8s"].candidate_has_evidence is False
    assert stats.high_frequency_missing_skills == ["K8s", "SQL"]


def test_batch_sort_is_count_descending_then_case_insensitive_name():
    stats = BatchAnalyzer().analyze(
        CandidateProfile(),
        [job(0, ["Zoo", "alpha"], []), job(1, ["Zoo"], ["Beta"])],
        total_jobs=2,
    )
    assert [item.skill for item in stats.frequencies] == ["Zoo", "alpha", "Beta"]


def test_batch_zero_valid_jobs_keeps_explicit_failed_denominator():
    stats = BatchAnalyzer().analyze(CandidateProfile(), [], total_jobs=2)
    assert stats.valid_jobs == 0
    assert stats.failed_jobs == 2
    assert stats.frequencies == []
    assert stats.high_frequency_missing_skills == []


@pytest.mark.parametrize(
    ("jobs", "total_jobs"),
    [
        ([job(0, [], []), job(0, [], [])], 2),
        ([job(2, [], [])], 2),
        ([job(0, [], []), job(1, [], [])], 1),
    ],
)
def test_batch_rejects_inconsistent_job_counts(jobs, total_jobs):
    with pytest.raises(BatchAnalysisError):
        BatchAnalyzer().analyze(CandidateProfile(), jobs, total_jobs=total_jobs)


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_batch_rejects_invalid_threshold(threshold):
    with pytest.raises(BatchAnalysisError):
        BatchAnalyzer(threshold)
