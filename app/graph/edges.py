"""Day 7 deterministic routing; retry and reflection routes start on Day 8."""

from typing import Literal

from app.graph.state import JobPilotState


def route_learning(
    state: JobPilotState,
) -> Literal["retrieve_knowledge", "optimize_resume"]:
    if state["need_advice"] and state["skill_gaps"]:
        return "retrieve_knowledge"
    return "optimize_resume"
