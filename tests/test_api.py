"""Day 10 FastAPI transport tests with deterministic injected services."""

from dataclasses import dataclass

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.agents.gap_analyzer import GapAnalyzer
from app.agents.learning_planner import LearningPlanner
from app.agents.resume_optimizer import ResumeOptimizer
from app.api.dependencies import ApiServices
from app.api.main import create_app
from app.business.batch_analyzer import BatchAnalyzer
from app.business.matching_engine import MatchingEngine
from app.core.config import Settings
from app.core.exceptions import ConfigurationError, ModelCallError
from app.graph.nodes import WorkflowDependencies
from app.graph.workflow import build_workflow
from app.schemas.learning import RetrievedDocument
from tests.test_workflow import CountingResumeParser, StaticJDAnalyzer


@dataclass
class StaticRetriever:
    def retrieve(self, gap):
        return [
            RetrievedDocument(
                doc_id=gap.skill.casefold(),
                chunk_id=f"{gap.skill.casefold()}:0",
                content=f"{gap.skill} practical guide",
                source=f"{gap.skill.casefold()}.md",
            )
        ]


class CapturingResumeParser(CountingResumeParser):
    def __init__(self):
        super().__init__()
        self.source_ids = []

    def parse_document(self, document, *, request_id):
        self.source_ids.append(document.source_id)
        return super().parse_document(document, request_id=request_id)


def settings(**overrides):
    values = dict(
        _env_file=None,
        llm_model="test-model",
        llm_api_key=SecretStr("synthetic-key"),
        max_jobs=20,
    )
    values.update(overrides)
    return Settings(**values)


def services(*, resume_parser=None, jd_analyzer=None, max_jobs=20):
    resume_parser = resume_parser or CapturingResumeParser()
    jd_analyzer = jd_analyzer or StaticJDAnalyzer()
    matching = MatchingEngine()
    batch = BatchAnalyzer()
    dependencies = WorkflowDependencies(
        resume_parser=resume_parser,
        jd_analyzer=jd_analyzer,
        matching_engine=matching,
        gap_analyzer=GapAnalyzer(),
        batch_analyzer=batch,
        learning_planner=LearningPlanner(),
        resume_optimizer=ResumeOptimizer(),
        retriever=StaticRetriever(),
    )
    return ApiServices(
        settings=settings(max_jobs=max_jobs),
        resume_parser=resume_parser,
        jd_analyzer=jd_analyzer,
        matching_engine=matching,
        batch_analyzer=batch,
        workflow=build_workflow(dependencies),
    )


def test_openapi_contains_exact_day10_routes():
    client = TestClient(create_app(services()))
    paths = set(client.get("/openapi.json").json()["paths"])
    assert {"/resume/parse", "/jobs/analyze", "/jobs/batch", "/agent/run"} <= paths


def test_resume_upload_is_parsed_in_memory_and_filename_is_sanitized():
    injected = services()
    response = TestClient(create_app(injected)).post(
        "/resume/parse",
        files={"file": ("../../resume.md", b"Built a Python API", "text/markdown")},
    )
    assert response.status_code == 200
    assert response.json()["skills"] == ["Python"]
    assert injected.resume_parser.source_ids == ["resume:resume.md"]


