"""Build and inject API services without duplicating business logic."""

import logging
from dataclasses import dataclass
from time import perf_counter

from fastapi import Request

from app.agents.gap_analyzer import GapAnalyzer
from app.agents.jd_analyzer import JDAnalyzer
from app.agents.learning_planner import LearningPlanner
from app.agents.reflection import Reflection
from app.agents.resume_optimizer import ResumeOptimizer
from app.agents.resume_parser import ResumeParser
from app.business.batch_analyzer import BatchAnalyzer
from app.business.matching_engine import MatchingEngine
from app.core.config import Settings, load_settings
from app.core.logging import log_event
from app.graph.nodes import WorkflowDependencies
from app.graph.workflow import build_workflow
from app.rag.retriever import KnowledgeRetriever
from app.services.embedding import BGEEmbeddingClient
from app.services.llm import LLMClient
from app.tools.retrieval_tool import LLMKnowledgeTool, RetrieveKnowledgeTool

logger = logging.getLogger("jobpilot")


@dataclass(frozen=True)
class ApiServices:
    settings: Settings
    resume_parser: object
    jd_analyzer: object
    matching_engine: object
    batch_analyzer: BatchAnalyzer
    workflow: object


def build_default_services(settings: Settings | None = None) -> ApiServices:
    started = perf_counter()
    settings = settings or load_settings()
    try:
        llm = LLMClient(settings)
        embedding = BGEEmbeddingClient(
            settings.embedding_model_path,
            device=settings.embedding_device,
        )
    except Exception as exc:
        log_event(
            logger,
            "services.initialization.failed",
            level=logging.ERROR,
            node="api.services",
            status="failed",
            duration_ms=round((perf_counter() - started) * 1000, 2),
            error_type=type(exc).__name__,
        )
        raise
    resume_parser = ResumeParser(llm)
    jd_analyzer = JDAnalyzer(llm)
    matching_engine = MatchingEngine(embedding)
    batch_analyzer = BatchAnalyzer()

    def create_knowledge_tool() -> LLMKnowledgeTool:
        retriever = KnowledgeRetriever(embedding)
        retriever.index_directory(settings.knowledge_dir)
        return LLMKnowledgeTool(llm, RetrieveKnowledgeTool(retriever))

    workflow = build_workflow(
        WorkflowDependencies(
            resume_parser=resume_parser,
            jd_analyzer=jd_analyzer,
            matching_engine=matching_engine,
            gap_analyzer=GapAnalyzer(),
            batch_analyzer=batch_analyzer,
            learning_planner=LearningPlanner(),
            resume_optimizer=ResumeOptimizer(),
            knowledge_tool_factory=create_knowledge_tool,
            reflection=Reflection(),
            max_repair_attempts=settings.max_repair_attempts,
        )
    )
    result = ApiServices(
        settings=settings,
        resume_parser=resume_parser,
        jd_analyzer=jd_analyzer,
        matching_engine=matching_engine,
        batch_analyzer=batch_analyzer,
        workflow=workflow,
    )
    log_event(
        logger,
        "services.initialization.completed",
        node="api.services",
        status="success",
        duration_ms=round((perf_counter() - started) * 1000, 2),
    )
    return result


def get_services(request: Request) -> ApiServices:
    services = getattr(request.app.state, "services", None)
    if services is None:
        services = request.app.state.services_factory()
        request.app.state.services = services
    return services
