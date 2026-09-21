"""Deterministic adapters for the offline Day 8 graph demonstration."""

from app.agents.gap_analyzer import GapAnalyzer
from app.agents.learning_planner import LearningPlanner
from app.agents.resume_optimizer import ResumeOptimizer
from app.business.batch_analyzer import BatchAnalyzer
from app.business.matching_engine import MatchingEngine
from app.graph.nodes import WorkflowDependencies
from app.schemas.candidate import CandidateProfile
from app.schemas.common import EvidenceRef
from app.schemas.job import JobProfile
from app.schemas.learning import RetrievedDocument


class DemoResumeParser:
    def parse_text(self, text, *, source_id, request_id):
        return CandidateProfile(
            skills=["Python", "FastAPI"],
            evidence=[
                EvidenceRef(
                    source_id=source_id,
                    quote="Built a Python API with FastAPI",
                    locator="line:1",
                )
            ],
        )

    def parse_document(self, document, *, request_id):
        return self.parse_text(
            document.text,
            source_id=document.source_id,
            request_id=request_id,
        )


class DemoJDAnalyzer:
    def analyze(self, text, *, job_index, source_id, request_id):
        required, preferred = {
            "backend": (["Python", "PostgreSQL"], ["FastAPI"]),
            "agent": (["Python", "LangGraph", "Docker"], ["FastAPI"]),
        }[text]
        return JobProfile(
            job_index=job_index,
            title=f"Synthetic {text.title()} Engineer",
            required_skills=required,
            preferred_skills=preferred,
            evidence=[
                EvidenceRef(
                    source_id=source_id,
                    quote="Required skills: " + ", ".join(required),
                    locator="line:1",
                ),
                EvidenceRef(
                    source_id=source_id,
                    quote="Preferred skills: " + ", ".join(preferred),
                    locator="line:2",
                ),
            ],
        )


class DemoRetriever:
    def retrieve(self, gap):
        return [
            RetrievedDocument(
                doc_id=gap.skill.casefold(),
                chunk_id=f"{gap.skill.casefold()}:0",
                content=f"{gap.skill} practical learning guide",
                source=f"{gap.skill.casefold()}.md",
                score=1.0,
            )
        ]


def build_demo_dependencies() -> WorkflowDependencies:
    return WorkflowDependencies(
        resume_parser=DemoResumeParser(),
        jd_analyzer=DemoJDAnalyzer(),
        matching_engine=MatchingEngine(),
        gap_analyzer=GapAnalyzer(),
        batch_analyzer=BatchAnalyzer(),
        learning_planner=LearningPlanner(),
        resume_optimizer=ResumeOptimizer(),
        retriever=DemoRetriever(),
    )
