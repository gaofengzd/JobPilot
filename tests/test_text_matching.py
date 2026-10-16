"""Shared term matching, and the gap/reflection contract that depends on it."""

import pytest

from app.agents.gap_analyzer import GapAnalyzer
from app.agents.reflection import Reflection
from app.schemas.common import EvidenceRef
from app.schemas.job import JobProfile
from app.schemas.match import MatchResult
from app.utils.resume_files import mentions_term


@pytest.mark.parametrize(
    ("term", "text", "expected"),
    [
        # Chinese is written without separators, so an embedded phrase must match.
        (
            "软件测试标准与规范的落地应用技能",
            "1、熟悉软件测试标准与规范的落地应用技能；",
            True,
        ),
        ("重大项目测试全流程管理技能", "2、具备重大项目测试全流程管理技能；", True),
        (
            "军工单位或航天领域质量相关工作经验",
            "6、有军工单位或航天领域质量相关工作经验者优先。",
            True,
        ),
        ("软件测试标准与规范的落地应用技能", "软件测试标准与规范的落地应用技能", True),
        ("测试", "软件测试标准", True),
        # An ASCII alphanumeric edge stays guarded, so a Latin fragment is not a term.
        ("Java", "Required skills: JavaScript, React", False),
        ("SQL", "熟悉MySQL数据库", False),
        # The guard must not reject a real term beside Chinese or a separator.
        ("Java", "Required skills: Java, React", True),
        ("Jmeter", "Required skills: Jmeter/LoadRunner", True),
        ("Postman", "熟悉 Postman 工具", True),
        ("Python", "熟悉Python开发", True),
        # Model spacing may disagree with the source spacing.
        ("Pos tman", "熟悉 Postman 工具", True),
        ("", "anything", False),
    ],
)
def test_mentions_term_only_requires_a_boundary_beside_ascii_words(term, text, expected):
    assert mentions_term(text, term) is expected


def _job_and_match(lines: list[str], required: list[str], preferred: list[str]):
    evidence = [
        EvidenceRef(source_id="job:0", quote=quote, locator=f"line:{index}")
        for index, quote in enumerate(lines, start=1)
    ]
    job = JobProfile(
        job_index=0,
        title="测试工程师",
        required_skills=required,
        preferred_skills=preferred,
        evidence=evidence,
    )
    match = MatchResult(
        job_index=0,
        matched_required_skills=[],
        missing_required_skills=required,
        matched_preferred_skills=[],
        missing_preferred_skills=preferred,
        required_skill_coverage=0.0,
        preferred_skill_coverage=0.0,
        project_similarity=0.0,
        project_similarity_available=False,
        evidence=[],
        score=0.0,
    )
    return job, match


def _issues_for(job: JobProfile, match: MatchResult) -> list[str]:
    gaps = GapAnalyzer().analyze(job, match)
    return Reflection().validate(
        {
            "job_profiles": [job],
            "match_results": [match],
            "selected_job_index": 0,
            "skill_gaps": gaps,
            "candidate_profile": None,
            "resume_suggestions": [],
            "retrieved_context": [],
            "learning_plan": None,
        }
    )


def test_chinese_skill_gap_evidence_survives_validation():
    """A Chinese JD wraps its skills in prose; every attached gap must validate.

    Regression: GapAnalyzer attached evidence with a normalized substring test
    while Reflection re-checked the same pair with a word-boundary regex.  A whole
    Chinese sentence is one ``\\w+`` token, so the boundary always failed and every
    Chinese skill was reported as "missing JD support".  Two repairs could not
    converge because they re-ran the same deterministic gap analysis, so the
    workflow ended in ``partial`` and pruned the gaps, learning plan, and advice.
    """
    required = [
        "软件测试标准与规范的落地应用技能",
        "重大项目测试全流程管理技能",
        "测试环境与工具运维管理技能",
        "软件专项测试技术实施技能",
        "软件质量保证与过程管控技能",
    ]
    preferred = ["军工单位或航天领域质量相关工作经验"]
    lines = [
        "1、熟悉软件测试标准与规范的落地应用技能；",
        "2、具备重大项目测试全流程管理技能；",
        "3、熟悉测试环境与工具运维管理技能；",
        "4、掌握软件专项测试技术实施技能；",
        "5、熟悉软件质量保证与过程管控技能；",
        "6、有军工单位或航天领域质量相关工作经验者优先。",
    ]
    job, match = _job_and_match(lines, required, preferred)
    assert _issues_for(job, match) == []


def test_gap_evidence_attachment_agrees_with_validation():
    """Reflection must accept every gap the analyzer attaches.

    The repair loop only converges while attachment and validation share one
    predicate, so this mixes Chinese, Latin, and CJK-adjacent skills in one case.
    """
    required = [
        "Python",
        "熟悉Python开发",
        "软件测试标准与规范的落地应用技能",
        "Jmeter",
        "Postman",
    ]
    preferred = ["军工单位或航天领域质量相关工作经验"]
    lines = [
        "1、熟悉Python开发与软件测试标准与规范的落地应用技能；",
        "2、Required skills: Jmeter, Postman",
        "3、有军工单位或航天领域质量相关工作经验者优先。",
    ]
    job, match = _job_and_match(lines, required, preferred)
    assert _issues_for(job, match) == []


def test_latin_fragment_evidence_is_still_reported_by_validation():
    """The ASCII guard stays in force: a `JavaScript` line does not support `Java`.

    GapAnalyzer keeps a lenient fallback so the tested "lacks JD evidence" contract
    cannot newly fire, which is why the validator still has to surface this pair.
    """
    job, match = _job_and_match(["Required skills: JavaScript, React"], ["Java"], [])
    assert _issues_for(job, match) == ["skill_gaps:Java:missing JD support"]
