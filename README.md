# JobPilot

智能求职岗位分析 Agent。项目事实来源：[开发文档](docs/开发文档.md)。

当前迭代：**Day 4 Matching Engine**。Gap、批量分析、RAG、Graph 编排、API、UI 尚未实现。
GLM-4.7 已用三份合成简历和十条合成 JD 完成真实结构化调用验证；离线测试与真实服务结果分开记录。

## uv 环境与依赖

要求 Python 3.11；项目使用 uv，虚拟环境位于 .venv。
已通过 uv init 初始化，uv add 管理依赖，uv.lock 固定解析结果。

```powershell
uv python install 3.11
uv sync --locked
uv run --locked python main.py
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```

main.py 默认只运行合成数据的本地 Schema / State 检查，不调用模型，不启动 API。
uv sync 在新机器自动创建 .venv；无需手动激活即可使用 uv run。

新增依赖使用 uv add；开发依赖使用 uv add --dev。
仅在有明确需要时升级。requirements.txt 从锁文件导出，禁止手工维护：

```powershell
uv export --locked --no-dev --no-hashes --format requirements-txt --output-file requirements.txt
```

## 真实模型验证

将 .env.example 复制为 .env，在本地填写 LLM_MODEL 和 LLM_API_KEY。
自定义接口设置 LLM_BASE_URL；默认接口则不设置该项。
当前模型配置为智普 GLM-4.7，使用 OpenAI 兼容地址和 `function_calling` 生成 Pydantic 结构化输出。
不使用仅面向 OpenAI 原生接口的 `json_schema` 请求格式，也不在失败时静默切换方法。
当前适配器为 langchain-openai，只承诺已测试的标准协议路径；
具体服务兼容性须经真实调用确认，不能宣称任意服务均可用。

```powershell
uv run --locked python main.py --check-llm
```

此命令发起一次真实请求，只发送固定合成连通性样例。成功必须返回 jobpilot-ok。
未配置模型或密钥时返回清晰错误和退出码 1；不会临时读取其他项目凭据。
密钥不提交 Git，日志只保存调用元数据，不保存简历、prompt、回复或原始异常。

## 当前实现

- app/core：环境配置、明确异常、白名单 JSON 日志。
- app/schemas：CandidateProfile、JobProfile、MatchResult、Gap、LearningPlan、
  BatchStatistics、FinalReport，以及输入/证据等模型。
- app/graph/state.py：全部状态字段、校验输入、独立默认值与 request_id。
- app/services/llm.py：单一结构化模型客户端、超时、显式方法选择、安全错误。
- app/utils/resume_files.py：UTF-8 Markdown/TXT 与文本层 PDF 读取、大小限制和行级定位。
- app/agents/resume_parser.py：CandidateProfile 结构化抽取、逐字段原文约束和证据校验。
- app/agents/jd_analyzer.py：JobProfile 抽取、required/preferred 明示标记校验、证据 grounding。
- app/business/matching_engine.py：确定性技能匹配、覆盖率、项目相似度、证据与可选总分。
- app/services/embedding.py：固定版本的本地哈希 Embedding 基线，无网络调用。
- tests：契约与基础设施测试，均不依赖真实网络。
- eval/datasets/error_cases.json：Day 1 异常案例；其余数据集留待后续积累。

模型计分、事实 Reflection、工具执行循环与整个请求时间预算不在此阶段实现。
Dockerfile、API、UI 和后续模块仅占位。

## 协作与记录

每次先读 [进度](docs/progress.md)、[决策](docs/decisions.md)、
[开发文档](docs/开发文档.md) 和相关代码。
每完成一部分功能，立即更新进度和决策记录；AGENTS.md 已固化此规则。

[目录职责](docs/architecture/structure.md)。
参考：[uv 项目初始化](https://docs.astral.sh/uv/concepts/projects/init/)、
[Pydantic 验证器](https://docs.pydantic.dev/latest/concepts/validators/)、
[LangChain 模型适配器](https://docs.langchain.com/oss/python/integrations/chat/openai)。

### Windows 临时目录权限问题

若 pytest 报系统 pytest-of-用户名 目录 PermissionError，可在项目根目录使用以下两条命令，
给本次测试分配独立目录，不更改系统权限：

    $testTemp = Join-Path (Get-Location) ('.pytest_cache/verify-' + [guid]::NewGuid().ToString('N'))
    uv run --locked pytest -q --basetemp $testTemp


## Day 2 简历解析

支持 UTF-8 编码的 `.md`、`.txt` 和带文本层的 `.pdf`，单文件上限 5 MB。扫描件和 OCR 不在 v1.0 Day 2 范围内。

```powershell
uv run --locked python main.py --parse-resume data/sample_resumes/candidate_backend.md
uv run --locked python main.py --parse-resume data/sample_resumes/candidate_data.txt
uv run --locked python main.py --parse-resume data/sample_resumes/candidate_agent.pdf
```

命令会调用已配置模型输出 `CandidateProfile` JSON。LLM 只负责抽取，Python 会拒绝原文中不存在的字段值、缺失证据或无效引用，并重建 `source_id` 和定位信息。


## Day 3 岗位解析与 v0.1

单条 JD 以 UTF-8 文本文件输入。LLM 负责语义抽取，Python 固定 `job_index`、校验原文事实、required/preferred 明示标记和证据定位。

```powershell
uv run --locked python main.py --analyze-job data/sample_jobs/backend-python.txt
uv run --locked python main.py --demo-v01 data/sample_resumes/candidate_backend.md data/sample_jobs/backend-python.txt
```

`--demo-v01` 依次生成 `CandidateProfile` 和 `JobProfile`，不执行匹配或评分。十条岗位样例位于 `data/sample_jobs`，期望结果位于 `eval/datasets/jd_cases.json`。


## Day 4 确定性匹配

Matching Engine 接收已验证的 `CandidateProfile` 和 `JobProfile`，不调用 LLM。技能仅使用候选画像的 `skills` 字段，通过显式别名字典匹配；项目相关性使用固定 `local-hash-v1` 向量和 Python cosine。

```powershell
uv run --locked python main.py --match-demo
```

输出包含 matched/missing、required/preferred coverage、项目相似度、可读证据和按可用维度重新归一化的分数。分数是固定规则的匹配指标，不是录用概率。`local-hash-v1` 是可复现的词法相关性基线，不等同于通用语义 Embedding。

## 本地 Embedding 与重排模型

- 当前项目相似度使用 `bge-large-zh-v1.5`，默认目录：`E:/00project/02agent/models/bge-large-zh-v1.5`。
- 后续 RAG 继续复用该 Embedding。
- 重排尚未实现；Day 6 先建立向量检索基线，仅在 eval 证明排序不足时使用 `bge-reranker-v2-m3`，默认目录：`E:/00project/02agent/models/bge-reranker-v2-m3`。
- 两个模型目录都不提交 Git，运行时不自动下载，也不静默切换其他模型。

首次加载 CPU 模型可能需要较长时间；同一进程内模型实例会缓存。
