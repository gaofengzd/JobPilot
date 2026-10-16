"""Day 9 metric and report regression tests; no model or embedding is loaded."""

import json
from pathlib import Path

import pytest

from eval.evaluators.extraction_eval import evaluate_jd_extraction
from eval.evaluators.rag_eval import evaluate_citation_support
from eval.run_eval import (
    FROZEN_REPORT,
    ROOT,
    build_parser,
    run_evaluation,
    write_report,
)


def test_jd_metrics_report_required_preferred_and_confusion_separately():
    cases = [
        {
            "id": "one",
            "expected": {
                "required_skills": ["Python", "SQL"],
                "preferred_skills": ["Docker"],
            },
        }
    ]
    predictions = {
        "one": {
            "required_skills": ["Python", "Docker"],
            "preferred_skills": ["SQL"],
        }
    }
    report = evaluate_jd_extraction(cases, predictions)

    assert report["required"]["precision"] == pytest.approx(0.5)
    assert report["required"]["recall"] == pytest.approx(0.5)
    assert report["preferred"]["precision"] == 0.0
    assert report["confusion_cases"] == [
        {
            "id": "one",
            "preferred_as_required": ["docker"],
            "required_as_preferred": ["sql"],
        }
    ]


def test_missing_prediction_counts_as_false_negative():
    cases = [
        {
            "id": "missing",
            "expected": {"required_skills": ["Python"], "preferred_skills": []},
        }
    ]
    report = evaluate_jd_extraction(cases, {})
    assert report["required"]["false_negative"] == 1
    assert report["required"]["recall"] == 0.0
    assert report["predictions"] == 0


def test_citation_support_uses_explicit_human_labels():
    result = evaluate_citation_support(
        [
            {"id": "supported", "supported": True},
            {"id": "unsupported", "supported": False},
        ]
    )
    assert result["supported"] == 1
    assert result["checked"] == 2
    assert result["value"] == 0.5
    assert result["unsupported_case_ids"] == ["unsupported"]


def test_deterministic_report_has_expected_base_cases_and_three_failure_analyses(tmp_path):
    report = run_evaluation("deterministic")
    # 3 resume + JD + 10 matching + 5 RAG + 5 error.  The JD count grew from 10
    # when the Chinese section-heading marker cases were added, so assert the
    # total against the inventory instead of a frozen literal.
    inventory = report["dataset"]["inventory"]
    assert report["dataset"]["base_case_count"] == (
        inventory["resume"]
        + inventory["jd"]
        + inventory["matching"]
        + inventory["rag"]
        + min(5, inventory["error_regressions"])
    )
    assert inventory["jd"] >= 10
    assert report["metrics"]["matching"]["cases"] == 10
    assert report["metrics"]["matching"]["exact_cases"] == 10
    assert report["runtime"]["llm_calls_performed"] is False
    assert report["runtime"]["embedding_inference_performed"] is False
    assert len(report["failure_analyses"]) >= 3
    assert report["failures"] == []

    prefix = tmp_path / "report"
    write_report(report, prefix)
    parsed = json.loads(Path(str(prefix) + ".json").read_text(encoding="utf-8"))
    markdown = Path(str(prefix) + ".md").read_text(encoding="utf-8")
    assert parsed["report_version"] == "0.6"
    assert "Failure analyses" in markdown


def test_report_prefix_with_version_dot_is_not_truncated(tmp_path):
    report = run_evaluation("deterministic")
    prefix = tmp_path / "day9-v0.6"
    write_report(report, prefix)
    assert (tmp_path / "day9-v0.6.json").is_file()
    assert (tmp_path / "day9-v0.6.md").is_file()


def test_unqualified_eval_run_cannot_overwrite_the_frozen_release_report():
    # scripts/check_release.py asserts the frozen report's version, case count
    # and failure analyses, so a bare `python -m eval.run_eval` must never
    # rewrite it.  The default output therefore points at a scratch path.
    args = build_parser().parse_args([])
    assert FROZEN_REPORT == ROOT / "eval" / "reports" / "day9-v0.6"
    assert args.output_prefix != FROZEN_REPORT
    assert Path(str(args.output_prefix) + ".json").name == "latest.json"
    assert Path(str(args.output_prefix) + ".json") != Path(str(FROZEN_REPORT) + ".json")
    assert Path(str(args.output_prefix) + ".md") != Path(str(FROZEN_REPORT) + ".md")
    # The scratch path stays under eval/reports, which .gitignore already
    # excludes, so an accidental run cannot add tracked files.
    assert args.output_prefix.parent == FROZEN_REPORT.parent


def test_explicit_prefix_can_still_refresh_the_frozen_report():
    # Refreshing the formal report stays possible, but only when asked for.
    args = build_parser().parse_args(["--output-prefix", "eval/reports/day9-v0.6"])
    resolved = args.output_prefix if args.output_prefix.is_absolute() else ROOT / args.output_prefix
    assert resolved == FROZEN_REPORT


def test_eval_datasets_keep_expected_minimum_counts():
    root = Path(__file__).parents[1] / "eval" / "datasets"
    counts = {
        name: len(json.loads((root / name).read_text(encoding="utf-8")))
        for name in (
            "resume_cases.json",
            "jd_cases.json",
            "matching_cases.json",
            "rag_cases.json",
            "error_cases.json",
            "grounding_cases.json",
        )
    }
    assert counts["resume_cases.json"] >= 3
    assert counts["jd_cases.json"] >= 10
    assert counts["matching_cases.json"] >= 10
    assert counts["rag_cases.json"] >= 5
    assert counts["error_cases.json"] >= 5
    assert counts["grounding_cases.json"] >= 5
