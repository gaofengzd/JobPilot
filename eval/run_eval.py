"""Reproducible Day 9 evaluation runner for deterministic, local, and live checks."""

import argparse
import json
import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from app.agents.jd_analyzer import JDAnalyzer
from app.agents.resume_parser import ResumeParser
from app.core.config import load_settings
from app.core.exceptions import JobPilotError
from app.graph.state import create_initial_state
from app.graph.workflow import build_default_workflow
from app.rag.retriever import KnowledgeRetriever
from app.services.embedding import BGEEmbeddingClient
from app.services.llm import LLMClient
from app.utils.resume_files import load_resume
from eval.evaluators.extraction_eval import (
    evaluate_jd_extraction,
    evaluate_resume_extraction,
)
from eval.evaluators.match_eval import evaluate_matching
from eval.evaluators.rag_eval import evaluate_citation_support, evaluate_hit_at_k

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "eval" / "datasets"
DEFAULT_REPORT = ROOT / "eval" / "reports" / "day9-v0.6"


class EvaluationLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run JobPilot v0.6 evaluation")
    parser.add_argument(
        "--mode",
        choices=("deterministic", "local", "full"),
        default="local",
        help="local adds real BGE/FAISS; full also calls configured GLM and Tool workflow",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=DEFAULT_REPORT,
        help="Write <prefix>.json and <prefix>.md",
    )
    args = parser.parse_args()
    report = run_evaluation(args.mode)
    write_report(report, args.output_prefix)
    print(json.dumps(_console_summary(report, args.output_prefix), ensure_ascii=False, indent=2))
    return 0 if not report["failures"] else 1


def run_evaluation(mode: str) -> dict:
    started = perf_counter()
    resume_cases = _load("resume_cases.json")
    jd_cases = _load("jd_cases.json")
    matching_cases = _load("matching_cases.json")
    rag_cases = _load("rag_cases.json")
    error_cases = _load("error_cases.json")
    citation_cases = _load("citation_cases.json")
    analyses = _load("failure_analyses.json")
    workflow_cases = _load("workflow_cases.json")
    batch_cases = _load("batch_cases.json")
    inventory = {
        "resume": len(resume_cases),
        "jd": len(jd_cases),
        "matching": len(matching_cases),
        "rag": len(rag_cases),
        "citation": len(citation_cases),
        "batch": len(batch_cases),
        "workflow": len(workflow_cases),
        "error_regressions": len(error_cases),
    }
    base_count = (
        len(resume_cases)
        + len(jd_cases)
        + len(matching_cases)
        + len(rag_cases)
        + min(5, len(error_cases))
    )
    metrics: dict[str, object] = {
        "matching": evaluate_matching(matching_cases),
        "citation_support": evaluate_citation_support(citation_cases),
    }
    runtime: dict[str, object] = {
        "mode": mode,
        "llm_calls_performed": False,
        "embedding_inference_performed": False,
    }
    failures = [{"area": "matching", **failure} for failure in metrics["matching"]["failures"]]

    if mode in {"local", "full"}:
        settings = load_settings()
        embedding = BGEEmbeddingClient(
            settings.embedding_model_path, device=settings.embedding_device
        )
        retriever = KnowledgeRetriever(embedding)
        indexed_chunks = retriever.index_directory(settings.knowledge_dir)
        hit_at_1 = evaluate_hit_at_k(retriever.store, rag_cases, top_k=1)
        hit_at_4 = evaluate_hit_at_k(retriever.store, rag_cases, top_k=4)
        metrics["rag"] = {"hit_at_1": hit_at_1, "hit_at_4": hit_at_4}
        runtime.update(
            embedding_inference_performed=True,
            embedding_model=embedding.model_id,
            indexed_chunks=indexed_chunks,
            reranker_used=False,
        )
        failures.extend(
            {"area": "rag", "id": case["id"], "metric": metric["metric"]}
            for metric in (hit_at_1, hit_at_4)
            for case in metric["cases"]
            if not case["hit"]
        )

    if mode == "full":
        live_metrics, live_runtime, live_failures = _run_live(resume_cases, jd_cases)
        metrics.update(live_metrics)
        runtime.update(live_runtime)
        failures.extend(live_failures)

    current = _comparison_values(metrics)
    baseline = json.loads((ROOT / "eval" / "baselines" / "v0.5.json").read_text(encoding="utf-8"))
    comparison = {
        key: {
            "baseline": baseline["metrics"].get(key),
            "current": value,
            "delta": (
                value - baseline["metrics"][key]
                if key in baseline["metrics"] and value is not None
                else None
            ),
        }
        for key, value in current.items()
    }
    return {
        "report_version": "0.6",
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "dataset": {
            "inventory": inventory,
            "base_case_count": base_count,
            "base_definition": "3 resume + 10 JD + 10 matching + 5 RAG + 5 error",
            "expectations": "human-authored synthetic or de-identified labels",
        },
        "metrics": metrics,
        "runtime": runtime,
        "baseline": baseline,
        "baseline_comparison": comparison,
        "failures": failures,
        "failure_analyses": analyses,
        "duration_seconds": round(perf_counter() - started, 3),
        "limitations": [
            "The five-query RAG set is too small to establish broad retrieval quality.",
            "Citation Support uses stored human labels and does not infer truth from overlap.",
            "Cost is unknown because no reviewed price table is configured.",
            "A one-request live workflow rate is evidence of that run, not a reliability claim.",
        ],
    }


