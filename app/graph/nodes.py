"""Thin LangGraph nodes that orchestrate existing business modules."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from app.agents.gap_analyzer import GapAnalyzer
from app.agents.learning_planner import LearningPlanner
from app.agents.reflection import Reflection, repair_target
from app.agents.resume_optimizer import ResumeOptimizer
from app.business.batch_analyzer import BatchAnalyzer
from app.core.exceptions import JobPilotError
from app.graph.state import JobPilotState
from app.schemas.candidate import CandidateProfile
from app.schemas.gap import SkillGap
from app.schemas.input import InternalInput
from app.schemas.job import JobProfile
from app.schemas.learning import RetrievedDocument
from app.schemas.match import MatchResult
from app.schemas.report import FinalReport
from app.tools.retrieval_tool import DirectKnowledgeTool, KnowledgeToolLike, RetrieveKnowledgeTool
from app.utils.resume_files import ResumeDocument, load_resume


class ResumeParserLike(Protocol):
    def parse_text(self, text: str, *, source_id: str, request_id: str) -> CandidateProfile: ...

    def parse_document(self, document: ResumeDocument, *, request_id: str) -> CandidateProfile: ...


class JDAnalyzerLike(Protocol):
    def analyze(
        self,
        text: str,
        *,
        job_index: int,
        source_id: str,
        request_id: str,
    ) -> JobProfile: ...


class MatchingEngineLike(Protocol):
    def match(self, candidate: CandidateProfile, job: JobProfile) -> MatchResult: ...


class GapRetrieverLike(Protocol):
    def retrieve(self, gap: SkillGap) -> list[RetrievedDocument]: ...


@dataclass
class WorkflowDependencies:
    resume_parser: ResumeParserLike
    jd_analyzer: JDAnalyzerLike
    matching_engine: MatchingEngineLike
    gap_analyzer: GapAnalyzer
    batch_analyzer: BatchAnalyzer
    learning_planner: LearningPlanner
    resume_optimizer: ResumeOptimizer
    retriever: GapRetrieverLike | None = None
    retriever_factory: Callable[[], GapRetrieverLike] | None = None
    knowledge_tool: KnowledgeToolLike | None = None
    knowledge_tool_factory: Callable[[], KnowledgeToolLike] | None = None
    reflection: Reflection | None = None
    max_repair_attempts: int = 2

    def get_retriever(self) -> GapRetrieverLike:
        if self.retriever is None:
            if self.retriever_factory is None:
                raise RuntimeError("Learning retrieval is not configured.")
            self.retriever = self.retriever_factory()
        return self.retriever

    def get_knowledge_tool(self) -> KnowledgeToolLike:
        if self.knowledge_tool is None:
            if self.knowledge_tool_factory is not None:
                self.knowledge_tool = self.knowledge_tool_factory()
            else:
                self.knowledge_tool = DirectKnowledgeTool(
                    RetrieveKnowledgeTool(self.get_retriever())
                )
        return self.knowledge_tool

    def get_reflection(self) -> Reflection:
        if self.reflection is None:
            self.reflection = Reflection()
        return self.reflection


class WorkflowNodes:
    def __init__(self, dependencies: WorkflowDependencies) -> None:
        self.dependencies = dependencies

    def validate_input(self, state: JobPilotState) -> dict[str, object]:
        InternalInput(
            resume_path=state["resume_path"],
            resume_text=state["resume_text"],
            raw_jobs=state["raw_jobs"],
            selected_job_index=state["selected_job_index"] or 0,
            need_advice=state["need_advice"],
        )
        return {}

    def parse_resume(self, state: JobPilotState) -> dict[str, object]:
        if state["resume_text"] is not None:
            profile = self.dependencies.resume_parser.parse_text(
                state["resume_text"],
                source_id="resume:text",
                request_id=state["request_id"],
            )
        else:
            document = load_resume(state["resume_path"] or "")
            profile = self.dependencies.resume_parser.parse_document(
                document,
                request_id=state["request_id"],
            )
        return {"candidate_profile": profile}

    def analyze_jobs(self, state: JobPilotState) -> dict[str, object]:
        profiles: list[JobProfile] = []
        errors: dict[int, str] = {}
        for index, text in enumerate(state["raw_jobs"]):
            try:
                profiles.append(
                    self.dependencies.jd_analyzer.analyze(
                        text,
                        job_index=index,
                        source_id=f"job:{index}",
                        request_id=state["request_id"],
                    )
                )
            except JobPilotError as exc:
                errors[index] = str(exc)
        return {"job_profiles": profiles, "job_errors": errors}

    def calculate_matches(self, state: JobPilotState) -> dict[str, object]:
        candidate = _require_candidate(state)
        matches = [
            self.dependencies.matching_engine.match(candidate, job) for job in state["job_profiles"]
        ]
        return {"match_results": matches}

    def calculate_statistics(self, state: JobPilotState) -> dict[str, object]:
        candidate = _require_candidate(state)
        statistics = self.dependencies.batch_analyzer.analyze(
            candidate,
            state["job_profiles"],
            total_jobs=len(state["raw_jobs"]),
        )
        return {"batch_statistics": statistics}

    def analyze_gap(self, state: JobPilotState) -> dict[str, object]:
        selected = state["selected_job_index"]
        jobs = {job.job_index: job for job in state["job_profiles"]}
        matches = {match.job_index: match for match in state["match_results"]}
        if selected not in jobs or selected not in matches:
            return {
                "skill_gaps": [],
                "errors": [
                    *state["errors"],
                    f"Selected job index {selected} could not be analyzed.",
                ],
            }
        return {
            "skill_gaps": self.dependencies.gap_analyzer.analyze(jobs[selected], matches[selected])
        }

    def retrieve_knowledge(self, state: JobPilotState) -> dict[str, object]:
        selected = state["selected_job_index"]
        if selected is None:
            return {"retrieved_context": []}
        tool = self.dependencies.get_knowledge_tool()
        documents: dict[str, RetrievedDocument] = {}
        errors = list(state["errors"])
        for gap in state["skill_gaps"]:
            try:
                results = tool.retrieve(
                    gap,
                    job_index=selected,
                    request_id=state["request_id"],
                )
            except JobPilotError as exc:
                errors.append(f"retrieve_knowledge_tool:{gap.skill}: {exc}")
                continue
            for document in results:
                documents.setdefault(document.chunk_id, document)
        return {"retrieved_context": list(documents.values()), "errors": errors}

    def create_learning_plan(self, state: JobPilotState) -> dict[str, object]:
        selected = state["selected_job_index"]
        if selected is None:
            return {"learning_plan": None}
        return {
            "learning_plan": self.dependencies.learning_planner.plan(
                job_index=selected,
                gaps=state["skill_gaps"],
                documents=state["retrieved_context"],
            )
        }

    def optimize_resume(self, state: JobPilotState) -> dict[str, object]:
        selected = state["selected_job_index"]
        jobs = {job.job_index: job for job in state["job_profiles"]}
        if selected not in jobs:
            return {"resume_suggestions": []}
        return {
            "resume_suggestions": self.dependencies.resume_optimizer.optimize(
                _require_candidate(state),
                jobs[selected],
                state["skill_gaps"],
            )
        }

    def reflect(self, state: JobPilotState) -> dict[str, object]:
        issues = self.dependencies.get_reflection().validate(state)
        return {
            "validation_issues": issues,
            "repair_target": repair_target(issues),
        }

    def repair_outputs(self, state: JobPilotState) -> dict[str, object]:
        target = state["repair_target"]
        updates: dict[str, object] = {"retry_count": state["retry_count"] + 1}
        selected = state["selected_job_index"]
        jobs = {job.job_index: job for job in state["job_profiles"]}
        if target == "match_results":
            updates["match_results"] = [
                self.dependencies.matching_engine.match(_require_candidate(state), job)
                for job in state["job_profiles"]
            ]
        if target in {"match_results", "skill_gaps"} and selected in jobs:
            matches = {
                item.job_index: item
                for item in updates.get("match_results", state["match_results"])
            }
            updates["skill_gaps"] = self.dependencies.gap_analyzer.analyze(
                jobs[selected], matches[selected]
            )
        effective_gaps = updates.get("skill_gaps", state["skill_gaps"])
        if target in {"match_results", "skill_gaps", "learning_plan"} and selected is not None:
            updates["learning_plan"] = self.dependencies.learning_planner.plan(
                job_index=selected,
                gaps=effective_gaps,
                documents=state["retrieved_context"],
            )
        if (
            target
            in {
                "match_results",
                "skill_gaps",
                "resume_suggestions",
            }
            and selected in jobs
        ):
            updates["resume_suggestions"] = self.dependencies.resume_optimizer.optimize(
                _require_candidate(state), jobs[selected], effective_gaps
            )
        return updates

    def finalize_reflection_failure(self, state: JobPilotState) -> dict[str, object]:
        target = state["repair_target"]
        updates: dict[str, object] = {
            "errors": [
                *state["errors"],
                "Reflection remained invalid after "
                f"{state['retry_count']} repairs: " + "; ".join(state["validation_issues"]),
            ]
        }
        if target == "match_results":
            updates.update(
                match_results=[],
                skill_gaps=[],
                retrieved_context=[],
                learning_plan=None,
                resume_suggestions=[],
            )
        elif target == "skill_gaps":
            updates.update(
                skill_gaps=[],
                retrieved_context=[],
                learning_plan=None,
                resume_suggestions=[],
            )
        elif target == "learning_plan":
            updates["learning_plan"] = None
        elif target == "resume_suggestions":
            updates["resume_suggestions"] = []
        return updates

    def build_final_report(self, state: JobPilotState) -> dict[str, object]:
        candidate = state["candidate_profile"]
        selected = state["selected_job_index"]
        valid_indexes = {job.job_index for job in state["job_profiles"]}
        errors = list(state["errors"])
        if candidate is None or not state["job_profiles"] or not state["match_results"]:
            status = "failed"
        elif state["job_errors"] or errors or selected not in valid_indexes:
            status = "partial"
        else:
            status = "success"
        warnings = list(state["learning_plan"].warnings) if state["learning_plan"] else []
        report = FinalReport(
            request_id=state["request_id"],
            status=status,
            candidate_profile=candidate,
            job_profiles=state["job_profiles"],
            match_results=state["match_results"],
            selected_job_index=selected,
            skill_gaps=state["skill_gaps"],
            retrieved_context=state["retrieved_context"],
            learning_plan=state["learning_plan"],
            resume_suggestions=state["resume_suggestions"],
            batch_statistics=state["batch_statistics"],
            job_errors=state["job_errors"],
            errors=errors,
            warnings=warnings,
        )
        return {"final_report": report, "status": status}


def _require_candidate(state: JobPilotState) -> CandidateProfile:
    candidate = state["candidate_profile"]
    if candidate is None:
        raise RuntimeError("Candidate profile is unavailable.")
    return candidate
