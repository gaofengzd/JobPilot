"""Candidate facts extracted from the resume."""

from pydantic import Field

from app.schemas.common import Contract, EvidenceRef, NonEmptyText


class Education(Contract):
    school: NonEmptyText | None = None
    degree: NonEmptyText | None = None
    major: NonEmptyText | None = None
    start_date: NonEmptyText | None = None
    end_date: NonEmptyText | None = None


class Project(Contract):
    name: NonEmptyText
    description: NonEmptyText
    technologies: list[NonEmptyText] = Field(default_factory=list)
    achievements: list[NonEmptyText] = Field(default_factory=list)


class Experience(Contract):
    company: NonEmptyText | None = None
    role: NonEmptyText | None = None
    description: NonEmptyText
    technologies: list[NonEmptyText] = Field(default_factory=list)
    achievements: list[NonEmptyText] = Field(default_factory=list)
    start_date: NonEmptyText | None = None
    end_date: NonEmptyText | None = None


class CandidateProfile(Contract):
    education: list[Education] = Field(default_factory=list)
    skills: list[NonEmptyText] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    certificates: list[NonEmptyText] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
