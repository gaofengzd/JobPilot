"""Thin deterministic matching tool."""

from typing import Protocol

from app.schemas.candidate import CandidateProfile
from app.schemas.common import Contract
from app.schemas.job import JobProfile
from app.schemas.match import MatchResult


class MatchingEngineLike(Protocol):
    def match(self, candidate: CandidateProfile, job: JobProfile) -> MatchResult: ...


class CalculateMatchInput(Contract):
    candidate: CandidateProfile
    job: JobProfile


class CalculateMatchTool:
    name = "calculate_match_tool"
    description = "Calculate a deterministic candidate-to-job match."
    args_schema = CalculateMatchInput

    def __init__(self, engine: MatchingEngineLike) -> None:
        self.engine = engine

    def invoke(self, arguments: CalculateMatchInput) -> MatchResult:
        return self.engine.match(arguments.candidate, arguments.job)
