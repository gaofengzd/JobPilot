"""Compile the Day 8 workflow with bounded tools, reflection, and repair."""

from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.gap_analyzer import GapAnalyzer
from app.agents.jd_analyzer import JDAnalyzer
from app.agents.learning_planner import LearningPlanner
from app.agents.reflection import Reflection
from app.agents.resume_optimizer import ResumeOptimizer
from app.agents.resume_parser import ResumeParser
from app.business.batch_analyzer import BatchAnalyzer
from app.business.matching_engine import MatchingEngine
from app.core.config import Settings
from app.graph.edges import route_learning, route_reflection
from app.graph.nodes import WorkflowDependencies, WorkflowNodes
from app.graph.state import JobPilotState
from app.rag.retriever import KnowledgeRetriever
from app.services.embedding import BGEEmbeddingClient
from app.services.llm import LLMClient
from app.tools.retrieval_tool import LLMKnowledgeTool, RetrieveKnowledgeTool


def build_workflow(dependencies: WorkflowDependencies) -> CompiledStateGraph:
    nodes = WorkflowNodes(dependencies)
    graph = StateGraph(JobPilotState)
    graph.add_node("validate_input", nodes.validate_input)
    graph.add_node("parse_resume", nodes.parse_resume)
    graph.add_node("analyze_jobs", nodes.analyze_jobs)
    graph.add_node("calculate_matches", nodes.calculate_matches)
    graph.add_node("calculate_statistics", nodes.calculate_statistics)
    graph.add_node("analyze_gap", nodes.analyze_gap)
    graph.add_node("retrieve_knowledge", nodes.retrieve_knowledge)
    graph.add_node("learning_plan", nodes.create_learning_plan)
    graph.add_node("optimize_resume", nodes.optimize_resume)
    graph.add_node("reflection", nodes.reflect)
    graph.add_node("repair_outputs", nodes.repair_outputs)
    graph.add_node("finalize_reflection_failure", nodes.finalize_reflection_failure)
    graph.add_node("final_report", nodes.build_final_report)

    graph.add_edge(START, "validate_input")
    graph.add_edge("validate_input", "parse_resume")
    graph.add_edge("parse_resume", "analyze_jobs")
    graph.add_edge("analyze_jobs", "calculate_matches")
    graph.add_edge("calculate_matches", "calculate_statistics")
    graph.add_edge("calculate_statistics", "analyze_gap")
    graph.add_conditional_edges(
        "analyze_gap",
        route_learning,
        {
            "retrieve_knowledge": "retrieve_knowledge",
            "optimize_resume": "optimize_resume",
        },
    )
    graph.add_edge("retrieve_knowledge", "learning_plan")
    graph.add_edge("learning_plan", "optimize_resume")
    graph.add_edge("optimize_resume", "reflection")
    graph.add_conditional_edges(
        "reflection",
        partial(
            route_reflection,
            max_repair_attempts=dependencies.max_repair_attempts,
        ),
        {
            "final_report": "final_report",
            "repair_outputs": "repair_outputs",
            "finalize_reflection_failure": "finalize_reflection_failure",
        },
    )
    graph.add_edge("repair_outputs", "reflection")
    graph.add_edge("finalize_reflection_failure", "final_report")
    graph.add_edge("final_report", END)
    return graph.compile()


def build_default_workflow(settings: Settings) -> CompiledStateGraph:
    llm = LLMClient(settings)
    embedding = BGEEmbeddingClient(
        settings.embedding_model_path,
        device=settings.embedding_device,
    )

    def create_retriever() -> KnowledgeRetriever:
        retriever = KnowledgeRetriever(embedding)
        retriever.index_directory(settings.knowledge_dir)
        return retriever

    def create_knowledge_tool() -> LLMKnowledgeTool:
        return LLMKnowledgeTool(llm, RetrieveKnowledgeTool(create_retriever()))

    dependencies = WorkflowDependencies(
        resume_parser=ResumeParser(llm),
        jd_analyzer=JDAnalyzer(llm),
        matching_engine=MatchingEngine(embedding),
        gap_analyzer=GapAnalyzer(),
        batch_analyzer=BatchAnalyzer(),
        learning_planner=LearningPlanner(),
        resume_optimizer=ResumeOptimizer(),
        knowledge_tool_factory=create_knowledge_tool,
        reflection=Reflection(),
        max_repair_attempts=settings.max_repair_attempts,
    )
    return build_workflow(dependencies)
