"""Deterministic fact reflection over existing structured workflow output."""

from app.business.matching_engine import match_key
from app.graph.state import JobPilotState
from app.schemas.common import EvidenceRef
from app.utils.resume_files import mentions_term


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
            expected_required = {match_key(item) for item in job.required_skills}
            actual_required = {
                match_key(item)
                for item in (match.matched_required_skills + match.missing_required_skills)
            }
            expected_preferred = {match_key(item) for item in job.preferred_skills}
            actual_preferred = {
                match_key(item)
                for item in (match.matched_preferred_skills + match.missing_preferred_skills)
            }
            if expected_required != actual_required or expected_preferred != actual_preferred:
                issues.append(f"match_results:job:{index}:skill partitions contradict JD")

        if selected in jobs and selected in matches:
            job = jobs[selected]
            match = matches[selected]
            missing = {
                (match_key(skill), requirement_type)
                for requirement_type, skills in (
                    ("required", match.missing_required_skills),
                    ("preferred", match.missing_preferred_skills),
                )
                for skill in skills
            }
            for gap in state["skill_gaps"]:
                key = (match_key(gap.skill), gap.requirement_type)
                if key not in missing or not _evidence_mentions(gap.jd_evidence, gap.skill):
                    issues.append(f"skill_gaps:{gap.skill}:missing JD support")

        candidate = state["candidate_profile"]
        candidate_evidence = {
            (item.source_id, item.quote, item.locator)
            for item in (candidate.evidence if candidate else [])
        }
        gap_skills = {match_key(gap.skill) for gap in state["skill_gaps"]}
        for index, suggestion in enumerate(state["resume_suggestions"]):
            if any(
                (item.source_id, item.quote, item.locator) not in candidate_evidence
                for item in suggestion.candidate_evidence
            ):
                issues.append(
                    f"resume_suggestions:{index}:candidate evidence is not in the resume profile"
                )
            if any(mentions_term(suggestion.suggested_text, skill) for skill in gap_skills):
                issues.append(
                    f"resume_suggestions:{index}:suggestion presents a missing skill as experience"
                )

        chunks = {document.chunk_id: document for document in state["retrieved_context"]}
        gap_index = {match_key(gap.skill) for gap in state["skill_gaps"]}
        plan = state["learning_plan"]
        if plan:
            for index, task in enumerate(plan.tasks):
                if match_key(task.skill) not in gap_index:
                    issues.append(f"learning_plan:{index}:task is not tied to a skill gap")
                    continue
                documents = [chunks.get(chunk_id) for chunk_id in task.source_chunk_ids]
                if any(document is None for document in documents) or not any(
                    mentions_term(document.content, task.skill) for document in documents
                ):
                    issues.append(f"learning_plan:{index}:sources do not support the task skill")
        return issues


def repair_target(issues: list[str]) -> str | None:
    for prefix in ("match_results", "skill_gaps", "learning_plan", "resume_suggestions"):
        if any(issue.startswith(prefix + ":") for issue in issues):
            return prefix
    return None


def _evidence_mentions(evidence: list[EvidenceRef], skill: str) -> bool:
    return any(mentions_term(item.quote, skill) for item in evidence)
