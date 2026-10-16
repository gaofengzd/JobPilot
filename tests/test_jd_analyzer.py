"""Day 3 grounded JD extraction tests."""

import io
import json
import logging
from pathlib import Path

import pytest

from app.agents.jd_analyzer import (
    PREFERRED_MARKERS,
    REQUIRED_MARKERS,
    JDAnalyzer,
    build_job_document,
)
from app.core.exceptions import JobGroundingError
from app.core.logging import JsonFormatter
from app.schemas.common import EvidenceRef
from app.schemas.job import JobProfile
from main import _read_job

CASES_PATH = Path(__file__).parents[1] / "eval" / "datasets" / "jd_cases.json"


class FakeLLM:
    def __init__(self, profile: JobProfile) -> None:
        self.profile = profile
        self.calls = []

    def structured(self, schema, **kwargs):
        self.calls.append((schema, kwargs))
        return self.profile


def evidence(quote: str) -> EvidenceRef:
    return EvidenceRef(source_id="model-value", quote=quote, locator="model-value")


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _matching_line(case: dict, *prefixes: str) -> str | None:
    """Return the first source line starting with any prefix (English or Chinese)."""
    for line in case["text"].splitlines():
        if line.strip().startswith(prefixes):
            return line
    return None


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["id"])
def test_jd_cases_produce_grounded_job_profiles(case):
    expected = case["expected"]
    quotes = [
        quote
        for quote in (
            _matching_line(case, "Title:", "标题:"),
            _matching_line(case, "Company:", "公司:"),
            _matching_line(case, "Required skills:", "任职要求", "岗位要求", "任职资格"),
            _matching_line(case, "Preferred skills:", "加分项"),
        )
        if quote
    ]
    assert quotes, f"Case {case['id']} must expose at least one evidence line."
    profile = JobProfile(job_index=999, **expected, evidence=[evidence(q) for q in quotes])
    fake = FakeLLM(profile)
    result = JDAnalyzer(fake).analyze(case["text"], job_index=7, source_id=f"job:{case['id']}")
    assert result.job_index == 7
    assert result.required_skills == expected["required_skills"]
    assert result.preferred_skills == expected["preferred_skills"]
    assert all(item.source_id == f"job:{case['id']}" for item in result.evidence)
    assert all(item.locator.startswith("line:") for item in result.evidence)


def test_instruction_preserves_required_preferred_boundary_and_untrusted_text():
    case = load_cases()[0]
    expected = case["expected"]
    fake = FakeLLM(
        JobProfile(
            job_index=0,
            **expected,
            evidence=[evidence(f"Title: {expected['title']}")],
        )
    )
    JDAnalyzer(fake).analyze(case["text"], job_index=0)
    schema, call = fake.calls[0]
    assert schema is JobProfile
    assert "required_skills only when" in call["instruction"]
    assert "preferred_skills only when" in call["instruction"]
    assert "Leave ambiguous skills out" in call["instruction"]
    assert "untrusted data" in call["instruction"]


@pytest.mark.parametrize("text", ["", " \n "])
def test_empty_job_description_fails_before_model(text):
    fake = FakeLLM(JobProfile(job_index=0, title="Unused"))
    with pytest.raises(JobGroundingError, match="no non-whitespace"):
        JDAnalyzer(fake).analyze(text, job_index=0)
    assert fake.calls == []


@pytest.mark.parametrize("job_index", [-1, True, 1.5, "1"])
def test_invalid_job_index_fails_before_model(job_index):
    fake = FakeLLM(JobProfile(job_index=0, title="Unused"))
    with pytest.raises(JobGroundingError, match="non-negative integer"):
        JDAnalyzer(fake).analyze("Title: Engineer", job_index=job_index)
    assert fake.calls == []


