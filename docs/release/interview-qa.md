# JobPilot Interview Questions

## Why is matching calculated in Python?

Coverage, partitions, scores, denominators, and evidence constraints must be
repeatable and testable. The model is used for extraction and bounded tool
selection, not as an authority for numeric business rules.

## Why use LangGraph?

The workflow has explicit state, conditional advice routing, bounded repair,
and a final validation boundary. LangGraph makes those transitions inspectable
without turning every module into an independent agent.

## Why is the RAG knowledge base limited?

It supplies curated learning references for verified gaps. It does not need to
cover every profession because it is not the source of job facts or candidate
skills. An empty or unsupported retrieval result remains an explicit warning.

## Why FastAPI and Streamlit?

FastAPI provides typed contracts and OpenAPI for the service boundary.
Streamlit is a small demonstration client. A product UI can later be replaced
by React/Next.js without moving business rules out of the API.

## What are the main failure boundaries?

Unsupported facts, invalid evidence, model/configuration failures, upload
limits, and retrieval failures are surfaced as controlled errors or partial
reports. The system does not silently fill missing facts or substitute a
different job when the selected job fails.
