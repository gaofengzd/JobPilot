"""Day 3 grounded JD extraction tests."""

import json
from pathlib import Path

import pytest

from app.agents.jd_analyzer import JDAnalyzer, build_job_document
from app.core.exceptions import JobGroundingError
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


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["id"])
def test_ten_jd_cases_produce_grounded_job_profiles(case):
    expected = case["expected"]
    profile = JobProfile(
        job_index=999,
        **expected,
        evidence=[
            evidence(f"Title: {expected['title']}"),
            evidence(f"Company: {expected['company']}"),
            evidence(next(line for line in case["text"].splitlines() if "skills:" in line.lower())),
        ],
    )
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
