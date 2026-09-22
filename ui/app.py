"""Thin Streamlit client for the existing JobPilot API."""

import os

import requests
import streamlit as st

API_URL = os.getenv("JOBPILOT_API_URL", "http://127.0.0.1:8000").rstrip("/")


def _render_report(report: dict) -> None:
    st.subheader("分析报告")
    st.write(f"状态：{report.get('status', 'unknown')}")
    selected = report.get("selected_job_index")
    jobs = report.get("job_profiles", [])
    matches = report.get("match_results", [])
    if selected is not None and selected < len(jobs):
        st.write(f"目标岗位：{jobs[selected].get('title', f'岗位 {selected + 1}')}")
    selected_match = next((item for item in matches if item.get("job_index") == selected), None)
    if selected_match:
        st.metric("匹配分数", selected_match.get("overall_score", "-"))
        st.write("已匹配必需技能：", selected_match.get("matched_required_skills", []))
        st.write("缺失必需技能：", selected_match.get("missing_required_skills", []))
        st.write("已匹配优先技能：", selected_match.get("matched_preferred_skills", []))
    if report.get("skill_gaps"):
        st.write("能力差距", report["skill_gaps"])
    if report.get("learning_plan"):
        st.write("学习计划", report["learning_plan"])
    if report.get("warnings"):
        st.warning("；".join(report["warnings"]))
    if report.get("errors"):
        st.error("；".join(report["errors"]))


def main() -> None:
    st.set_page_config(page_title="JobPilot", page_icon="🎯", layout="wide")
    st.title("JobPilot 岗位分析")
    st.caption(f"API：{API_URL}")
    resume_file = st.file_uploader("上传简历（Markdown/TXT/PDF）", type=["md", "txt", "pdf"])
    resume_text = st.text_area("或直接粘贴简历", height=180)
    job_texts = [
        st.text_area(f"岗位 JD {index + 1}", height=130, key=f"job_{index}") for index in range(5)
    ]
    selected_job_index = st.number_input("目标岗位编号", min_value=1, max_value=5, value=1) - 1
    need_advice = st.checkbox("生成学习与简历建议", value=True)
    if st.button("开始分析", type="primary"):
        if resume_file is not None:
            resume_text = resume_file.getvalue().decode("utf-8", errors="replace")
        jobs = [text.strip() for text in job_texts if text.strip()]
        if not resume_text.strip():
            st.error("请提供简历内容。")
            return
        if len(jobs) != 5:
            st.error("请填写 5 个岗位 JD。")
            return
        payload = {
            "resume_text": resume_text,
            "raw_jobs": jobs,
            "selected_job_index": int(selected_job_index),
            "need_advice": need_advice,
        }
        try:
            response = requests.post(f"{API_URL}/agent/run", json=payload, timeout=180)
            response.raise_for_status()
        except requests.RequestException as exc:
            st.error(f"API 请求失败：{exc}")
            return
        _render_report(response.json())


if __name__ == "__main__":
    main()
