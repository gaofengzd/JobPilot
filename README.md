# JobPilot

智能求职岗位分析 Agent。项目事实来源：[开发文档](docs/开发文档.md)。

当前版本：**v1.0 / Day 12 交付候选**。项目包含 FastAPI API、Vue 3 + TypeScript 前端、LangGraph 工作流、受控本地 RAG、33 条基础评测和 Docker API 启动配置。Streamlit 页面已退役，不再维护。
GLM-4.7 与本地 `bge-large-zh-v1.5` 的真实结果、确定性测试和未运行项目分开记录；当前正式评测报告为 `eval/reports/day9-v0.6.{json,md}`。

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

## 运行日志与可观测性

后端会将 JSON 日志同时打印到终端并保存到项目目录 `log/jobpilot.log`，覆盖 API 请求、服务初始化、LangGraph 节点、模型请求、响应耗时、模型地址、token、内容长度和 SHA-256 摘要。`log/` 已加入 Git 忽略。

默认不记录简历、JD、Prompt 或模型原文。如需本地排障时临时记录最多 2000 字符的模型输入/输出预览，在启动后端的同一个 CMD 窗口设置：

```cmd
set LOG_CAPTURE_CONTENT=true
```

排障完成后关闭该选项并删除 `log/jobpilot.log`，避免个人信息长期留存：

```cmd
set LOG_CAPTURE_CONTENT=false
del /q log\jobpilot.log
```

简历抽取若触发原文校验失败，日志会额外记录未通过校验的字段和值（最多 2000 字符），即使 `LOG_CAPTURE_CONTENT=false` 也会记录，以便定位模型改写或拼接。岗位（JD）抽取的原文校验失败同样会记录 `jobs.grounding.failed`，包含 `request_id`、`job_index`、`grounding_issue`、未通过字段和值摘要；由于 `analyze_jobs` 会把单条失败写入 `job_errors`，这类事件是定位“选定岗位无法分析”的主要依据。API 错误响应只返回通用提示；请将 `log/jobpilot.log` 当作包含简历敏感信息的文件保管，并在排障后删除。

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
密钥不提交 Git；普通模型日志只保存调用元数据。简历抽取 grounding 失败时会按前述规则将未通过字段和值写入本地日志。

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
- app/agents/gap_analyzer.py：将缺失技能转换为可追溯 JD 证据的 SkillGap。
- app/business/batch_analyzer.py：按有效岗位统计技能频率、高频缺失项和失败数。
- app/rag：受控知识加载、可追踪分块、本地 BGE、FAISS 向量检索。
- app/agents/learning_planner.py：只使用检索 chunk 生成可追溯学习任务。
- app/agents/resume_optimizer.py：只根据候选人证据生成最小措辞建议。
- app/services/embedding.py：从固定本地路径加载 bge-large-zh-v1.5，无网络下载。
- tests：契约、基础设施、解析、匹配、Gap、批量统计和 RAG 离线测试。
- app/tools：5 个带 Pydantic 参数的薄 Tool；计算与检索仍由既有业务模块执行。
- app/agents/reflection.py：按固定事实规则定位 Match、Gap、简历建议和学习来源问题。
- app/api：FastAPI 应用、四个业务端点、健康检查、进程内共享依赖、受控上传和异常映射。
- eval/datasets：持续积累抽取、匹配、批量、RAG、工作流和失败案例。
- frontend：Vue 3 + TypeScript + Vite 薄客户端，只调用 `/agent/run` 并展示 `FinalReport`。
- docs/architecture、docs/release：架构图、Demo 脚本、项目描述和面试问答。
- scripts/check_release.py：发布前的确定性文件、版本、评测、Docker 和 API 检查。

模型不负责计分或事实 Reflection。整个请求的统一墙钟时间预算、认证、队列和持久化不属于 v1.0。

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

### required/preferred 明示标记

技能只有在 JD 明确标记时才归类，required 与 preferred 都支持两种版式：

- **同行标记**：`Required skills: Python`、`Preferred skills: Redis`。
- **分节标题**：标题单独占一行，其后各行属于该节，直到出现下一个标题。例如 `任职要求：` 后的编号条款，或 `加分项：` 后的加分技能。标题可带中英文冒号或句末标点。

中文标记：required 接受 `任职要求`、`岗位要求`、`职位要求`、`任职资格`、`硬性要求`、`必备`、`必须`；preferred 接受 `加分项`、`加分`、`优先`。某一行若自带相反标记（例如 `任职要求` 段落里的「…的优先」条款），该行按自己的标记归类。匹配前只保留可见文字，空格与标点不影响判定。


## Day 4 确定性匹配

Matching Engine 接收已验证的 `CandidateProfile` 和 `JobProfile`，不调用 LLM。技能仅使用候选画像的 skills 字段，通过显式别名字典匹配；项目相关性使用本地 bge-large-zh-v1.5 向量和 Python cosine。

```powershell
uv run --locked python main.py --match-demo
```

输出包含 matched/missing、required/preferred coverage、项目相似度、可读证据和按可用维度重新归一化的分数。分数是固定规则的匹配指标，不是录用概率。