@pytest.mark.parametrize(
    "profile",
    [
        JobProfile(
            job_index=0,
            title="Invented title",
            evidence=[evidence("Title: Engineer")],
        ),
        JobProfile(job_index=0, title="Engineer"),
        JobProfile(
            job_index=0,
            title="Engineer",
            evidence=[evidence("Missing quote")],
        ),
        JobProfile(
            job_index=0,
            title="Engineer",
            required_skills=["Kubernetes"],
            evidence=[evidence("Title: Engineer")],
        ),
    ],
)
def test_ungrounded_job_output_is_rejected(profile):
    fake = FakeLLM(profile)
    with pytest.raises(JobGroundingError):
        JDAnalyzer(fake).analyze("Title: Engineer\nRequired skills: Python", job_index=0)


def test_evidence_is_deduplicated_and_relocated():
    profile = JobProfile(
        job_index=10,
        title="Engineer",
        evidence=[evidence("Title: Engineer"), evidence("Title: Engineer")],
    )
    result = JDAnalyzer(FakeLLM(profile)).analyze(
        "Title: Engineer", job_index=2, source_id="job:test"
    )
    assert result.evidence == [
        EvidenceRef(source_id="job:test", quote="Title: Engineer", locator="line:1")
    ]


def test_job_document_keeps_ambiguous_lines_as_data():
    document = build_job_document(
        "Title: Engineer\nThe team is exploring Rust",
        source_id="job:ambiguous",
    )
    assert document.lines[1] == ("line:2", "The team is exploring Rust")
    assert "[line:2]" in document.prompt_text


def test_required_preferred_misclassification_is_rejected():
    profile = JobProfile(
        job_index=0,
        title="Engineer",
        required_skills=["Redis"],
        preferred_skills=["Python"],
        evidence=[evidence("Title: Engineer")],
    )
    text = "Title: Engineer\nRequired skills: Python\nPreferred skills: Redis"
    with pytest.raises(JobGroundingError, match="classification"):
        JDAnalyzer(FakeLLM(profile)).analyze(text, job_index=0)


def test_chinese_required_heading_applies_to_following_lines():
    """Chinese postings put 任职要求 on its own line, then list clauses below."""
    text = (
        "jd1:软件测试\n"
        "任职要求：\n"
        "3）熟练运维性能测试工具(Jmeter、\n"
        "LoadRunner)、接口测试工具（Pos tman)，保障环境稳定。\n"
        "6）有军工单位或航天领域质量相关工作经验的优先。"
    )
    profile = JobProfile(
        job_index=0,
        title="软件测试",
        required_skills=["Jmeter", "LoadRunner", "Pos tman"],
        preferred_skills=["军工单位"],
        evidence=[evidence("任职要求：")],
    )
    result = JDAnalyzer(FakeLLM(profile)).analyze(text, job_index=0)
    assert result.required_skills == ["Jmeter", "LoadRunner", "Pos tman"]
    assert result.preferred_skills == ["军工单位"]


def test_chinese_heading_can_be_used_inline_and_with_punctuation_variants():
    document = build_job_document(
        "岗位要求：Java\n加分项：Kubernetes\n任职资格: Python",
        source_id="job:zh",
    )
    assert document.has_marked_support("Java", REQUIRED_MARKERS)
    assert document.has_marked_support("Python", REQUIRED_MARKERS)
    assert document.has_marked_support("Kubernetes", PREFERRED_MARKERS)


def test_heading_sections_do_not_leak_across_marker_types():
    document = build_job_document("任职要求：\nJava\n加分项：\nKubernetes", source_id="job:zh")
    assert document.has_marked_support("Java", REQUIRED_MARKERS)
    assert not document.has_marked_support("Java", PREFERRED_MARKERS)
    assert document.has_marked_support("Kubernetes", PREFERRED_MARKERS)
    assert not document.has_marked_support("Kubernetes", REQUIRED_MARKERS)


