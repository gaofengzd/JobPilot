"""Thin deterministic batch-statistics tool."""

from app.business.batch_analyzer import BatchAnalyzer
from app.schemas.batch import BatchStatistics
from app.schemas.candidate import CandidateProfile
from app.schemas.common import Contract, NonNegativeInt
from app.schemas.job import JobProfile


class CalculateStatisticsInput(Contract):
    candidate: CandidateProfile
    jobs: list[JobProfile]
    total_jobs: NonNegativeInt


class CalculateStatisticsTool:
    name = "calculate_statistics_tool"
    description = "Calculate deterministic skill frequencies for valid jobs."
    args_schema = CalculateStatisticsInput

    def __init__(self, analyzer: BatchAnalyzer) -> None:
        self.analyzer = analyzer

    def invoke(self, arguments: CalculateStatisticsInput) -> BatchStatistics:
        return self.analyzer.analyze(
            arguments.candidate,
            arguments.jobs,
            total_jobs=arguments.total_jobs,
        )
