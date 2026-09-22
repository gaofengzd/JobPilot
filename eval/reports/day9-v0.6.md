# JobPilot v0.6 Evaluation Report

- Generated: 2026-09-22T06:55:15.833879+00:00
- Mode: `full`
- Base cases: 33
- Duration: 334.651 seconds

## Metrics

- Matching exact cases: 10/10
- Matching precision/recall: 1.0000/1.0000
- Citation support: 5/5
- RAG Hit@1: 5/5
- RAG Hit@4: 5/5
- JD exact cases: 10/10
- Required P/R/F1: 1.0000/1.0000/1.0000
- Preferred P/R/F1: 1.0000/1.0000/1.0000
- Structured output first-valid: 13/13
- Tool success: 2/2
- Workflow status counts: success=1, partial=0, failed=0

## Baseline comparison

- matching_exact_case_rate: baseline=1.0, current=1.0, delta=0.0
- rag_hit_at_1: baseline=1.0, current=1.0, delta=0.0
- rag_hit_at_4: baseline=1.0, current=1.0, delta=0.0
- workflow_live_success_rate: baseline=1.0, current=1.0, delta=0.0

## Current failures

- None in this run.

## Repeatability observations

- first-full: structured=12/13, JD exact=9/10, failure=data-engineer grounding rejected unsupported data qualityB
- final-full: structured=13/13, JD exact=10/10, failure=None

## Failure analyses

### glm-string-null

- Observed: GLM-4.7 returned the literal string null for optional JD fields.
- Root cause: Compatible structured output did not consistently preserve JSON null semantics.
- Fix: Normalize a small allowlist of optional placeholder values only when absent from source text.
- Regression: `tests/test_jd_analyzer.py::test_optional_string_null_placeholder_is_normalized`
- Provenance: docs/decisions.md ADR-011

### windows-unicode-evidence

- Observed: A Unicode arrow in match evidence raised UnicodeEncodeError on a GBK Windows console.
- Root cause: Machine-generated evidence used a character unsupported by the active console encoding.
- Fix: Use the ASCII <-> separator for generated evidence.
- Regression: `matching eval case and Day 4 output test`
- Provenance: docs/decisions.md Day 4 Windows output compatibility

### glm-intermittent-structured-output

- Observed: A real --analyze-job call returned StructuredOutputError although the same sample later succeeded.
- Root cause: Provider output was nondeterministic and did not contain exactly one valid schema tool call.
- Fix: Keep strict validation and safe failure; Day 8 added bounded business repair without relaxing the schema.
- Regression: `eval/datasets/error_cases.json#day3-live-intermittent-structured-output`
- Provenance: docs/decisions.md Day 3 live nondeterminism observation

### day9-live-grounding-mutation

- Observed: The first Day 9 full run returned data qualityB for a JD keyword and Python grounding rejected the case; the complete rerun passed 10/10.
- Root cause: The provider produced a nondeterministic suffix that was absent from the source JD.
- Fix: Keep exact grounding, count the first call as failed, continue the batch, and retain the case for repeatability analysis.
- Regression: `eval/datasets/error_cases.json#day9-live-jd-grounding-mutation`
- Provenance: Day 9 first full report on 2026-09-22

## Limitations

- The five-query RAG set is too small to establish broad retrieval quality.
- Citation Support uses stored human labels and does not infer truth from overlap.
- Cost is unknown because no reviewed price table is configured.
- A one-request live workflow rate is evidence of that run, not a reliability claim.