def _run_live(resume_cases: list[dict], jd_cases: list[dict]) -> tuple[dict, dict, list]:
    settings = load_settings()
    llm = LLMClient(settings)
    handler = EvaluationLogHandler()
    previous_level = llm.logger.level
    llm.logger.setLevel(logging.INFO)
    llm.logger.addHandler(handler)
    resume_predictions: dict[str, dict] = {}
    jd_predictions: dict[str, dict] = {}
    failures = []
    latencies = []
    try:
        for case in resume_cases:
            started = perf_counter()
            try:
                profile = ResumeParser(llm).parse_document(load_resume(ROOT / case["file"]))
                resume_predictions[case["id"]] = {
                    "skills": profile.skills,
                    "project_names": [item.name for item in profile.projects],
                    "education_schools": [item.school for item in profile.education],
                }
            except JobPilotError as exc:
                failures.append(_runtime_failure("resume_extraction", case["id"], exc))
            latencies.append(perf_counter() - started)
        for index, case in enumerate(jd_cases):
            started = perf_counter()
            try:
                profile = JDAnalyzer(llm).analyze(
                    case["text"],
                    job_index=index,
                    source_id=f"eval:job:{case['id']}",
                    request_id=f"eval-jd-{index}",
                )
                jd_predictions[case["id"]] = profile.model_dump()
            except JobPilotError as exc:
                failures.append(_runtime_failure("jd_extraction", case["id"], exc))
            latencies.append(perf_counter() - started)

        workflow_started = perf_counter()
        workflow_status = "failed"
        try:
            workflow = build_default_workflow(settings)
            result = workflow.invoke(
                create_initial_state(
                    resume_path=str(ROOT / resume_cases[0]["file"]),
                    raw_jobs=[jd_cases[0]["text"]],
                    selected_job_index=0,
                    need_advice=True,
                )
            )
            workflow_status = result["final_report"].status
            if workflow_status != "success":
                failures.append(
                    {"area": "workflow", "id": "live-backend", "status": workflow_status}
                )
        except JobPilotError as exc:
            failures.append(_runtime_failure("workflow", "live-backend", exc))
        workflow_latency = perf_counter() - workflow_started
    finally:
        llm.logger.removeHandler(handler)
        llm.logger.setLevel(previous_level)

    extraction_total = len(resume_cases) + len(jd_cases)
    extraction_success = len(resume_predictions) + len(jd_predictions)
    events = Counter(record.getMessage() for record in handler.records)
    token_totals = {
        field: sum(getattr(record, field, 0) or 0 for record in handler.records)
        for field in ("input_tokens", "output_tokens", "total_tokens")
    }
    tool_started = events["tool.started"]
    tool_completed = events["tool.completed"]
    metrics = {
        "resume_extraction": evaluate_resume_extraction(resume_cases, resume_predictions),
        "jd_extraction": evaluate_jd_extraction(jd_cases, jd_predictions),
        "structured_output": {
            "first_schema_valid": extraction_success,
            "calls": extraction_total,
            "first_schema_valid_rate": extraction_success / extraction_total,
            "retry_after_failure": "not_run",
        },
        "tool_success": {
            "successful": tool_completed,
            "actual_calls": tool_started,
            "value": tool_completed / tool_started if tool_started else None,
        },
        "workflow": {
            "success": int(workflow_status == "success"),
            "partial": int(workflow_status == "partial"),
            "failed": int(workflow_status == "failed"),
            "requests": 1,
            "success_rate": float(workflow_status == "success"),
        },
    }
    runtime = {
        "llm_calls_performed": True,
        "llm_model": settings.llm_model,
        "extraction_calls": extraction_total,
        "extraction_successes": extraction_success,
        "average_extraction_latency_seconds": (
            sum(latencies) / len(latencies) if latencies else None
        ),
        "workflow_latency_seconds": workflow_latency,
        "observed_token_usage": token_totals,
        "token_scope": "Only calls whose provider response exposed usage metadata.",
        "cost": None,
        "cost_reason": "No reviewed price table is configured.",
    }
    return metrics, runtime, failures


