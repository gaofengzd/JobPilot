"""JobPilot verification and incremental command-line entry point."""

import argparse
import json

from app.agents.resume_parser import ResumeParser
from app.core.config import load_settings
from app.core.exceptions import JobPilotError
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
    args = parser.parse_args()
    try:
        settings = load_settings()
        configure_logging(settings.log_level)
        if args.parse_resume:
            document = load_resume(args.parse_resume)
            profile = ResumeParser(LLMClient(settings)).parse_document(document)
            print(profile.model_dump_json(indent=2))
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


if __name__ == "__main__":
    raise SystemExit(main())
