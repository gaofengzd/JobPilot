"""Bounded learning retrieval tool with an optional real LLM tool request."""

from typing import Literal, Protocol

from app.business.matching_engine import normalize_skill
from app.core.exceptions import ToolArgumentError
from app.schemas.common import Contract, NonEmptyText, NonNegativeInt
from app.schemas.gap import SkillGap
from app.schemas.learning import RetrievedDocument
from app.services.llm import LLMClient


class GapRetrieverLike(Protocol):
    def retrieve(self, gap: SkillGap) -> list[RetrievedDocument]: ...


class retrieve_knowledge_tool(Contract):
    job_index: NonNegativeInt
    skill: NonEmptyText
    requirement_type: Literal["required", "preferred"]


RetrieveKnowledgeInput = retrieve_knowledge_tool


class KnowledgeToolLike(Protocol):
    def retrieve(
        self,
        gap: SkillGap,
        *,
        job_index: int,
        request_id: str,
    ) -> list[RetrievedDocument]: ...


class RetrieveKnowledgeTool:
    name = "retrieve_knowledge_tool"
    description = "Retrieve grounded learning material for one validated skill gap."
    args_schema = RetrieveKnowledgeInput

    def __init__(self, retriever: GapRetrieverLike) -> None:
        self.retriever = retriever

    def invoke(
        self,
        arguments: RetrieveKnowledgeInput,
        *,
        allowed_gap: SkillGap,
        job_index: int,
    ) -> list[RetrievedDocument]:
        if arguments.job_index != job_index:
            raise ToolArgumentError("Tool job_index does not match the selected job.")
        if (
            normalize_skill(arguments.skill) != normalize_skill(allowed_gap.skill)
            or arguments.requirement_type != allowed_gap.requirement_type
        ):
            raise ToolArgumentError("Tool arguments do not match the validated skill gap.")
        return self.retriever.retrieve(allowed_gap)


class DirectKnowledgeTool:
    """Deterministic executor used by offline workflows and tests."""

    def __init__(self, tool: RetrieveKnowledgeTool) -> None:
        self.tool = tool

    def retrieve(
        self,
        gap: SkillGap,
        *,
        job_index: int,
        request_id: str,
    ) -> list[RetrievedDocument]:
        arguments = RetrieveKnowledgeInput(
            job_index=job_index,
            skill=gap.skill,
            requirement_type=gap.requirement_type,
        )
        return self.tool.invoke(arguments, allowed_gap=gap, job_index=job_index)


class LLMKnowledgeTool:
    """Ask the provider for one real tool call, then execute the validated request."""

    def __init__(self, llm: LLMClient, tool: RetrieveKnowledgeTool) -> None:
        self.llm = llm
        self.tool = tool

    def retrieve(
        self,
        gap: SkillGap,
        *,
        job_index: int,
        request_id: str,
    ) -> list[RetrievedDocument]:
        result = self.llm.call_tool(
            RetrieveKnowledgeInput,
            instruction=(
                "Select the learning retrieval tool for the validated JobPilot skill gap. "
                "Use the exact job_index, skill, and requirement_type supplied."
            ),
            text=(
                f"job_index={job_index}\nskill={gap.skill}\nrequirement_type={gap.requirement_type}"
            ),
            request_id=request_id,
            execute=lambda arguments: self.tool.invoke(
                arguments,
                allowed_gap=gap,
                job_index=job_index,
            ),
            serialize_result=lambda documents: [item.model_dump() for item in documents],
            max_argument_repairs=1,
        )
        return list(result.value)
