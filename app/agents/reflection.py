"""Deterministic fact reflection over existing structured workflow output."""

import re

from app.business.matching_engine import normalize_skill
from app.graph.state import JobPilotState
from app.schemas.common import EvidenceRef
from app.utils.resume_files import normalize_text


class Reflection:
    """Return localized issues; it never asks an LLM for a subjective review."""

    def validate(self, state: JobPilotState) -> list[str]:
        issues: list[str] = []
        jobs = {job.job_index: job for job in state["job_profiles"]}
        matches = {match.job_index: match for match in state["match_results"]}
        selected = state["selected_job_index"]

        for index, job in jobs.items():
            match = matches.get(index)
            if match is None:
                issues.append(f"match_results:job:{index}:missing match result")
                continue
            expected_required = {normalize_skill(item) for item in job.required_skills}
            actual_required = {
                normalize_skill(item)
                for item in (match.matched_required_skills + match.missing_required_skills)
            }
            expected_preferred = {normalize_skill(item) for item in job.preferred_skills}
            actual_preferred = {
                normalize_skill(item)
                for item in (match.matched_preferred_skills + match.missing_preferred_skills)
            }
            if expected_required != actual_required or expected_preferred != actual_preferred:
                issues.append(f"match_results:job:{index}:skill partitions contradict JD")

        if selected in jobs and selected in matches:
            job = jobs[selected]
            match = matches[selected]
            missing = {
                (normalize_skill(skill), requirement_type)
                for requirement_type, skills in (
                    ("required", match.missing_required_skills),
                    ("preferred", match.missing_preferred_skills),
                )
                for skill in skills
            }
            for gap in state["skill_gaps"]:
                key = (normalize_skill(gap.skill), gap.requirement_type)
                if key not in missing or not _evidence_mentions(gap.jd_evidence, gap.skill):
                    issues.append(f"skill_gaps:{gap.skill}:missing JD support")

        candidate = state["candidate_profile"]
        candidate_evidence = {
            (item.source_id, item.quote, item.locator)
            for item in (candidate.evidence if candidate else [])
        }
        gap_skills = {normalize_skill(gap.skill) for gap in state["skill_gaps"]}
        for index, suggestion in enumerate(state["resume_suggestions"]):
            if any(
                (item.source_id, item.quote, item.locator) not in candidate_evidence
                for item in suggestion.candidate_evidence
            ):
                issues.append(
                    f"resume_suggestions:{index}:candidate evidence is not in the resume profile"
                )
            if any(_mentions(suggestion.suggested_text, skill) for skill in gap_skills):
                issues.append(
                    f"resume_suggestions:{index}:suggestion presents a missing skill as experience"
                )

        chunks = {document.chunk_id: document for document in state["retrieved_context"]}
        gap_index = {normalize_skill(gap.skill) for gap in state["skill_gaps"]}
        plan = state["learning_plan"]
        if plan:
            for index, task in enumerate(plan.tasks):
                if normalize_skill(task.skill) not in gap_index:
                    issues.append(f"learning_plan:{index}:task is not tied to a skill gap")
                    continue
                documents = [chunks.get(chunk_id) for chunk_id in task.source_chunk_ids]
                if any(document is None for document in documents) or not any(
                    normalize_skill(task.skill) in normalize_skill(document.content)
                    for document in documents
                    if document is not None
                ):
                    issues.append(f"learning_plan:{index}:sources do not support the task skill")
        return issues


def repair_target(issues: list[str]) -> str | None:
    for prefix in ("match_results", "skill_gaps", "learning_plan", "resume_suggestions"):
        if any(issue.startswith(prefix + ":") for issue in issues):
            return prefix
    return None


def _evidence_mentions(evidence: list[EvidenceRef], skill: str) -> bool:
    return any(_mentions(item.quote, normalize_skill(skill)) for item in evidence)


def _mentions(text: str, normalized_skill: str) -> bool:
    haystack = normalize_text(text)
    needle = normalize_text(normalized_skill)
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack) is not None
