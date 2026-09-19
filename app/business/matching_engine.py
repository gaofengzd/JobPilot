"""Deterministic CandidateProfile and JobProfile matching."""

import math
import re
import unicodedata

from app.core.exceptions import MatchCalculationError
from app.schemas.candidate import CandidateProfile, Project
from app.schemas.job import JobProfile
from app.schemas.match import MatchResult
from app.services.embedding import EmbeddingClient, HashingEmbeddingClient

REQUIRED_WEIGHT = 0.5
PREFERRED_WEIGHT = 0.2
PROJECT_WEIGHT = 0.3
SCORE_VERSION = "1.0"

SKILL_ALIASES = {
    "js": "javascript",
    "javascript": "javascript",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "py": "python",
    "python 3": "python",
    "python3": "python",
    "scikit learn": "scikit-learn",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "ts": "typescript",
    "typescript": "typescript",
}


class MatchingEngine:
    def __init__(self, embedding: EmbeddingClient | None = None) -> None:
        self.embedding = embedding or HashingEmbeddingClient()

    def match(self, candidate: CandidateProfile, job: JobProfile) -> MatchResult:
        candidate_skills = _candidate_skill_index(candidate.skills)
        required = _deduplicate_requirements(job.required_skills)
        preferred = _deduplicate_requirements(job.preferred_skills)
        overlap = {canonical for _, canonical in required} & {
            canonical for _, canonical in preferred
        }
        if overlap:
            raise MatchCalculationError(
                "Required and preferred skills overlap after alias normalization."
            )

        matched_required, missing_required, required_evidence = _partition_skills(
            required, candidate_skills, "required"
        )
        matched_preferred, missing_preferred, preferred_evidence = _partition_skills(
            preferred, candidate_skills, "preferred"
        )
        required_coverage = _coverage(matched_required, missing_required)
        preferred_coverage = _coverage(matched_preferred, missing_preferred)

        similarity, similarity_available, project_evidence = self._project_similarity(
            candidate.projects, job.responsibilities
        )
        dimensions: list[tuple[float, float]] = []
        if required:
            dimensions.append((REQUIRED_WEIGHT, required_coverage))
        if preferred:
            dimensions.append((PREFERRED_WEIGHT, preferred_coverage))
        if similarity_available:
            dimensions.append((PROJECT_WEIGHT, similarity))
        score = _weighted_score(dimensions)
        score_evidence = _score_evidence(
            score,
            required_available=bool(required),
            preferred_available=bool(preferred),
            project_available=similarity_available,
        )

        return MatchResult(
            job_index=job.job_index,
            matched_required_skills=matched_required,
            missing_required_skills=missing_required,
            matched_preferred_skills=matched_preferred,
            missing_preferred_skills=missing_preferred,
            required_skill_coverage=required_coverage,
            preferred_skill_coverage=preferred_coverage,
            project_similarity=similarity,
            project_similarity_available=similarity_available,
            evidence=(required_evidence + preferred_evidence + project_evidence + score_evidence),
            score=score,
            score_version=SCORE_VERSION,
        )

    def _project_similarity(
        self,
        projects: list[Project],
        responsibilities: list[str],
    ) -> tuple[float, bool, list[str]]:
        if not projects or not responsibilities:
            return 0.0, False, []
        project_texts = [_project_text(project) for project in projects]
        texts = project_texts + responsibilities
        vectors = self.embedding.embed_documents(texts)
        _validate_vectors(vectors, expected_count=len(texts))
        project_vectors = vectors[: len(projects)]
        responsibility_vectors = vectors[len(projects) :]

        best_similarity = -1.0
        best_pair = (0, 0)
        for project_index, project_vector in enumerate(project_vectors):
            for responsibility_index, responsibility_vector in enumerate(responsibility_vectors):
                similarity = _cosine(project_vector, responsibility_vector)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_pair = (project_index, responsibility_index)
        similarity = round(min(1.0, max(0.0, best_similarity)), 6)
        project = projects[best_pair[0]]
        responsibility = responsibilities[best_pair[1]]
        evidence = [
            "project similarity: "
            f"'{project.name}' <-> '{responsibility}' "
            f"= {similarity:.6f} ({self.embedding.model_id})"
        ]
        return similarity, True, evidence


def normalize_skill(skill: str) -> str:
    normalized = unicodedata.normalize("NFKC", skill).strip().casefold()
    normalized = re.sub(r"[_.]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return SKILL_ALIASES.get(normalized, normalized)


def _candidate_skill_index(skills: list[str]) -> dict[str, str]:
    index: dict[str, str] = {}
    for skill in skills:
        index.setdefault(normalize_skill(skill), skill)
    return index


def _deduplicate_requirements(skills: list[str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for skill in skills:
        canonical = normalize_skill(skill)
        if canonical not in seen:
            result.append((skill, canonical))
            seen.add(canonical)
    return result


def _partition_skills(
    requirements: list[tuple[str, str]],
    candidate_skills: dict[str, str],
    kind: str,
) -> tuple[list[str], list[str], list[str]]:
    matched: list[str] = []
    missing: list[str] = []
    evidence: list[str] = []
    for original, canonical in requirements:
        candidate_original = candidate_skills.get(canonical)
        if candidate_original is None:
            missing.append(original)
            continue
        matched.append(original)
        evidence.append(
            f"{kind} skill '{original}' matched candidate skill "
            f"'{candidate_original}' (canonical: '{canonical}')"
        )
    return matched, missing, evidence


def _coverage(matched: list[str], missing: list[str]) -> float:
    total = len(matched) + len(missing)
    return len(matched) / total if total else 0.0


def _project_text(project: Project) -> str:
    return " ".join(
        [project.name, project.description, *project.technologies, *project.achievements]
    )


def _validate_vectors(vectors: list[list[float]], *, expected_count: int) -> None:
    if len(vectors) != expected_count or not vectors:
        raise MatchCalculationError("Embedding client returned an unexpected vector count.")
    dimensions = len(vectors[0])
    if dimensions == 0 or any(len(vector) != dimensions for vector in vectors):
        raise MatchCalculationError("Embedding client returned inconsistent dimensions.")
    if any(not math.isfinite(value) for vector in vectors for value in vector):
        raise MatchCalculationError("Embedding client returned non-finite values.")


def _cosine(left: list[float], right: list[float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _score_evidence(
    score: float | None,
    *,
    required_available: bool,
    preferred_available: bool,
    project_available: bool,
) -> list[str]:
    if score is None:
        return []
    available = [
        name
        for name, included in (
            (f"required:{REQUIRED_WEIGHT}", required_available),
            (f"preferred:{PREFERRED_WEIGHT}", preferred_available),
            (f"project:{PROJECT_WEIGHT}", project_available),
        )
        if included
    ]
    return [f"score {SCORE_VERSION}: {score:.2f}/100; available weights: " + ", ".join(available)]


def _weighted_score(dimensions: list[tuple[float, float]]) -> float | None:
    if not dimensions:
        return None
    total_weight = sum(weight for weight, _ in dimensions)
    score = 100 * sum(weight * value for weight, value in dimensions) / total_weight
    return round(score, 2)
