"""Run deterministic checks required before packaging JobPilot v1.0."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

REQUIRED_PATHS = (
    "app/api/main.py",
    "app/api/routes/health.py",
    "app/graph/workflow.py",
    "app/schemas/report.py",
    "eval/reports/day9-v0.6.json",
    "docs/architecture/overview.md",
    "docs/release/demo-script.md",
    "docs/release/project-description.md",
    "docs/release/interview-qa.md",
    "ui/app.py",
    "Dockerfile",
    "uv.lock",
)


def _tracked_files(root: Path) -> set[str]:
    try:
        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {line.replace("\\", "/") for line in completed.stdout.splitlines()}


def check_release(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_PATHS:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        if project.get("version") != "1.0.0":
            errors.append("pyproject version must be 1.0.0")
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"invalid pyproject.toml: {exc}")

    try:
        report = json.loads((root / "eval/reports/day9-v0.6.json").read_text(encoding="utf-8"))
        if report.get("report_version") != "0.6":
            errors.append("formal evaluation report must remain version 0.6")
        if report.get("dataset", {}).get("base_case_count") != 33:
            errors.append("formal evaluation report must contain 33 base cases")
        if not report.get("failure_analyses"):
            errors.append("formal evaluation report must retain failure analyses")
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        errors.append(f"invalid formal evaluation report: {exc}")

    tracked = _tracked_files(root)
    for forbidden in (".env", ".env.local"):
        if forbidden in tracked:
            errors.append(f"secret file is tracked: {forbidden}")

    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    for marker in ("FROM python:3.11", "HEALTHCHECK", "uvicorn", "requirements.txt"):
        if marker not in dockerfile:
            errors.append(f"Dockerfile missing marker: {marker}")

    openapi_paths = {
        "/health",
        "/resume/parse",
        "/jobs/analyze",
        "/jobs/batch",
        "/agent/run",
    }
    try:
        from app.api.main import create_app

        actual_paths = set(create_app().openapi()["paths"])
        missing_paths = sorted(openapi_paths - actual_paths)
        if missing_paths:
            errors.append(f"API paths missing: {', '.join(missing_paths)}")
    except Exception as exc:  # pragma: no cover - environment/import failure report
        errors.append(f"cannot inspect API OpenAPI document: {exc}")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = check_release(root)
    if errors:
        print("RELEASE CHECK FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("RELEASE CHECK PASSED: v1.0.0 metadata, files, report, Docker, and API paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
