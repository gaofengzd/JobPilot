"""Create source-traceable learning tasks without inventing references."""

from app.schemas.gap import SkillGap
from app.schemas.learning import LearningPlan, LearningTask, RetrievedDocument
from app.utils.resume_files import normalize_text

EMPTY_RETRIEVAL_WARNING = (
    "Knowledge base has insufficient material; the gap remains and no unsupported task was created."
)


class LearningPlanner:
    def plan(
        self,
        *,
        job_index: int,
        gaps: list[SkillGap],
        documents: list[RetrievedDocument],
    ) -> LearningPlan:
        tasks: list[LearningTask] = []
        warnings: list[str] = []
        seen_chunks: set[str] = set()
        unique_documents = [
            document
            for document in documents
            if not (document.chunk_id in seen_chunks or seen_chunks.add(document.chunk_id))
        ]

        for gap in sorted(gaps, key=lambda item: (item.priority, item.skill.casefold())):
            needle = normalize_text(gap.skill)
            sources = [
                document
                for document in unique_documents
                if needle in normalize_text(document.content)
            ][:2]
            if not sources:
                warnings.append(f"{gap.skill}: {EMPTY_RETRIEVAL_WARNING}")
                continue
            tasks.append(
                LearningTask(
                    skill=gap.skill,
                    priority=gap.priority,
                    objective=(
                        f"Learn the {gap.skill} fundamentals required by the job "
                        "and complete a verifiable exercise."
                    ),
                    actions=[
                        f"Read the {gap.skill} material in {source.source}." for source in sources
                    ]
                    + [
                        f"Build a minimal {gap.skill} exercise from the source "
                        "and record its result."
                    ],
                    deliverable=f"A runnable minimal {gap.skill} example and learning notes.",
                    source_chunk_ids=[source.chunk_id for source in sources],
                )
            )
        if gaps and not tasks and not warnings:
            warnings.append(EMPTY_RETRIEVAL_WARNING)
        return LearningPlan(job_index=job_index, tasks=tasks, warnings=warnings)
