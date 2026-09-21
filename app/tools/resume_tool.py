"""Thin, text-only resume tool; callers cannot supply a filesystem path."""

from typing import Protocol

from app.schemas.candidate import CandidateProfile
from app.schemas.common import Contract, NonEmptyText


class ResumeParserLike(Protocol):
    def parse_text(self, text: str, *, source_id: str, request_id: str) -> CandidateProfile: ...


class ParseResumeInput(Contract):
    text: NonEmptyText
    source_id: NonEmptyText = "resume:text"
    request_id: NonEmptyText


class ParseResumeTool:
    name = "parse_resume_tool"
    description = "Parse authorized resume text into a CandidateProfile."
    args_schema = ParseResumeInput

    def __init__(self, parser: ResumeParserLike) -> None:
        self.parser = parser

    def invoke(self, arguments: ParseResumeInput) -> CandidateProfile:
        return self.parser.parse_text(
            arguments.text,
            source_id=arguments.source_id,
            request_id=arguments.request_id,
        )