def test_resume_upload_rejects_unsupported_empty_and_oversized_files():
    client = TestClient(create_app(services()))
    unsupported = client.post(
        "/resume/parse", files={"file": ("resume.docx", b"content", "application/octet-stream")}
    )
    empty = client.post("/resume/parse", files={"file": ("resume.txt", b"", "text/plain")})
    oversized = client.post(
        "/resume/parse",
        files={"file": ("resume.txt", b"a" * (5 * 1024 * 1024 + 1), "text/plain")},
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["detail"]["code"] == "ResumeReadError"
    assert empty.status_code == 400
    assert oversized.status_code == 413


def test_single_job_analysis_and_request_validation():
    client = TestClient(create_app(services()))
    response = client.post("/jobs/analyze", json={"jd_text": "Python,Docker", "job_index": 3})
    invalid = client.post("/jobs/analyze", json={"jd_text": "   "})
    assert response.status_code == 200
    assert response.json()["job_index"] == 3
    assert response.json()["required_skills"] == ["Python", "Docker"]
    assert invalid.status_code == 422


def test_batch_keeps_partial_failures_and_valid_denominator():
    injected = services(jd_analyzer=StaticJDAnalyzer(failures={1}))
    response = TestClient(create_app(injected)).post(
        "/jobs/batch",
        json={
            "candidate_profile": {"skills": ["Python"]},
            "raw_jobs": ["Python,Docker", "broken", "Python"],
        },
    )
    body = response.json()
    assert response.status_code == 200
    assert [item["job_index"] for item in body["job_profiles"]] == [0, 2]
    assert [item["job_index"] for item in body["match_results"]] == [0, 2]
    assert body["job_errors"] == {"1": "Synthetic JD failure."}
    assert body["batch_statistics"]["total_jobs"] == 3
    assert body["batch_statistics"]["valid_jobs"] == 2
    assert body["batch_statistics"]["failed_jobs"] == 1


def test_dynamic_batch_limit_returns_422_before_model_calls():
    analyzer = StaticJDAnalyzer()
    injected = services(jd_analyzer=analyzer, max_jobs=1)
    response = TestClient(create_app(injected)).post(
        "/jobs/batch",
        json={"candidate_profile": {"skills": []}, "raw_jobs": ["Python", "SQL"]},
    )
    assert response.status_code == 422
    assert analyzer.calls == []


def test_agent_requests_have_isolated_state_and_same_business_results():
    client = TestClient(create_app(services()))
    payload = {
        "resume_text": "Built a Python API",
        "raw_jobs": ["Python,Docker"],
        "selected_job_index": 0,
        "need_advice": True,
    }
    first = client.post("/agent/run", json=payload)
    second = client.post("/agent/run", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["request_id"] != second.json()["request_id"]
    assert first.json()["match_results"] == second.json()["match_results"]
    assert first.json()["status"] == second.json()["status"] == "success"


def test_agent_rejects_invalid_selection_and_over_limit():
    client = TestClient(create_app(services(max_jobs=1)))
    invalid_selection = client.post(
        "/agent/run",
        json={"resume_text": "Python", "raw_jobs": ["Python"], "selected_job_index": 1},
    )
    over_limit = client.post(
        "/agent/run",
        json={"resume_text": "Python", "raw_jobs": ["Python", "SQL"]},
    )
    assert invalid_selection.status_code == 422
    assert over_limit.status_code == 422


class FailingJDAnalyzer:
    def analyze(self, *args, **kwargs):
        raise ModelCallError("Model request failed safely.")


def test_model_failure_maps_to_redacted_502():
    response = TestClient(create_app(services(jd_analyzer=FailingJDAnalyzer()))).post(
        "/jobs/analyze", json={"jd_text": "Required skills: Python"}
    )
    assert response.status_code == 502
    assert response.json() == {
        "detail": {"code": "ModelCallError", "message": "Model request failed safely."}
    }


def test_services_factory_is_lazy_and_cached():
    calls = []
    injected = services()

    def factory():
        calls.append("called")
        return injected

    client = TestClient(create_app(services_factory=factory))
    assert calls == []
    assert client.post("/jobs/analyze", json={"jd_text": "Python"}).status_code == 200
    assert client.post("/jobs/analyze", json={"jd_text": "Python"}).status_code == 200
    assert calls == ["called"]


def test_configuration_failure_maps_to_503():
    def failing_factory():
        raise ConfigurationError("Model provider is not configured.")

    response = TestClient(create_app(services_factory=failing_factory)).post(
        "/jobs/analyze", json={"jd_text": "Python"}
    )
    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "ConfigurationError",
            "message": "Model provider is not configured.",
        }
    }
