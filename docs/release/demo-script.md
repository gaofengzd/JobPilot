# JobPilot v1.0 Demo Script

This script is the repeatable three-minute demonstration. It is a runbook, not
a claim that a recording has been produced.

## Before the demo

1. Copy `.env.example` to `.env` and set the GLM-4.7 key and local BGE paths.
2. Start the API with `uv run --locked uvicorn app.api.main:app --host 127.0.0.1 --port 8000`.
3. Start the UI with `uv run --locked streamlit run ui/app.py`.
4. Open the Streamlit URL and confirm `GET /health` returns `status=ok`.

## Walkthrough

1. Paste the de-identified resume and five sample JDs.
2. Select a target job and start analysis.
3. Show the candidate profile and evidence, then compare required/preferred
   skill coverage for all five jobs.
4. Show the selected job's gaps, JD evidence, retrieved learning sources, and
   resume suggestions. Explain that score and coverage are calculated in Python.
5. Open `eval/reports/day9-v0.6.md` and show the metrics plus three failure
   analyses. Mention that the full report used real GLM/BGE in its recorded run.
6. Demonstrate a controlled invalid input, such as an empty resume or an
   unsupported upload, and show the explicit error instead of a fabricated report.

The demo must not claim Docker or a live model run unless that run was executed
in the environment being presented.
