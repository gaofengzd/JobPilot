"""Create source-traceable learning tasks without inventing references."""

from app.schemas.gap import SkillGap
from app.schemas.learning import LearningPlan, LearningTask, RetrievedDocument
from app.utils.resume_files import normalize_text

EMPTY_RETRIEVAL_WARNING = "知识库素材不足，该技能差距保留，未生成缺乏依据的学习任务。"


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
                    objective=f"掌握岗位要求的 {gap.skill} 基础知识，并完成一次可验证的练习。",
                    actions=[
                        f"阅读 {source.source} 中的 {gap.skill} 相关材料。" for source in sources
                    ]
                    + [f"基于上述材料完成一个最小的 {gap.skill} 练习，并记录结果。"],
                    deliverable=f"一个可运行的最小 {gap.skill} 示例与学习笔记。",
                    source_chunk_ids=[source.chunk_id for source in sources],
                )
            )
        if gaps and not tasks and not warnings:
            warnings.append(EMPTY_RETRIEVAL_WARNING)
        return LearningPlan(job_index=job_index, tasks=tasks, warnings=warnings)
