"""JobPilot verification and incremental command-line entry point."""

import argparse
import json
from pathlib import Path

from app.agents.gap_analyzer import GapAnalyzer
from app.agents.jd_analyzer import JDAnalyzer
from app.agents.learning_planner import LearningPlanner
from app.agents.resume_optimizer import ResumeOptimizer
from app.agents.resume_parser import ResumeParser
from app.business.batch_analyzer import BatchAnalyzer
from app.business.matching_engine import MatchingEngine
from app.core.config import load_settings
from app.core.exceptions import JobGroundingError, JobPilotError
from app.core.logging import configure_logging
from app.graph.demo import build_demo_dependencies
from app.graph.state import create_initial_state
from app.graph.workflow import build_default_workflow, build_workflow
from app.rag.retriever import KnowledgeRetriever
from app.schemas.candidate import CandidateProfile, Project
from app.schemas.common import Contract, EvidenceRef, NonEmptyText
from app.schemas.gap import SkillGap
from app.schemas.job import JobProfile
from app.services.embedding import BGEEmbeddingClient
from app.services.llm import LLMClient
from app.utils.resume_files import load_resume


class ConnectionCheck(Contract):
    message: NonEmptyText


def main() -> int:
    parser = argparse.ArgumentParser(description="JobPilot incremental verification")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check-llm", action="store_true", help="Make one real model request")
    actions.add_argument(
        "--parse-resume",
        metavar="PATH",
        help="Parse one PDF, Markdown, or TXT resume with the configured model",
    )
    actions.add_argument(
        "--analyze-job",
        metavar="PATH",
        help="Analyze one UTF-8 job description with the configured model",
    )
    actions.add_argument(
        "--match-demo",
        action="store_true",
        help="Run deterministic Day 4 matching without a model request",
    )
    actions.add_argument(
        "--run-workflow",
        nargs="+",
        metavar="PATH",
        help="Run the real workflow: first path is a resume, remaining paths are JDs",
    )
    actions.add_argument(
        "--demo-v05",
        action="store_true",
        help="Run the offline Day 8 Tool/Reflection workflow demonstration",
    )
    actions.add_argument(
        "--demo-v04",
        action="store_true",
        help="Run the offline Day 7 LangGraph workflow demonstration",
    )
    actions.add_argument(
        "--demo-v03",
        action="store_true",
        help="Run the Day 6 local BGE, FAISS, learning, and resume advice demo",
    )
    actions.add_argument(
        "--eval-rag",
        action="store_true",
        help="Run the five-case local BGE and FAISS Hit@K baseline",
    )
    actions.add_argument(
        "--demo-v02",
        action="store_true",
        help="Run the offline Day 5 five-job match, gap, and batch demo",
    )
    actions.add_argument(
        "--demo-v01",
        nargs=2,
        metavar=("RESUME_PATH", "JOB_PATH"),
        help="Parse one resume and one job description into structured profiles",
    )
    parser.add_argument(
        "--selected-job-index",
        type=int,
        default=0,
        help="Original JD index selected for workflow details",
    )
    parser.add_argument(
        "--no-advice",
        action="store_true",
        help="Skip the workflow learning retrieval branch",
    )
    args = parser.parse_args()
    try:
        settings = load_settings()
        configure_logging(settings.log_level)
        if args.parse_resume:
            document = load_resume(args.parse_resume)
            profile = ResumeParser(LLMClient(settings)).parse_document(document)
            print(profile.model_dump_json(indent=2))
            return 0
        if args.analyze_job:
            job_text, source_id = _read_job(args.analyze_job)
            profile = JDAnalyzer(LLMClient(settings)).analyze(
                job_text, job_index=0, source_id=source_id
            )
            print(profile.model_dump_json(indent=2))
            return 0
        if args.match_demo:
            candidate = CandidateProfile(
                skills=["python3", "FastAPI"],
                projects=[
                    Project(
                        name="Campus API",
                        description="REST API for course search",
                        technologies=["Python", "FastAPI"],
                    )
                ],
            )
            job = JobProfile(
                job_index=0,
                title="Backend Engineer",
                required_skills=["Python", "FastAPI", "PostgreSQL"],
                preferred_skills=["Docker"],
                responsibilities=["Build and maintain REST APIs"],
            )
            embedding = BGEEmbeddingClient(
                settings.embedding_model_path, device=settings.embedding_device
            )
            result = MatchingEngine(embedding).match(candidate, job)
            print(result.model_dump_json(indent=2))
            return 0
        if args.run_workflow:
            if len(args.run_workflow) < 2:
                raise JobGroundingError(
                    "--run-workflow needs one resume path and at least one JD path."
                )
            resume_path, *job_paths = args.run_workflow
            raw_jobs = [_read_job(path)[0] for path in job_paths]
            state = create_initial_state(
                resume_path=resume_path,
                raw_jobs=raw_jobs,
                selected_job_index=args.selected_job_index,
                need_advice=not args.no_advice,
                max_jobs=settings.max_jobs,
            )
            result = build_default_workflow(settings).invoke(state)
            print(result["final_report"].model_dump_json(indent=2))
            return 0
        if args.demo_v05 or args.demo_v04:
            state = create_initial_state(
                resume_text="Built a Python API with FastAPI",
                raw_jobs=["backend", "agent"],
                selected_job_index=1,
                need_advice=True,
                max_jobs=settings.max_jobs,
            )
            result = build_workflow(build_demo_dependencies()).invoke(state)
            report = result["final_report"]
            print(
                json.dumps(
                    {
                        "mode": "offline-synthetic",
                        "version": "0.5" if args.demo_v05 else "0.4",
                        "graph_status": result["status"],
                        "retry_count": result["retry_count"],
                        "validation_issues": result["validation_issues"],
                        "report": report.model_dump(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.eval_rag or args.demo_v03:
            embedding = BGEEmbeddingClient(
                settings.embedding_model_path, device=settings.embedding_device
            )
            retriever = KnowledgeRetriever(embedding)
            chunk_count = retriever.index_directory(settings.knowledge_dir)
            if args.eval_rag:
                from eval.evaluators.rag_eval import evaluate_hit_at_k

                cases_path = Path("eval/datasets/rag_cases.json")
                cases = json.loads(cases_path.read_text(encoding="utf-8"))
                report = {
                    "hit_at_1": evaluate_hit_at_k(retriever.store, cases, top_k=1),
                    "hit_at_4": evaluate_hit_at_k(retriever.store, cases, top_k=4),
                }
                report["chunk_count"] = chunk_count
                report["embedding_model"] = embedding.model_id
                report["reranker_used"] = False
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 0

            candidate_evidence = EvidenceRef(
                source_id="resume:demo",
                quote="Built a Python API with FastAPI",
                locator="line:1",
            )
            candidate = CandidateProfile(
                skills=["Python", "FastAPI"],
                evidence=[candidate_evidence],
            )
            job = JobProfile(
                job_index=0,
                title="AI Backend Engineer",
                required_skills=["Python", "Docker", "LangGraph"],
                preferred_skills=["FastAPI"],
            )
            gaps = [
                SkillGap(
                    skill=skill,
                    requirement_type="required",
                    reason="Resume does not mention this required JD skill.",
                    evidence_status="not_mentioned",
                    jd_evidence=[
                        EvidenceRef(
                            source_id="job:demo",
                            quote=f"Required skills: {skill}",
                            locator="line:2",
                        )
                    ],
                    priority=1,
                )
                for skill in ("Docker", "LangGraph")
            ]
            retrieved = []
            for gap in gaps:
                retrieved.extend(retriever.retrieve(gap))
            documents = list({item.chunk_id: item for item in retrieved}.values())
            plan = LearningPlanner().plan(
                job_index=job.job_index,
                gaps=gaps,
                documents=documents,
            )
            suggestions = ResumeOptimizer().optimize(candidate, job, gaps)
            print(
                json.dumps(
                    {
                        "version": "0.3",
                        "embedding_model": embedding.model_id,
                        "reranker_used": False,
                        "indexed_chunks": chunk_count,
                        "skill_gaps": [item.model_dump() for item in gaps],
                        "retrieved_context": [item.model_dump() for item in documents],
                        "learning_plan": plan.model_dump(),
                        "resume_suggestions": [item.model_dump() for item in suggestions],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.demo_v02:
            candidate = CandidateProfile(skills=["Python", "FastAPI", "Docker"])
            specifications = [
                (["Python", "FastAPI", "PostgreSQL"], ["Docker"]),
                (["Python", "SQL", "Airflow"], ["Docker"]),
                (["Python", "LangGraph", "RAG"], ["FastAPI"]),
                (["Linux", "Kubernetes", "Terraform"], ["Python", "SQL"]),
            ]
            jobs = [
                JobProfile(
                    job_index=index,
                    title=f"Synthetic Job {index + 1}",
                    required_skills=required,
                    preferred_skills=preferred,
                    evidence=[
                        EvidenceRef(
                            source_id=f"job:{index}",
                            quote="Required skills: " + ", ".join(required),
                            locator="line:1",
                        ),
                        EvidenceRef(
                            source_id=f"job:{index}",
                            quote="Preferred skills: " + ", ".join(preferred),
                            locator="line:2",
                        ),
                    ],
                )
                for index, (required, preferred) in enumerate(specifications)
            ]
            engine = MatchingEngine()
            matches = [engine.match(candidate, job) for job in jobs]
            selected = max(
                matches,
                key=lambda item: item.score if item.score is not None else -1,
            )
            selected_job = next(job for job in jobs if job.job_index == selected.job_index)
            output = {
                "version": "0.2",
                "total_jobs": 5,
                "job_errors": {"4": "Synthetic invalid JD excluded before analysis."},
                "matches": [
                    item.model_dump()
                    for item in sorted(
                        matches,
                        key=lambda item: item.score if item.score is not None else -1,
                        reverse=True,
                    )
                ],
                "selected_job_index": selected.job_index,
                "skill_gaps": [
                    item.model_dump() for item in GapAnalyzer().analyze(selected_job, selected)
                ],
                "batch_statistics": BatchAnalyzer()
                .analyze(candidate, jobs, total_jobs=5)
                .model_dump(),
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0
        if args.demo_v01:
            resume_path, job_path = args.demo_v01
            llm = LLMClient(settings)
            candidate = ResumeParser(llm).parse_document(load_resume(resume_path))
            job_text, source_id = _read_job(job_path)
            job = JDAnalyzer(llm).analyze(job_text, job_index=0, source_id=source_id)
            print(
                json.dumps(
                    {
                        "candidate_profile": candidate.model_dump(),
                        "job_profile": job.model_dump(),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        state = create_initial_state(
            resume_text="Synthetic sample: Python",
            raw_jobs=["Synthetic Python JD"],
            max_jobs=settings.max_jobs,
        )
        candidate = CandidateProfile(skills=["Python"])
        if args.check_llm:
            result = LLMClient(settings).structured(
                ConnectionCheck,
                instruction="Return a structured object with message set to jobpilot-ok.",
                text="This is a synthetic connectivity check, not a resume.",
                request_id=state["request_id"],
            )
            if result.message != "jobpilot-ok":
                print(json.dumps({"status": "failed", "error": "Unexpected smoke response"}))
                return 1
            print(json.dumps({"status": "ok", "mode": "live", "message": result.message}))
        else:
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "mode": "offline",
                        "schema": candidate.model_dump(),
                        "state_status": state["status"],
                        "note": "No model request was made. Business workflow is not implemented.",
                    },
                    ensure_ascii=False,
                )
            )
        return 0
    except JobPilotError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1


def _read_job(path_value: str) -> tuple[str, str]:
    path = Path(path_value)
    if not path.is_file():
        raise JobGroundingError("Job description file does not exist or is not a file.")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raise JobGroundingError("Job description must be valid UTF-8 text.") from None
    except OSError:
        raise JobGroundingError("Job description file could not be read.") from None
    return text, f"job:{path.name}"


if __name__ == "__main__":
    raise SystemExit(main())