def test_inline_opposite_marker_overrides_open_section():
    """A clause that states 优先 stays preferred even inside 任职要求."""
    document = build_job_document(
        "任职要求：\nJava\n有军工经验的优先。",
        source_id="job:zh",
    )
    assert document.has_marked_support("Java", REQUIRED_MARKERS)
    assert not document.has_marked_support("军工经验", REQUIRED_MARKERS)
    assert document.has_marked_support("军工经验", PREFERRED_MARKERS)


def test_unmarked_skill_is_still_rejected_under_chinese_heading():
    document = build_job_document("任职要求：\nJava", source_id="job:zh")
    assert not document.has_marked_support("Redis", REQUIRED_MARKERS)
    assert not document.has_marked_support("Redis", PREFERRED_MARKERS)


def test_job_file_reader_handles_utf8_bom(tmp_path):
    path = tmp_path / "job.txt"
    path.write_text("\ufeffTitle: Engineer", encoding="utf-8")
    text, source_id = _read_job(str(path))
    assert text == "Title: Engineer"
    assert source_id == "job:job.txt"


def test_job_file_reader_rejects_missing_and_invalid_utf8(tmp_path):
    with pytest.raises(JobGroundingError, match="does not exist"):
        _read_job(str(tmp_path / "missing.txt"))
    path = tmp_path / "bad.txt"
    path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(JobGroundingError, match="UTF-8"):
        _read_job(str(path))


def test_optional_string_null_placeholder_is_normalized():
    profile = JobProfile(
        job_index=0,
        title="Engineer",
        company="null",
        education_requirement="N/A",
        experience_requirement="not specified",
        evidence=[evidence("Title: Engineer")],
    )
    result = JDAnalyzer(FakeLLM(profile)).analyze("Title: Engineer", job_index=0)
    assert result.company is None
    assert result.education_requirement is None
    assert result.experience_requirement is None


def test_evidence_quote_spanning_two_adjacent_lines_is_grounded():
    text = "Title: Engineer\nResponsibilities include platform work\nand on-call rotation"
    profile = JobProfile(
        job_index=0,
        title="Engineer",
        evidence=[evidence("Responsibilities include platform work and on-call rotation")],
    )
    result = JDAnalyzer(FakeLLM(profile)).analyze(text, job_index=0)
    assert result.evidence[0].locator == "line:2-line:3"


def test_evidence_quote_spanning_three_adjacent_lines_is_grounded():
    text = "Title: Engineer\nLine one of duties\nLine two of duties\nLine three of duties"
    profile = JobProfile(
        job_index=0,
        title="Engineer",
        evidence=[evidence("Line one of duties Line two of duties Line three of duties")],
    )
    result = JDAnalyzer(FakeLLM(profile)).analyze(text, job_index=0)
    assert result.evidence[0].locator == "line:2-line:4"


def test_evidence_quote_beyond_three_lines_is_rejected():
    text = "Title: Engineer\nA\nB\nC\nD"
    profile = JobProfile(
        job_index=0,
        title="Engineer",
        evidence=[evidence("A B C D")],
    )
    with pytest.raises(JobGroundingError, match="not found"):
        JDAnalyzer(FakeLLM(profile)).analyze(text, job_index=0)


def test_evidence_quote_skipping_a_line_is_rejected():
    text = "Title: Engineer\nFirst line\nSeparator\nThird line"
    profile = JobProfile(
        job_index=0,
        title="Engineer",
        evidence=[evidence("First line Third line")],
    )
    with pytest.raises(JobGroundingError, match="not found"):
        JDAnalyzer(FakeLLM(profile)).analyze(text, job_index=0)


def test_lookup_tolerates_invisible_and_punctuation_differences():
    document = build_job_document(
        "Ti\u200btle: Sen\u00adior Engi­neer!\nRequired skills: Py\u200bthon",
        source_id="job:invisible",
    )
    assert document.locate_quote("Title: Senior Engineer") == "line:1"
    assert document.locate_quote("Required skills: Python") == "line:2"
    assert document.contains_exact_span("Senior Engineer")