## 本地 Embedding 与重排模型

- 当前项目相似度使用 `bge-large-zh-v1.5`，默认目录：`E:/00project/02agent/models/bge-large-zh-v1.5`。
- 后续 RAG 继续复用该 Embedding。
- 重排尚未实现；Day 6 先建立向量检索基线，仅在 eval 证明排序不足时使用 `bge-reranker-v2-m3`，默认目录：`E:/00project/02agent/models/bge-reranker-v2-m3`。
- 两个模型目录都不提交 Git，运行时不自动下载，也不静默切换其他模型。

首次加载 CPU 模型可能需要较长时间；同一进程内模型实例会缓存。

## Day 5 Gap 与批量分析

GapAnalyzer 将 MatchingEngine 的缺失技能转换为 SkillGap。每项 Gap 必须能绑定原岗位的 JD 证据；必需技能优先级为 1，优先技能为 2。“未在简历体现”不解释为用户绝对不会。

BatchAnalyzer 对成功解析的岗位按规范技能逐岗位去重，分别统计 required、preferred 和岗位并集频率。ratio 的分母只使用 valid_jobs，失败岗位单独显示；初始高频阈值为 0.5。

    uv run --locked python main.py --demo-v02

该离线演示使用 5 个合成岗位输入，其中 4 个有效、1 个模拟解析失败；输出岗位排名、所选岗位 Gap 和批量统计。不调用 LLM，也不加载 Embedding 模型。

## Day 6 学习 RAG 与建议

RAG 仅用于 Gap 到学习建议。人工维护的 Markdown/TXT 资料经过确定性分块，由本地 bge-large-zh-v1.5 生成归一化向量，并用 FAISS IndexFlatIP 检索。RetrievedDocument 保留来源、文档 ID、chunk ID 和检索分数。

固定 5 条人工标注检索案例的真实本地基线为 Hit@1=5/5、Hit@4=5/5，因此本迭代没有接入 bge-reranker-v2-m3。LearningPlanner 只引用检索结果；空检索返回 warning。ResumeOptimizer 只改写候选人已有证据，不把 Gap 写成已有经历。

    uv run --locked python main.py --eval-rag
    uv run --locked python main.py --demo-v03

两个命令均加载本地 BGE。--eval-rag 输出固定检索基线；--demo-v03 输出 Docker/LangGraph Gap、检索来源、学习任务与一条有候选人证据的简历建议，不调用 LLM。

## Day 7 LangGraph 工作流

工作流顺序为 validate_input → parse_resume → analyze_jobs → calculate_matches → calculate_statistics → analyze_gap。只有 selected job 存在 Gap 且 need_advice=true 时才进入 retrieve_knowledge → learning_plan，然后统一执行 optimize_resume → final_report。

每条 JD 保留原始 job_index；单条失败进入 job_errors，不会使后续岗位错位。选定岗位失败时返回 partial/failed 报告和明确错误，不混用其他岗位的 Gap。Retriever 通过工厂延迟创建，无 Gap 或关闭建议时不会加载知识库或 BGE。

    uv run --locked python main.py --demo-v04
    uv run --locked python main.py --run-workflow data/sample_resumes/candidate_backend.md data/sample_jobs/backend-python.txt

--demo-v04 是不调用模型和 Embedding 的合成离线 Graph 演示。--run-workflow 使用已配置 GLM、本地 BGE 和知识库执行真实工作流；可附加 --selected-job-index N 或 --no-advice。

## Day 8 Tool Calling、Reflection 与修复

主干仍由 Graph 固定控制。学习分支中，真实工作流让 GLM 根据已验证 Gap 请求 `retrieve_knowledge_tool`；Python 校验参数、执行本地 BGE/FAISS 检索，并用同一 `tool_call_id` 将结果返回模型。参数最多修复一次，不允许开放工具循环。离线演示直接执行同一 Tool，不伪装为模型调用。

Reflection 使用 Python 规则依次检查匹配分区、Gap 的 JD 依据、简历建议的候选人证据和学习任务来源。只重建有问题的产物，整个请求最多修复两次；仍不合格时删除未通过的建议并返回 partial。

    uv run --locked python main.py --demo-v05
    uv run --locked python main.py --run-workflow data/sample_resumes/candidate_backend.md data/sample_jobs/backend-python.txt

`--demo-v05` 是确定性离线验证。`--run-workflow` 才会使用已配置 GLM 进行真实 Tool Calling，并加载本地 BGE/FAISS。

## Day 9 Evaluation 与 v0.6

评测器读取人工期望，不把当前模型输出写回标准答案。三个模式分别用于纯 Python、真实本地 BGE，以及真实 GLM + BGE + Tool/Workflow；报告同时生成 JSON 和 Markdown。

    uv run --locked python -m eval.run_eval --mode deterministic --output-prefix eval/reports/day9-deterministic
    uv run --locked python -m eval.run_eval --mode local --output-prefix eval/reports/day9-local
    uv run --locked python -m eval.run_eval --mode full --output-prefix eval/reports/day9-v0.6

不带 `--output-prefix` 时报告写入 `eval/reports/latest.{json,md}`：该路径被 `.gitignore` 排除，是可随意覆盖的临时产物。

