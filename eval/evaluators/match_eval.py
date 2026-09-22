"""Deterministic skill-match metrics against human-authored cases."""

from app.business.matching_engine import MatchingEngine, normalize_skill
from app.schemas.candidate import CandidateProfile
from app.schemas.job import JobProfile


def evaluate_matching(cases: list[dict]) -> dict:
    engine = MatchingEngine()
    expected_matched: set[tuple[str, str, str]] = set()
    actual_matched: set[tuple[str, str, str]] = set()
    coverage_errors: list[float] = []
    failures = []
    for case in cases:
        result = engine.match(
            CandidateProfile(skills=case["candidate_skills"]),
            JobProfile(
                job_index=0,
                title="Evaluation Job",
                required_skills=case["required_skills"],
                preferred_skills=case["preferred_skills"],
            ),
        )
        expected = case["expected"]
        for kind in ("required", "preferred"):
            expected_matched.update(
                (case["id"], kind, normalize_skill(skill)) for skill in expected[f"matched_{kind}"]
            )
            actual_matched.update(
                (case["id"], kind, normalize_skill(skill))
                for skill in getattr(result, f"matched_{kind}_skills")
            )
            coverage_errors.append(
                abs(getattr(result, f"{kind}_skill_coverage") - expected[f"{kind}_coverage"])
            )
        actual = {
            "matched_required": result.matched_required_skills,
            "missing_required": result.missing_required_skills,
            "matched_preferred": result.matched_preferred_skills,
            "missing_preferred": result.missing_preferred_skills,
        }
        if any(
            {normalize_skill(skill) for skill in actual[key]}
            != {normalize_skill(skill) for skill in expected[key]}
            for key in actual
        ):
            failures.append({"id": case["id"], "expected": expected, "actual": actual})

    true_positive = len(expected_matched & actual_matched)
    precision = _ratio(true_positive, len(actual_matched))
    recall = _ratio(true_positive, len(expected_matched))
    return {
        "cases": len(cases),
        "precision": precision,
        "recall": recall,
        "coverage_mean_absolute_error": (
            sum(coverage_errors) / len(coverage_errors) if coverage_errors else 0.0
        ),
        "exact_cases": len(cases) - len(failures),
        "failures": failures,
    }


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0
