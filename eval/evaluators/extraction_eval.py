"""Set-based extraction metrics against human-authored expectations."""

from collections.abc import Callable

from app.business.matching_engine import normalize_skill


def evaluate_jd_extraction(cases: list[dict], predictions: dict[str, dict]) -> dict:
    required = _aggregate_sets(
        cases,
        predictions,
        expected_key="required_skills",
        predicted_key="required_skills",
        normalize=normalize_skill,
    )
    preferred = _aggregate_sets(
        cases,
        predictions,
        expected_key="preferred_skills",
        predicted_key="preferred_skills",
        normalize=normalize_skill,
    )
    confusion_cases = []
    exact = 0
    for case in cases:
        predicted = predictions.get(case["id"], {})
        expected_required = _normalized(case["expected"]["required_skills"], normalize_skill)
        expected_preferred = _normalized(case["expected"]["preferred_skills"], normalize_skill)
        actual_required = _normalized(predicted.get("required_skills", []), normalize_skill)
        actual_preferred = _normalized(predicted.get("preferred_skills", []), normalize_skill)
        if expected_required == actual_required and expected_preferred == actual_preferred:
            exact += 1
        moved_to_required = sorted(actual_required & expected_preferred)
        moved_to_preferred = sorted(actual_preferred & expected_required)
        if moved_to_required or moved_to_preferred:
            confusion_cases.append(
                {
                    "id": case["id"],
                    "preferred_as_required": moved_to_required,
                    "required_as_preferred": moved_to_preferred,
                }
            )
    return {
        "cases": len(cases),
        "predictions": len(predictions),
        "exact_cases": exact,
        "exact_case_rate": exact / len(cases) if cases else 0.0,
        "required": required,
        "preferred": preferred,
        "confusion_cases": confusion_cases,
    }


def evaluate_resume_extraction(cases: list[dict], predictions: dict[str, dict]) -> dict:
    fields = {}
    for key in ("skills", "project_names", "education_schools"):
        fields[key] = _aggregate_sets(
            cases,
            predictions,
            expected_key=key,
            predicted_key=key,
            normalize=lambda value: value.strip().casefold(),
        )
    exact = sum(
        all(
            _normalized(case["expected"][key], lambda value: value.strip().casefold())
            == _normalized(
                predictions.get(case["id"], {}).get(key, []),
                lambda value: value.strip().casefold(),
            )
            for key in fields
        )
        for case in cases
    )
    return {
        "cases": len(cases),
        "predictions": len(predictions),
        "exact_cases": exact,
        "exact_case_rate": exact / len(cases) if cases else 0.0,
        "fields": fields,
    }


def _aggregate_sets(
    cases: list[dict],
    predictions: dict[str, dict],
    *,
    expected_key: str,
    predicted_key: str,
    normalize: Callable[[str], str],
) -> dict:
    true_positive = false_positive = false_negative = 0
    failures = []
    for case in cases:
        expected = _normalized(case["expected"][expected_key], normalize)
        predicted = _normalized(predictions.get(case["id"], {}).get(predicted_key, []), normalize)
        true_positive += len(expected & predicted)
        false_positive += len(predicted - expected)
        false_negative += len(expected - predicted)
        if expected != predicted:
            failures.append(
                {
                    "id": case["id"],
                    "missing": sorted(expected - predicted),
                    "unexpected": sorted(predicted - expected),
                }
            )
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    return {
        "precision": precision,
        "recall": recall,
        "f1": _ratio(2 * precision * recall, precision + recall),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "failures": failures,
    }


def _normalized(values: list[str], normalize: Callable[[str], str]) -> set[str]:
    return {normalize(value) for value in values}


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
