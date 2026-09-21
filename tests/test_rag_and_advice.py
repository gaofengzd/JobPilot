"""Day 6 learning-only RAG, planning, and resume suggestion tests."""

import json
from pathlib import Path

import pytest

from app.agents.learning_planner import EMPTY_RETRIEVAL_WARNING, LearningPlanner
from app.agents.resume_optimizer import ResumeOptimizer
from app.core.exceptions import RetrievalError
from app.rag.loader import KnowledgeDocument, load_knowledge_documents
from app.rag.splitter import split_documents
from app.rag.vectorstore import FaissVectorStore
from app.schemas.candidate import CandidateProfile
from app.schemas.common import EvidenceRef
from app.schemas.gap import SkillGap
from app.schemas.job import JobProfile

RAG_CASES = Path(__file__).parents[1] / "eval" / "datasets" / "rag_cases.json"


class KeywordEmbedding:
    model_id = "keyword-test-v1"

    def embed_documents(self, texts):
        vectors = []
        for text in texts:
            lowered = text.casefold()
            vectors.append(
                [
                    float("fastapi" in lowered),
                    float("docker" in lowered),
                    float("langgraph" in lowered),
                    float("postgresql" in lowered),
                    float("rag" in lowered),
                    float(
                        not any(
                            word in lowered
                            for word in ("fastapi", "docker", "langgraph", "postgresql", "rag")
                        )
                    ),
                ]
            )
        return vectors


def gap(skill: str, priority: int = 1) -> SkillGap:
    return SkillGap(
        skill=skill,
        requirement_type="required",
        reason="Resume does not mention this required JD skill.",
        evidence_status="not_mentioned",
        jd_evidence=[
            EvidenceRef(source_id="job:0", quote=f"Required skills: {skill}", locator="line:1")
        ],
        priority=priority,
    )


def test_loader_reads_supported_utf8_files_in_stable_order(tmp_path):
    (tmp_path / "b.txt").write_text("Docker guide", encoding="utf-8")
    (tmp_path / "a.md").write_text("# FastAPI", encoding="utf-8")
    (tmp_path / "ignored.json").write_text("{}", encoding="utf-8")
    documents = load_knowledge_documents(tmp_path)
    assert [(item.doc_id, item.source) for item in documents] == [
        ("a", "a.md"),
        ("b", "b.txt"),
    ]


def test_loader_rejects_missing_directory_and_invalid_utf8(tmp_path):
    with pytest.raises(RetrievalError, match="does not exist"):
        load_knowledge_documents(tmp_path / "missing")
    (tmp_path / "bad.txt").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(RetrievalError, match="UTF-8"):
        load_knowledge_documents(tmp_path)


def test_splitter_preserves_metadata_and_overlap():
    text = " ".join(f"token{i}" for i in range(10))
    chunks = split_documents(
        [KnowledgeDocument(doc_id="guide", source="guide.md", content=text)],
        chunk_size=5,
        chunk_overlap=2,
    )
    assert [chunk.chunk_id for chunk in chunks] == ["guide:0", "guide:1", "guide:2"]
    assert chunks[0].content.split()[-2:] == chunks[1].content.split()[:2]


def test_splitter_rejects_invalid_configuration():
    with pytest.raises(RetrievalError):
        split_documents([], chunk_size=10, chunk_overlap=10)


def test_faiss_retrieval_returns_traceable_top_k():
    chunks = split_documents(
        [
            KnowledgeDocument("fastapi", "fastapi.md", "FastAPI dependency injection"),
            KnowledgeDocument("docker", "docker.md", "Docker container image"),
        ]
    )
    store = FaissVectorStore(KeywordEmbedding())
    store.build(chunks)
    results = store.search("learn Docker", top_k=1)
    assert store.size == 2
    assert results[0].doc_id == "docker"
    assert results[0].chunk_id == "docker:0"
    assert results[0].source == "docker.md"
    assert results[0].score == pytest.approx(1.0)


def test_empty_store_and_score_threshold_degrade_to_empty():
    store = FaissVectorStore(KeywordEmbedding())
    store.build([])
    assert store.search("Docker") == []

    chunks = split_documents([KnowledgeDocument("docker", "docker.md", "Docker guide")])
    store.build(chunks)
    assert store.search("unrelated topic", min_score=0.5) == []


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_query_is_rejected(query):
    store = FaissVectorStore(KeywordEmbedding())
    with pytest.raises(RetrievalError, match="must not be empty"):
        store.search(query)


def test_invalid_embedding_output_is_rejected():
    class BrokenEmbedding:
        model_id = "broken"

        def embed_documents(self, texts):
            return []

    store = FaissVectorStore(BrokenEmbedding())
    chunks = split_documents([KnowledgeDocument("doc", "doc.md", "content")])
    with pytest.raises(RetrievalError, match="vector count"):
        store.build(chunks)


def test_learning_plan_references_only_retrieved_chunks_and_orders_priority():
    store = FaissVectorStore(KeywordEmbedding())
    store.build(
        split_documents(
            [
                KnowledgeDocument("docker", "docker.md", "Docker container practice"),
                KnowledgeDocument("langgraph", "langgraph.md", "LangGraph state practice"),
            ]
        )
    )
    documents = store.search("Docker", top_k=2) + store.search("LangGraph", top_k=2)
    plan = LearningPlanner().plan(
        job_index=3,
        gaps=[gap("Docker", 2), gap("LangGraph", 1)],
        documents=documents,
    )
    assert plan.job_index == 3
    assert [task.skill for task in plan.tasks] == ["LangGraph", "Docker"]
    available = {document.chunk_id for document in documents}
    assert all(set(task.source_chunk_ids) <= available for task in plan.tasks)


def test_learning_plan_empty_retrieval_returns_warning_without_fake_task():
    plan = LearningPlanner().plan(job_index=0, gaps=[gap("UnknownSkill")], documents=[])
    assert plan.tasks == []
    assert EMPTY_RETRIEVAL_WARNING in plan.warnings[0]


def test_resume_optimizer_uses_only_existing_evidence_and_supported_skills():
    evidence = EvidenceRef(
        source_id="resume:test",
        quote="Built a Python API with FastAPI",
        locator="line:4",
    )
    candidate = CandidateProfile(skills=["Python", "FastAPI"], evidence=[evidence])
    job = JobProfile(
        job_index=0,
        title="Backend Engineer",
        required_skills=["Python", "PostgreSQL"],
        preferred_skills=["FastAPI"],
    )
    suggestions = ResumeOptimizer().optimize(candidate, job, [gap("PostgreSQL")])
    assert len(suggestions) == 1
    assert suggestions[0].original_text == evidence.quote
    assert suggestions[0].candidate_evidence == [evidence]
    assert "PostgreSQL" not in suggestions[0].suggested_text
    assert "Python" in suggestions[0].suggested_text
    assert "FastAPI" in suggestions[0].suggested_text


def test_resume_optimizer_returns_empty_without_candidate_evidence():
    candidate = CandidateProfile(skills=["Python"])
    job = JobProfile(job_index=0, title="Engineer", required_skills=["Python"])
    assert ResumeOptimizer().optimize(candidate, job, []) == []


def test_rag_eval_dataset_has_five_human_labeled_cases():
    cases = json.loads(RAG_CASES.read_text(encoding="utf-8"))
    assert len(cases) == 5
    assert all(case["expected_doc_ids"] for case in cases)
