"""Thin job-analysis tool backed by JDAnalyzer."""

from typing import Protocol

from app.schemas.common import Contract, NonEmptyText, NonNegativeInt
from app.schemas.job import JobProfile


class JDAnalyzerLike(Protocol):
    def analyze(
        self, text: str, *, job_index: int, source_id: str, request_id: str
    ) -> JobProfile: ...


class AnalyzeJobInput(Contract):
    text: NonEmptyText
    job_index: NonNegativeInt
    source_id: NonEmptyText
    request_id: NonEmptyText


class AnalyzeJobTool:
    name = "analyze_job_tool"
    description = "Analyze one job description and preserve its original job index."
    args_schema = AnalyzeJobInput

    def __init__(self, analyzer: JDAnalyzerLike) -> None:
        self.analyzer = analyzer

    def invoke(self, arguments: AnalyzeJobInput) -> JobProfile:
        return self.analyzer.analyze(
            arguments.text,
            job_index=arguments.job_index,
            source_id=arguments.source_id,
            request_id=arguments.request_id,
        )
