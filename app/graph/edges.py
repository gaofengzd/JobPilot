"""Deterministic learning and bounded reflection routes."""

from typing import Literal

from app.graph.state import JobPilotState


def route_learning(
    state: JobPilotState,
) -> Literal["retrieve_knowledge", "optimize_resume"]:
    if state["need_advice"] and state["skill_gaps"]:
        return "retrieve_knowledge"
    return "optimize_resume"


def route_reflection(
    state: JobPilotState,
    *,
    max_repair_attempts: int = 2,
) -> Literal["final_report", "repair_outputs", "finalize_reflection_failure"]:
    if not state["validation_issues"]:
        return "final_report"
    if state["repair_target"] is not None and state["retry_count"] < max_repair_attempts:
        return "repair_outputs"
    return "finalize_reflection_failure"