def write_report(report: dict, prefix: Path) -> None:
    prefix = prefix if prefix.is_absolute() else ROOT / prefix
    prefix.parent.mkdir(parents=True, exist_ok=True)
    _report_path(prefix, ".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _report_path(prefix, ".md").write_text(_markdown(report), encoding="utf-8")


def _markdown(report: dict) -> str:
    metrics = report["metrics"]
    matching = metrics["matching"]
    citation = metrics["citation_support"]
    lines = [
        "# JobPilot v0.6 Evaluation Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Mode: `{report['mode']}`",
        f"- Base cases: {report['dataset']['base_case_count']}",
        f"- Duration: {report['duration_seconds']} seconds",
        "",
        "## Metrics",
        "",
        f"- Matching exact cases: {matching['exact_cases']}/{matching['cases']}",
        f"- Matching precision/recall: {matching['precision']:.4f}/{matching['recall']:.4f}",
        f"- Citation support: {citation['supported']}/{citation['checked']}",
    ]
    if "rag" in metrics:
        hit_at_1 = metrics["rag"]["hit_at_1"]
        hit_at_4 = metrics["rag"]["hit_at_4"]
        lines.extend(
            [
                f"- RAG Hit@1: {hit_at_1['hits']}/{hit_at_1['total']}",
                f"- RAG Hit@4: {hit_at_4['hits']}/{hit_at_4['total']}",
            ]
        )
    if "jd_extraction" in metrics:
        jd = metrics["jd_extraction"]
        structured = metrics["structured_output"]
        tool = metrics["tool_success"]
        workflow = metrics["workflow"]
        lines.extend(
            [
                f"- JD exact cases: {jd['exact_cases']}/{jd['cases']}",
                f"- Required P/R/F1: {_prf(jd['required'])}",
                f"- Preferred P/R/F1: {_prf(jd['preferred'])}",
                "- Structured output first-valid: "
                f"{structured['first_schema_valid']}/{structured['calls']}",
                f"- Tool success: {tool['successful']}/{tool['actual_calls']}",
                "- Workflow status counts: "
                f"success={workflow['success']}, partial={workflow['partial']}, "
                f"failed={workflow['failed']}",
            ]
        )
    lines.extend(["", "## Baseline comparison", ""])
    for name, item in report["baseline_comparison"].items():
        lines.append(
            f"- {name}: baseline={item['baseline']}, current={item['current']}, "
            f"delta={item['delta']}"
        )
    lines.extend(["", "## Current failures", ""])
    if report["failures"]:
        lines.extend(
            f"- `{item.get('area')}/{item.get('id')}`: {item}" for item in report["failures"]
        )
    else:
        lines.append("- None in this run.")
    if report.get("repeatability_observations"):
        lines.extend(["", "## Repeatability observations", ""])
        lines.extend(
            f"- {item['run']}: structured={item['structured_output']}, "
            f"JD exact={item['jd_exact']}, failure={item['failure']}"
            for item in report["repeatability_observations"]
        )
    lines.extend(["", "## Failure analyses", ""])
    for item in report["failure_analyses"]:
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"- Observed: {item['observed']}",
                f"- Root cause: {item['root_cause']}",
                f"- Fix: {item['fix']}",
                f"- Regression: `{item['regression']}`",
                f"- Provenance: {item['provenance']}",
                "",
            ]
        )
    lines.extend(["## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def _comparison_values(metrics: dict) -> dict[str, float | None]:
    matching = metrics["matching"]
    values = {
        "matching_exact_case_rate": matching["exact_cases"] / matching["cases"],
    }
    if "rag" in metrics:
        values.update(
            rag_hit_at_1=metrics["rag"]["hit_at_1"]["value"],
            rag_hit_at_4=metrics["rag"]["hit_at_4"]["value"],
        )
    if "workflow" in metrics:
        values["workflow_live_success_rate"] = metrics["workflow"]["success_rate"]
    return values


def _console_summary(report: dict, prefix: Path) -> dict:
    return {
        "version": report["report_version"],
        "mode": report["mode"],
        "base_cases": report["dataset"]["base_case_count"],
        "failures": len(report["failures"]),
        "json_report": str(_report_path(prefix, ".json")),
        "markdown_report": str(_report_path(prefix, ".md")),
    }


def _runtime_failure(area: str, case_id: str, exc: Exception) -> dict:
    return {"area": area, "id": case_id, "error_type": type(exc).__name__, "error": str(exc)}


def _load(name: str) -> list[dict]:
    data = json.loads((DATASETS / name).read_text(encoding="utf-8"))
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise ValueError(f"{name} must contain a JSON list of objects")
    ids = [item.get("id") for item in data]
    if any(not isinstance(item, str) or not item.strip() for item in ids):
        raise ValueError(f"{name} contains an invalid id")
    if len(ids) != len(set(ids)):
        raise ValueError(f"{name} contains duplicate ids")
    return data


def _prf(metric: dict) -> str:
    return f"{metric['precision']:.4f}/{metric['recall']:.4f}/{metric['f1']:.4f}"


def _report_path(prefix: Path, extension: str) -> Path:
    return Path(str(prefix) + extension)


if __name__ == "__main__":
    raise SystemExit(main())
