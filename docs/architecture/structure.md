# 目录职责与实施阶段

| 目录 | 职责 | 开始实现 |
|---|---|---|
| app/core | 配置、日志、异常 | Day 1 |
| app/services | LLM / Embedding 基础设施客户端 | Day 1 / 4 |
| app/schemas | 统一 Pydantic 数据契约 | Day 1 |
| app/graph | State 与节点、边、工作流 | State Day 1，其余 Day 7–8 |
| app/agents | 解析、Gap、建议、Reflection 业务模块；不是多 Agent | Day 2–8 |
| app/business | 确定性匹配和批量统计 | Day 4–5 |
| app/tools | 五个薄 Tool 适配器 | 对应业务完成后接入 |
| app/rag | Loader、分块、向量存储与检索 | Day 6 |
| app/api/routes | 健康检查及四个业务接口，agent/jobs/resume 三组路由 | Day 10–11 |
| app/utils | 仅存放必要的通用辅助代码 | 按实际需求 |
| eval/datasets | 脱敏输入、人工期望、失败案例 | Day 1 建结构，Day 2 起积累 |
| eval/evaluators | 抽取、匹配、RAG 评测 | Day 9 集中完善 |
| eval/reports | 真实评测结果 | 实际评测后生成 |
| tests | 规则与模块测试 | 模块实现时加入 |
| data/knowledge | 人工整理的学习资料 | Day 6 |
| data/sample_jobs | 脱敏岗位样例 | Day 3 |
| data/sample_resumes | 脱敏简历样例 | Day 2 |
| ui | Streamlit 薄客户端页面 | Day 11 |
| docs/architecture | 架构与目录说明 | 当前已建 |
| scripts | 发布前确定性检查 | Day 12 |

空目录使用 .gitkeep 保留。所有 Python 占位只包含模块说明，没有虚假功能。
