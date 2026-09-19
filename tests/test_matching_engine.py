"""Day 4 deterministic matching tests."""

import json
import math
from pathlib import Path

import pytest

from app.business.matching_engine import MatchingEngine, normalize_skill
from app.core.exceptions import MatchCalculationError
from app.schemas.candidate import CandidateProfile, Project
from app.schemas.job import JobProfile
from app.services.embedding import HashingEmbeddingClient

CASES_PATH = Path(__file__).parents[1] / "eval" / "datasets" / "matching_cases.json"


class StaticEmbedding:
    model_id = "static-test-v1"

    def __init__(self, vectors):
        self.vectors = vectors
        self.calls = []

    def embed_documents(self, texts):
        self.calls.append(texts)
        return self.vectors


@pytest.mark.parametrize(
    "case",
    json.loads(CASES_PATH.read_text(encoding="utf-8")),
    ids=lambda case: case["id"],
)
def test_skill_matching_cases(case):
    candidate = CandidateProfile(skills=case["candidate_skills"])
    job = JobProfile(
        job_index=3,
        title="Engineer",
        required_skills=case["required_skills"],
        preferred_skills=case["preferred_skills"],
    )
    result = MatchingEngine().match(candidate, job)
    expected = case["expected"]
    assert result.job_index == 3
    assert result.matched_required_skills == expected["matched_required"]
    assert result.missing_required_skills == expected["missing_required"]
    assert result.matched_preferred_skills == expected["matched_preferred"]
    assert result.missing_preferred_skills == expected["missing_preferred"]
    assert result.required_skill_coverage == pytest.approx(expected["required_coverage"])
    assert result.preferred_skill_coverage == pytest.approx(expected["preferred_coverage"])


def test_alias_dictionary_is_explicit_and_does_not_merge_related_frameworks():
    assert normalize_skill("Python3") == "python"
    assert normalize_skill("Postgres") == "postgresql"
    assert normalize_skill("K8s") == "kubernetes"
    assert normalize_skill("LangChain") == "langchain"
    assert normalize_skill("LangGraph") == "langgraph"
    assert normalize_skill("LangChain") != normalize_skill("LangGraph")


def test_project_similarity_uses_highest_project_responsibility_pair():
    candidate = CandidateProfile(
        projects=[
            Project(name="Unrelated", description="mobile layout"),
            Project(name="Search API", description="REST API course search"),
        ]
    )
    job = JobProfile(
        job_index=1,
        title="Backend Engineer",
        responsibilities=["Build REST APIs", "Operate databases"],
    )
    embedding = StaticEmbedding(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [0.0, 1.0],
            [0.6, 0.8],
        ]
    )
    result = MatchingEngine(embedding).match(candidate, job)
    assert result.project_similarity_available is True
    assert result.project_similarity == 1.0
    assert result.score == 100.0
    assert "Search API" in result.evidence[-2]
    assert "Build REST APIs" in result.evidence[-2]
    assert "static-test-v1" in result.evidence[-2]
    assert len(embedding.calls) == 1


@pytest.mark.parametrize(
    ("projects", "responsibilities"),
    [([], ["Build APIs"]), ([Project(name="API", description="Build APIs")], [])],
)
def test_project_similarity_is_unavailable_when_one_side_is_empty(projects, responsibilities):
    candidate = CandidateProfile(projects=projects)
    job = JobProfile(
        job_index=0,
        title="Engineer",
        responsibilities=responsibilities,
    )
    result = MatchingEngine().match(candidate, job)
    assert result.project_similarity == 0.0
    assert result.project_similarity_available is False
    assert result.score is None


def test_score_renormalizes_only_available_dimensions():
    candidate = CandidateProfile(skills=["Python"])
    job = JobProfile(
        job_index=0,
        title="Engineer",
        required_skills=["Python", "SQL"],
        preferred_skills=["Docker"],
    )
    result = MatchingEngine().match(candidate, job)
    assert result.required_skill_coverage == 0.5
    assert result.preferred_skill_coverage == 0.0
    assert result.project_similarity_available is False
    assert result.score == pytest.approx(35.71, abs=0.001)


def test_empty_requirements_with_project_uses_only_project_weight():
    candidate = CandidateProfile(projects=[Project(name="API", description="Build API")])
    job = JobProfile(
        job_index=0,
        title="Engineer",
        responsibilities=["Build API"],
    )
    result = MatchingEngine(StaticEmbedding([[1.0, 0.0], [1.0, 0.0]])).match(candidate, job)
    assert result.required_skill_coverage == 0.0
    assert result.preferred_skill_coverage == 0.0
    assert result.score == 100.0


def test_hash_embedding_and_matching_are_deterministic():
    embedding = HashingEmbeddingClient()
    texts = ["REST API course search", "Build REST APIs"]
    assert embedding.embed_documents(texts) == embedding.embed_documents(texts)
    candidate = CandidateProfile(
        skills=["Python"],
        projects=[Project(name="Course API", description="REST API course search")],
    )
    job = JobProfile(
        job_index=0,
        title="Backend Engineer",
        required_skills=["Python"],
        responsibilities=["Build REST APIs"],
    )
    engine = MatchingEngine(embedding)
    assert engine.match(candidate, job) == engine.match(candidate, job)


@pytest.mark.parametrize(
    "vectors",
    [
        [],
        [[1.0, 0.0]],
        [[1.0], [1.0, 0.0]],
        [[math.nan, 0.0], [1.0, 0.0]],
    ],
)
def test_invalid_embedding_output_is_rejected(vectors):
    candidate = CandidateProfile(projects=[Project(name="API", description="Build API")])
    job = JobProfile(
        job_index=0,
        title="Engineer",
        responsibilities=["Build API"],
    )
    with pytest.raises(MatchCalculationError):
        MatchingEngine(StaticEmbedding(vectors)).match(candidate, job)


def test_evidence_names_candidate_and_job_skills():
    result = MatchingEngine().match(
        CandidateProfile(skills=["python3"]),
        JobProfile(job_index=0, title="Engineer", required_skills=["Python"]),
    )
    assert result.evidence[0] == (
        "required skill 'Python' matched candidate skill 'python3' (canonical: 'python')"
    )
    assert "available weights: required:0.5" in result.evidence[-1]


def test_alias_overlap_between_required_and_preferred_is_rejected():
    job = JobProfile(
        job_index=0,
        title="Engineer",
        required_skills=["Python"],
        preferred_skills=["Python3"],
    )
    with pytest.raises(MatchCalculationError, match="overlap"):
        MatchingEngine().match(CandidateProfile(skills=["Python"]), job)
