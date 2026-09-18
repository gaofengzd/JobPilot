"""Day 1 contract regressions; no network calls."""

import math

import pytest
from pydantic import ValidationError

from app.graph.state import JobPilotState, create_initial_state
from app.schemas.batch import BatchStatistics, SkillFrequency
from app.schemas.candidate import CandidateProfile, Education, Experience, Project
from app.schemas.common import EvidenceRef
from app.schemas.gap import SkillGap
from app.schemas.input import AgentInput
from app.schemas.job import JobProfile
from app.schemas.learning import LearningPlan, LearningTask, RetrievedDocument
from app.schemas.match import MatchResult
from app.schemas.report import FinalReport, ResumeSuggestion


def sample_report():
    evidence = EvidenceRef(source_id="jd:0", quote="Python required", locator="line:1")
    candidate_evidence = EvidenceRef(
        source_id="resume",
        quote="Built a Python project",
        locator="line:1",
    )
    return FinalReport(
        request_id="test",
        status="success",
        candidate_profile=CandidateProfile(
            education=[Education()],
            skills=["Python"],
            projects=[Project(name="Demo", description="Python project")],
            experiences=[Experience(description="Synthetic internship")],
            evidence=[candidate_evidence],
        ),
        job_profiles=[
            JobProfile(
                job_index=0,
                title="Engineer",
                required_skills=["Python"],
                preferred_skills=["Docker"],
                evidence=[evidence],
            )
        ],
        match_results=[
            MatchResult(
                job_index=0,
                matched_required_skills=["Python"],
                missing_preferred_skills=["Docker"],
                required_skill_coverage=1,
                preferred_skill_coverage=0,
                project_similarity=0,
                project_similarity_available=False,
            )
        ],
        selected_job_index=0,
        skill_gaps=[
            SkillGap(
                skill="Docker",
                requirement_type="preferred",
                reason="Not mentioned",
                evidence_status="not_mentioned",
                jd_evidence=[
                    EvidenceRef(source_id="jd:0", quote="Docker preferred", locator="line:2"),
                ],
                priority=2,
            )
        ],
        retrieved_context=[
            RetrievedDocument(
                doc_id="guide",
                chunk_id="guide:1",
                content="Docker basics",
                source="manual",
            )
        ],
        learning_plan=LearningPlan(
            job_index=0,
            tasks=[
                LearningTask(
                    skill="Docker",
                    priority=2,
                    objective="Learn containers",
                    actions=["Read guide"],
                    deliverable="One local container",
                    source_chunk_ids=["guide:1"],
                )
            ],
        ),
        resume_suggestions=[
            ResumeSuggestion(
                original_text="Built a Python project",
                suggested_text="Implemented a project using Python",
                reason="Clarify wording",
                candidate_evidence=[candidate_evidence],
            )
        ],
        batch_statistics=BatchStatistics(
            total_jobs=1,
            valid_jobs=1,
            failed_jobs=0,
            frequencies=[
                SkillFrequency(
                    skill="Python",
                    required_count=1,
                    preferred_count=0,
                    any_count=1,
                    ratio=1,
                    candidate_has_evidence=True,
                ),
            ],
        ),
    )