def test_lookup_still_rejects_different_visible_text():
    document = build_job_document("Title: Engineer", source_id="job:visible")
    assert document.locate_quote("Title: Senior Engineer") is None
    assert not document.contains_exact_span("Senior Engineer")


def test_field_value_spanning_adjacent_lines_is_grounded():
    text = "Title: Data Platform\nEngineer"
    profile = JobProfile(
        job_index=0,
        title="Data Platform Engineer",
        evidence=[evidence("Title: Data Platform")],
    )
    result = JDAnalyzer(FakeLLM(profile)).analyze(text, job_index=0)
    assert result.title == "Data Platform Engineer"


def test_ungrounded_values_are_logged_without_enabling_general_content_capture(monkeypatch):
    profile = JobProfile(
        job_index=0,
        title="Invented title",
        evidence=[evidence("Title: Engineer")],
    )
    stream = io.StringIO()
    logger = logging.Logger("jobpilot-test")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    monkeypatch.setattr("app.agents.jd_analyzer.logger", logger)

    with pytest.raises(JobGroundingError):
        JDAnalyzer(FakeLLM(profile)).analyze(
            "Title: Engineer",
            job_index=3,
            request_id="jd-grounding-test",
        )

    event = json.loads(stream.getvalue().splitlines()[-1])
    assert event["event"] == "jobs.grounding.failed"
    assert event["request_id"] == "jd-grounding-test"
    assert event["job_index"] == 3
    assert event["node"] == "analyze_jobs"
    assert event["error_type"] == "JobGroundingError"
    assert event["grounding_issue"] == "unsupported_profile_value"
    assert "title" in event["unsupported_fields"]
    assert '"field": "title"' in event["unsupported_preview"]
    assert "Invented title" in event["unsupported_preview"]
    handler.close()


def test_unmarked_skill_classification_is_logged(monkeypatch):
    # The skill must exist in the JD but without a required/preferred marker.
    profile = JobProfile(
        job_index=0,
        title="Engineer",
        required_skills=["Kubernetes"],
        evidence=[evidence("Title: Engineer")],
    )
    stream = io.StringIO()
    logger = logging.Logger("jobpilot-test")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    monkeypatch.setattr("app.agents.jd_analyzer.logger", logger)

    with pytest.raises(JobGroundingError, match="classification"):
        JDAnalyzer(FakeLLM(profile)).analyze("Title: Engineer\nKeywords: Kubernetes", job_index=0)

    event = json.loads(stream.getvalue().splitlines()[-1])
    assert event["event"] == "jobs.grounding.failed"
    assert event["grounding_issue"] == "unmarked_skill_classification"
    assert "required_skills[0]" in event["unsupported_fields"]
    assert "Kubernetes" in event["unsupported_preview"]
    handler.close()


def test_missing_evidence_and_missing_quote_are_logged(monkeypatch):
    stream = io.StringIO()
    logger = logging.Logger("jobpilot-test")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    monkeypatch.setattr("app.agents.jd_analyzer.logger", logger)

    with pytest.raises(JobGroundingError, match="no JD evidence"):
        JDAnalyzer(FakeLLM(JobProfile(job_index=0, title="Engineer"))).analyze(
            "Title: Engineer", job_index=0
        )
    assert json.loads(stream.getvalue().splitlines()[-1])["grounding_issue"] == "missing_evidence"

    stream.seek(0)
    stream.truncate(0)
    profile = JobProfile(
        job_index=0,
        title="Engineer",
        evidence=[evidence("Missing quote")],
    )
    with pytest.raises(JobGroundingError, match="not found"):
        JDAnalyzer(FakeLLM(profile)).analyze("Title: Engineer", job_index=0)
    event = json.loads(stream.getvalue().splitlines()[-1])
    assert event["grounding_issue"] == "unsupported_evidence_quote"
    assert "evidence.quote" in event["unsupported_fields"]
    assert "Missing quote" in event["unsupported_preview"]
    handler.close()
