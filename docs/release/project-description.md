# Project Description

## Resume bullet

Built JobPilot, a LangGraph-based job analysis Agent that parses resumes and
job descriptions into grounded Pydantic profiles, computes deterministic skill
coverage and gaps across batches, and produces citation-backed learning and
resume suggestions through a bounded local BGE/FAISS retrieval branch. Exposed
the workflow through FastAPI and a Streamlit demo, with 33-case evaluation,
strict evidence validation, controlled Tool Calling, Reflection, and Docker
startup configuration.

## Short project summary

JobPilot helps a job seeker compare one resume with several positions. GLM-4.7
extracts structured facts, while Python owns matching, scoring, validation, and
error boundaries. RAG is used only for learning resources related to verified
skill gaps; it never invents candidate experience.
