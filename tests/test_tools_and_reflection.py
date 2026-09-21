"""Day 8 tool execution, deterministic reflection, and bounded repair tests."""

from langchain_core.messages import AIMessage, ToolMessage
from pydantic import SecretStr

from app.agents.learning_planner import LearningPlanner
from app.core.config import Settings
from app.core.exceptions import ToolArgumentError
from app.graph.state import create_initial_state
from app.graph.workflow import build_workflow
from app.schemas.learning import LearningPlan, LearningTask
from app.services.llm import LLMClient
from app.tools.retrieval_tool import RetrieveKnowledgeInput, RetrieveKnowledgeTool
from tests.test_workflow import (
    CountingResumeParser,
    CountingRetriever,
    StaticJDAnalyzer,
    dependencies,
)


class SequenceModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.invocations = []

    def bind_tools(self, tools, **kwargs):
        self.schema = tools[0]
        self.options = kwargs
        return self

    def invoke(self, messages):
        self.invocations.append(messages)
        return self.responses.pop(0)


def llm_settings():
    return Settings(
        _env_file=None,
        llm_model="test-model",
        llm_api_key=SecretStr("synthetic-key"),
    )


def test_real_tool_protocol_executes_and_returns_tool_result_to_model():
    model = SequenceModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "retrieve_knowledge_tool",
                        "args": {
                            "job_index": 0,
                            "skill": "Docker",
                            "requirement_type": "required",
                        },
                        "id": "call_retrieve",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Tool result received."),
        ]
    )
    executed = []
    result = LLMClient(llm_settings(), model=model).call_tool(
        RetrieveKnowledgeInput,
        instruction="Call retrieval.",
        text="Docker",
        request_id="request-test",
        execute=lambda arguments: executed.append(arguments.skill) or ["docker:0"],
        serialize_result=lambda value: value,
    )

    assert result.value == ["docker:0"]
    assert result.tool_call_id == "call_retrieve"
    assert executed == ["Docker"]
    assert any(
        isinstance(message, ToolMessage) and message.tool_call_id == "call_retrieve"
        for message in model.invocations[1]
    )


def test_tool_arguments_receive_only_one_bounded_repair():
    def tool_call(skill, call_id):
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "retrieve_knowledge_tool",
                    "args": {
                        "job_index": 0,
                        "skill": skill,
                        "requirement_type": "required",
                    },
                    "id": call_id,
                    "type": "tool_call",
                }
            ],
        )

    model = SequenceModel(
        [
            tool_call("Kubernetes", "call_bad"),
            tool_call("Docker", "call_fixed"),
            AIMessage(content="received"),
        ]
    )

    def execute(arguments):
        if arguments.skill != "Docker":
            raise ToolArgumentError("skill drift")
        return ["docker:0"]

    result = LLMClient(llm_settings(), model=model).call_tool(
        RetrieveKnowledgeInput,
        instruction="Call retrieval.",
        text="Docker",
        request_id="request-test",
        execute=execute,
        serialize_result=lambda value: value,
    )
    assert result.argument_repairs == 1
    assert result.tool_call_id == "call_fixed"
    assert len(model.invocations) == 3


def test_retrieval_tool_rejects_model_argument_drift():
    retriever = CountingRetriever([])
    tool = RetrieveKnowledgeTool(retriever)
    from app.schemas.common import EvidenceRef
    from app.schemas.gap import SkillGap

    gap = SkillGap(
        skill="Docker",
        requirement_type="required",
        reason="Missing required skill.",
        evidence_status="not_mentioned",
        jd_evidence=[EvidenceRef(source_id="job:0", quote="Docker", locator="line:1")],
        priority=1,
    )
    arguments = RetrieveKnowledgeInput(
        job_index=0,
        skill="Kubernetes",
        requirement_type="required",
    )
    try:
        tool.invoke(arguments, allowed_gap=gap, job_index=0)
    except ToolArgumentError as error:
        assert "validated skill gap" in str(error)
    else:
        raise AssertionError("Argument drift must fail before retrieval.")
    assert retriever.calls == []


class FlakyLearningPlanner(LearningPlanner):
    def __init__(self, *, always_invalid=False):
        self.calls = 0
        self.always_invalid = always_invalid

    def plan(self, *, job_index, gaps, documents):
        self.calls += 1
        if self.always_invalid or self.calls == 1:
            return LearningPlan(
                job_index=job_index,
                tasks=[
                    LearningTask(
                        skill=gaps[0].skill,
                        priority=1,
                        objective="Learn safely.",
                        actions=["Read material."],
                        deliverable="Exercise.",
                        source_chunk_ids=["unknown:0"],
                    )
                ],
            )
        return super().plan(job_index=job_index, gaps=gaps, documents=documents)


def repair_dependencies(planner):
    base = dependencies(
        CountingResumeParser(),
        StaticJDAnalyzer(),
        retriever=CountingRetriever([]),
    )
    base.learning_planner = planner
    return base


def test_reflection_repairs_only_invalid_learning_plan_once():
    planner = FlakyLearningPlanner()
    state = create_initial_state(resume_text="Python", raw_jobs=["Python,Docker"])
    result = build_workflow(repair_dependencies(planner)).invoke(state)

    assert planner.calls == 2
    assert result["retry_count"] == 1
    assert result["validation_issues"] == []
    assert result["final_report"].status == "success"
    assert result["final_report"].learning_plan.tasks[0].source_chunk_ids == ["docker:0"]


def test_reflection_stops_after_two_repairs_and_prunes_invalid_advice():
    planner = FlakyLearningPlanner(always_invalid=True)
    state = create_initial_state(resume_text="Python", raw_jobs=["Python,Docker"])
    result = build_workflow(repair_dependencies(planner)).invoke(state)

    report = result["final_report"]
    assert planner.calls == 3
    assert result["retry_count"] == 2
    assert report.status == "partial"
    assert report.learning_plan is None
    assert "Reflection remained invalid after 2 repairs" in report.errors[-1]