def test_full_report_roundtrip_and_all_schemas():
    report = sample_report()
    assert FinalReport.model_validate_json(report.model_dump_json()) == report
    for model in (
        CandidateProfile,
        Education,
        Experience,
        Project,
        EvidenceRef,
        JobProfile,
        MatchResult,
        SkillGap,
        LearningPlan,
        LearningTask,
        RetrievedDocument,
        ResumeSuggestion,
        BatchStatistics,
        SkillFrequency,
        FinalReport,
        AgentInput,
    ):
        assert model.model_json_schema()["additionalProperties"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(unexpected=True),
        lambda d: d["match_results"][0].update(required_skill_coverage=1.1),
        lambda d: d["match_results"][0].update(required_skill_coverage=0.5),
        lambda d: d["match_results"][0].update(missing_required_skills=["Python"]),
        lambda d: d["match_results"][0].update(project_similarity=0.5),
        lambda d: d["match_results"][0].update(project_similarity=math.nan),
        lambda d: d["match_results"][0].update(job_index=9),
        lambda d: d["match_results"][0].update(matched_required_skills=["Java"]),
        lambda d: d["job_profiles"].append(d["job_profiles"][0]),
        lambda d: d["job_profiles"][0].update(preferred_skills=["Python"]),
        lambda d: d["job_profiles"][0].update(required_skills=["Python", "python"]),
        lambda d: d["learning_plan"].update(job_index=1),
        lambda d: d["learning_plan"]["tasks"][0].update(source_chunk_ids=["unknown"]),
        lambda d: d["resume_suggestions"][0].update(candidate_evidence=[]),
        lambda d: d["skill_gaps"][0].update(jd_evidence=[]),
        lambda d: d["batch_statistics"].update(failed_jobs=1),
        lambda d: d["batch_statistics"]["frequencies"][0].update(ratio=0.5),
        lambda d: d.update(selected_job_index=9),
        lambda d: d.update(errors=["failure"]),
    ],
)
def test_invalid_reports_are_rejected(mutation):
    data = sample_report().model_dump()
    mutation(data)
    with pytest.raises(ValidationError):
        FinalReport.model_validate(data)


def test_no_evaluable_dimensions_requires_null_score():
    values = dict(
        job_index=0,
        required_skill_coverage=0,
        preferred_skill_coverage=0,
        project_similarity=0,
        project_similarity_available=False,
    )
    assert MatchResult(**values).score is None
    with pytest.raises(ValidationError):
        MatchResult(**values, score=70)


def test_batch_count_must_not_exceed_denominator():
    with pytest.raises(ValidationError):
        BatchStatistics(
            total_jobs=1,
            valid_jobs=1,
            failed_jobs=0,
            frequencies=[
                SkillFrequency(
                    skill="Python",
                    required_count=2,
                    preferred_count=0,
                    any_count=2,
                    ratio=1,
                    candidate_has_evidence=True,
                )
            ],
        )


def test_request_state_isolation_and_complete_fields():
    jobs = ["Python"]
    first = create_initial_state(resume_text="Resume", raw_jobs=jobs)
    second = create_initial_state(resume_text="Resume", raw_jobs=jobs)
    first["errors"].append("failed")
    first["job_errors"][0] = "failed"
    first["raw_jobs"].append("Extra")
    assert second["errors"] == [] and second["job_errors"] == {}
    assert jobs == ["Python"]
    assert first["request_id"] != second["request_id"]
    assert set(first) == set(JobPilotState.__annotations__)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"raw_jobs": ["job"]},
        {"resume_text": "resume", "resume_path": "file", "raw_jobs": ["job"]},
        {"resume_text": " ", "raw_jobs": ["job"]},
        {"resume_text": "resume", "raw_jobs": []},
        {"resume_text": "resume", "raw_jobs": [" "]},
        {"resume_text": "resume", "raw_jobs": ["job"], "selected_job_index": 1},
        {"resume_text": "resume", "raw_jobs": ["job"] * 21},
    ],
)
def test_invalid_initial_input(kwargs):
    with pytest.raises(ValueError):
        create_initial_state(**kwargs)


def test_public_input_cannot_accept_server_path():
    with pytest.raises(ValidationError):
        AgentInput(resume_text="resume", resume_path="C:/private", raw_jobs=["job"])


def test_candidate_list_defaults_are_independent():
    first, second = CandidateProfile(), CandidateProfile()
    first.skills.append("Python")
    assert second.skills == []


def test_failed_report_can_preserve_error_without_fake_profile():
    report = FinalReport(request_id="failed", status="failed", errors=["Empty file"])
    assert report.candidate_profile is None
