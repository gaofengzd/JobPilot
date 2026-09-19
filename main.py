"""JobPilot verification and incremental command-line entry point."""

import argparse
import json
from pathlib import Path

from app.agents.jd_analyzer import JDAnalyzer
from app.agents.resume_parser import ResumeParser
from app.core.config import load_settings
from app.core.exceptions import JobGroundingError, JobPilotError
from app.core.logging import configure_logging
from app.graph.state import create_initial_state
from app.schemas.candidate import CandidateProfile
from app.schemas.common import Contract, NonEmptyText
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
        "--demo-v01",
        nargs=2,
        metavar=("RESUME_PATH", "JOB_PATH"),
        help="Parse one resume and one job description into structured profiles",
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
