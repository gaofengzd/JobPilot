"""Day 7 LangGraph orchestration tests with injected deterministic modules."""

from dataclasses import dataclass

from app.agents.gap_analyzer import GapAnalyzer
from app.agents.learning_planner import LearningPlanner
from app.agents.resume_optimizer import ResumeOptimizer
from app.business.batch_analyzer import BatchAnalyzer
from app.business.matching_engine import MatchingEngine
from app.core.exceptions import JobGroundingError
from app.graph.nodes import WorkflowDependencies
from app.graph.state import create_initial_state
from app.graph.workflow import build_workflow
from app.schemas.candidate import CandidateProfile
from app.schemas.common import EvidenceRef
from app.schemas.job import JobProfile
from app.schemas.learning import RetrievedDocument


class CountingResumeParser:
    def __init__(self, skills=None):
        self.calls = 0
        self.skills = skills or ["Python"]
        self.evidence = EvidenceRef(
            source_id="resume:text",
            quote="Built a Python API",
            locator="line:1",
        )

    def parse_text(self, text, *, source_id, request_id):
        self.calls += 1
        return CandidateProfile(skills=self.skills, evidence=[self.evidence])

    def parse_document(self, document, *, request_id):
        self.calls += 1
        return CandidateProfile(skills=self.skills, evidence=[self.evidence])


class StaticJDAnalyzer:
    def __init__(self, failures=None):
        self.failures = set(failures or [])
        self.calls = []

    def analyze(self, text, *, job_index, source_id, request_id):
        self.calls.append(job_index)
        if job_index in self.failures:
            raise JobGroundingError("Synthetic JD failure.")
        required = [part for part in text.split(",") if part]
        return JobProfile(
            job_index=job_index,
            title=f"Job {job_index}",
            required_skills=required,
            evidence=[
                EvidenceRef(
                    source_id=source_id,
                    quote="Required skills: " + ", ".join(required),
                    locator="line:1",
                )
            ],
        )


@dataclass
class CountingRetriever:
    calls: list[str]

    def retrieve(self, gap):
        self.calls.append(gap.skill)
        return [
            RetrievedDocument(
                doc_id=gap.skill.casefold(),
                chunk_id=f"{gap.skill.casefold()}:0",
                content=f"{gap.skill} practical learning guide",
                source=f"{gap.skill.casefold()}.md",
                score=1.0,
            )
        ]


def dependencies(resume_parser, jd_analyzer, retriever=None, retriever_factory=None):
    return WorkflowDependencies(
        resume_parser=resume_parser,
        jd_analyzer=jd_analyzer,
        matching_engine=MatchingEngine(),
        gap_analyzer=GapAnalyzer(),
        batch_analyzer=BatchAnalyzer(),
        learning_planner=LearningPlanner(),
        resume_optimizer=ResumeOptimizer(),
        retriever=retriever,
        retriever_factory=retriever_factory,
    )


def invoke(deps, jobs, *, selected=0, need_advice=True):
    graph = build_workflow(deps)
    state = create_initial_state(
        resume_text="Built a Python API",
        raw_jobs=jobs,
        selected_job_index=selected,
        need_advice=need_advice,
    )
    return graph.invoke(state)


def test_workflow_parses_resume_once_and_keeps_selected_job_consistent():
    resume = CountingResumeParser()
    jd = StaticJDAnalyzer()
    retriever = CountingRetriever([])
    result = invoke(
        dependencies(resume, jd, retriever=retriever),
        ["Python", "Python,Docker"],
        selected=1,
    )
    report = result["final_report"]

    assert resume.calls == 1
    assert jd.calls == [0, 1]
    assert report.status == "success"
    assert report.selected_job_index == 1
    assert [gap.skill for gap in report.skill_gaps] == ["Docker"]
    assert report.learning_plan.job_index == 1
    assert report.learning_plan.tasks[0].source_chunk_ids == ["docker:0"]
    assert retriever.calls == ["Docker"]
    assert report.batch_statistics.total_jobs == 2
    assert [match.job_index for match in report.match_results] == [0, 1]


def test_no_gap_skips_retrieval_and_learning_branch():
    factories = []

    def factory():
        factories.append("called")
        return CountingRetriever([])

    result = invoke(
        dependencies(
            CountingResumeParser(),
            StaticJDAnalyzer(),
            retriever_factory=factory,
        ),
        ["Python"],
    )
    report = result["final_report"]
    assert factories == []
    assert report.skill_gaps == []
    assert report.retrieved_context == []
    assert report.learning_plan is None
    assert report.status == "success"


def test_need_advice_false_skips_rag_but_keeps_gap_and_resume_step():
    retriever = CountingRetriever([])
    result = invoke(
        dependencies(
            CountingResumeParser(),
            StaticJDAnalyzer(),
            retriever=retriever,
        ),
        ["Python,Docker"],
        need_advice=False,
    )
    report = result["final_report"]
    assert [gap.skill for gap in report.skill_gaps] == ["Docker"]
    assert retriever.calls == []
    assert report.learning_plan is None
    assert report.retrieved_context == []
    assert report.status == "success"


def test_partial_job_failure_preserves_original_indexes_and_denominator():
    result = invoke(
        dependencies(
            CountingResumeParser(),
            StaticJDAnalyzer(failures={0}),
            retriever=CountingRetriever([]),
        ),
        ["broken", "Python,Docker"],
        selected=1,
    )
    report = result["final_report"]
    assert report.status == "partial"
    assert report.job_errors == {0: "Synthetic JD failure."}
    assert [job.job_index for job in report.job_profiles] == [1]
    assert [match.job_index for match in report.match_results] == [1]
    assert report.batch_statistics.total_jobs == 2
    assert report.batch_statistics.valid_jobs == 1
    assert report.batch_statistics.failed_jobs == 1
    assert report.selected_job_index == 1
    assert [gap.skill for gap in report.skill_gaps] == ["Docker"]


def test_selected_job_failure_is_explicit_and_does_not_mix_other_job_details():
    result = invoke(
        dependencies(
            CountingResumeParser(),
            StaticJDAnalyzer(failures={0}),
            retriever=CountingRetriever([]),
        ),
        ["broken", "Python,Docker"],
        selected=0,
    )
    report = result["final_report"]
    assert report.status == "partial"
    assert report.selected_job_index == 0
    assert report.skill_gaps == []
    assert report.learning_plan is None
    assert report.resume_suggestions == []
    assert report.errors == ["Selected job index 0 could not be analyzed."]


def test_retriever_factory_is_lazy_and_cached_for_multiple_gaps():
    created = []
    retriever = CountingRetriever([])

    def factory():
        created.append("created")
        return retriever

    result = invoke(
        dependencies(
            CountingResumeParser(),
            StaticJDAnalyzer(),
            retriever_factory=factory,
        ),
        ["Python,Docker,LangGraph"],
    )
    assert created == ["created"]
    assert retriever.calls == ["Docker", "LangGraph"]
    assert len(result["retrieved_context"]) == 2


def test_compiled_graph_contains_day7_nodes():
    graph = build_workflow(
        dependencies(
            CountingResumeParser(),
            StaticJDAnalyzer(),
            retriever=CountingRetriever([]),
        )
    )
    names = set(graph.get_graph().nodes)
    assert {
        "validate_input",
        "parse_resume",
        "analyze_jobs",
        "calculate_matches",
        "calculate_statistics",
        "analyze_gap",
        "retrieve_knowledge",
        "learning_plan",
        "optimize_resume",
        "final_report",
    } <= names