`day9-v0.6` 是**冻结的发布证据**——`scripts/check_release.py` 断言它的 `report_version`、`base_case_count` 与 `failure_analyses`。因此它不会被默认运行改写；只有显式传入 `--output-prefix eval/reports/day9-v0.6` 才覆盖它，且仅应在有意重新冻结时执行。

`full` 会产生真实模型费用并耗时数分钟。当前正式报告位于 `eval/reports/day9-v0.6.{json,md}`。一次完整运行不代表长期可靠性；首轮真实运行出现 1 条 grounding 失败，完整复跑为 13/13 首次结构化有效，该差异已保留为失败分析。

## Day 10 FastAPI

四个接口使用同一套核心 Schema、业务模块和 LangGraph 工作流，不在 API 层重新计算匹配或统计：

- `POST /resume/parse`：上传 UTF-8 Markdown/TXT 或文本层 PDF，返回 `CandidateProfile`；单文件上限 5 MB。
- `POST /jobs/analyze`：提交 `jd_text` 和可选 `job_index`，返回 `JobProfile`。
- `POST /jobs/batch`：提交 `CandidateProfile` 与 JD 列表；当前单次只接受一个 JD。
- `POST /agent/run`：提交 `AgentInput`，运行完整 Graph 并返回 `FinalReport`。

### 单 JD 范围

`AgentInput.raw_jobs` 与 `JobBatchRequest.raw_jobs` 都要求恰好一项，`MAX_JOBS` 固定为 1；`selected_job_index` 因此只能是 0。空数组或多于一个 JD 返回 422，且在调用模型前完成校验。前端只提供一个 JD 输入框。

保留 `job_errors`、`job_profiles` 和 `batch_statistics` 的字段与语义：单个 JD 解析失败时 PDF 仍返回 `status=failed` 的报告，失败岗位计入 `total_jobs` 和 `failed_jobs`。批量统计模块与字段未删除，只是当前请求规模恒为 1；若要恢复多岗位，需要同时放开 Schema 上限、`MAX_JOBS` 和前端（见 `docs/decisions.md` ADR-039）。

```powershell
uv run --locked uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

启动后访问 `http://127.0.0.1:8000/docs` 查看交互式接口文档。模型、Embedding 和知识库继续使用 `.env` 中的现有配置。上传内容在内存中解析，客户端文件名只作为安全的来源标识，不会被当作服务器路径。

## 网页 Demo 与 Docker

Vue 3 + TypeScript 页面是 API 的薄客户端：输入一份简历和一个目标岗位 JD，调用 `/agent/run` 展示 `FinalReport`。页面不复制解析、匹配或建议规则。前端通过 `VITE_API_BASE_URL` 配置 API 地址，默认是 `http://127.0.0.1:8000`。

先在一个 CMD 窗口启动 FastAPI，再在 `frontend/` 中启动 Vue 开发服务器：

```powershell
cd frontend
npm install
npm run dev
```

浏览器默认访问 `http://localhost:5173`。如后端地址不同，可在 `frontend/.env` 中设置 `VITE_API_BASE_URL`。Docker 镜像只运行 FastAPI API：

```powershell
docker build -t jobpilot:v1 .
docker run --env-file .env -p 8000:8000 jobpilot:v1
Invoke-WebRequest http://127.0.0.1:8000/health
```

`.env`、本地模型和向量索引不会进入镜像构建上下文；容器运行时仍需通过环境变量或挂载提供模型配置。Vue 前端单独运行，不包含在 API 镜像中。

## CMD 手动启动

如果使用 Windows CMD（提示符类似 `E:\00project\02agent\JobPilot>`），请打开两个 CMD 窗口。不需要配置系统环境变量。

窗口一：启动 FastAPI 后端：

```cmd
cd /d E:\00project\02agent\JobPilot
下面指令二选一
uv run --locked uvicorn app.api.main:app --host 127.0.0.1 --port 8000
.venv\Scripts\uvicorn.exe app.api.main:app --host 127.0.0.1 --port 8000
```

窗口二：启动 Vue 前端：

```cmd
cd /d E:\00project\02agent\JobPilot\frontend
npm install
npm run dev
```

然后访问 `http://localhost:5173`；后端健康检查为 `http://127.0.0.1:8000/health`。两个窗口都需要保持运行。

## v1.0 发布检查

Vue 生产构建检查：

```cmd
cd frontend
npm run build
```

运行以下命令执行不调用模型的本地发布检查：

```powershell
uv run --locked python -m scripts.check_release
uv run --locked ruff check .
uv run --locked ruff format --check .
$testTemp = Join-Path (Get-Location) ('.pytest_cache/verify-' + [guid]::NewGuid().ToString('N'))
uv run --locked pytest -q --basetemp $testTemp
```

架构图、三分钟 Demo 脚本、项目描述和面试问答位于 `docs/architecture/` 与 `docs/release/`。
Demo 运行步骤不会把未实际执行的 Docker 或模型调用写成通过；发布前请按
`docs/release/demo-script.md` 逐项执行并记录环境结果。
