# 开发进度

更新时间：2026-09-21
当前迭代：Day 7
版本：0.4（LangGraph 主干工作流）
状态：Day 7 实现完成；State、Node、Edge 与 v0.4 离线工作流演示验证通过。
落地目标：E:/00project/02agent/JobPilot

## 分部分记录

### 1. uv 与项目骨架

- 已使用 uv init 初始化，完整目录及后续模块占位已建立。
- 已通过 uv python install 安装 Python 3.11.15，uv venv 创建验证环境。
- 依赖通过 uv add 管理，真实 uv.lock 已生成，requirements.txt 已由 uv export 导出。
- Day 1 直接依赖：Pydantic、pydantic-settings、langchain-openai；开发依赖 pytest、HTTPX、Ruff。
- 未安装未来业务所需的全部框架，未实现 Day 2 及后续业务。

### 2. 核心数据契约与 State

- 已实现全部文档核心模型，外部/内部输入模型分离。
- 已实现范围、集合、计数、覆盖率、岗位索引、引用关联校验。
- 已实现 JobPilotState 全部字段和初始化；每个请求独立默认值及 request_id。
- 验证：契约用例 33 项通过；包含合法完整报告的 JSON 往返与所有模型 JSON Schema。

### 3. 基础设施与客户端

- 已实现环境配置、JSON 日志、安全异常、LLM 结构化客户端与冒烟入口。
- 日志仅写白名单元数据；SDK 重试默认 0，业务重试留到 Day 8。
- 验证：基础设施用例 12 项通过；其中真实安装的适配器使用 HTTPX MockTransport 验证。
- MockTransport 不是真实服务验证，不代表模型连接成功。

### 4. 整体验证

- 准备目录中 pytest：45 passed。
- Ruff 检查与格式化已执行；最终目标目录检查将在落地后追加。
- eval 已记录 4 条 Day 1 异常案例，无抽取准确率或 RAG 评测结果。

## 待完成 / 限制

- 真实服务、模型及凭据尚未配置；未执行真实模型成功调用。
- 缺少此项，不将 Day 1 全体验收标记为完成。
- Git 和目标目录 .venv 的实际落地状态见下方追加记录。
- Pydantic 检查结构一致性，不保证简历建议的事实真实性；后者由后续 Reflection 负责。

## 下一次唯一目标

在本地 .env 配置目标服务与模型，执行 uv run --locked python main.py --check-llm，
记录实际结果；通过 Day 1 验收后再开始 Day 2 ResumeParser。

## 目标目录落地验证

- 已在 E:/00project/02agent/JobPilot 执行 uv init、uv venv、uv sync --locked --offline。
- 目标目录 .venv 已创建并安装锁定依赖；原开发文档哈希一致，未改动。
- Git 已初始化为 main；未自动提交或推送。
- 离线冒烟通过；目标首次测试 44 passed / 1 setup error：系统 pytest 临时目录无权限。
- 改用项目内新建专用临时目录复验：45 passed；不是跳过失败用例。
- Ruff、格式检查、uv.lock 一致性检查通过。
- 缺模型/密钥的错误路径已在准备目录验证，正确返回退出码 1。
- 真实模型连接仍未验证；Day 1 待办为模型配置和真实冒烟验收。


## GLM-4.7 配置更新

- 按用户指定，在 .env 设置 LLM_MODEL=glm-4.7 和 LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/。
- 保留已有密钥及其余参数；本次仅核验配置文件，不发起模型请求。
- 模型服务已确定；真实连通性与结构化输出兼容性仍待验证。

## GLM-4.7 模型调用适配

- 结构化输出由 OpenAI 原生 json_schema 改为 OpenAI 兼容 function_calling。
- ChatOpenAI 对兼容端点显式关闭 streaming usage 扩展；当前调用仍为同步模式。
- .env、.env.example、README、配置默认值和客户端测试已同步。
- 模拟兼容接口验证请求包含 tools/tool_choice，并能解析为 Pydantic 模型。
- 完整离线测试 45 项通过；真实 GLM 请求仍需有效 API Key。

## GLM-4.7 真实调用修复与验收

- 初次真实结构化调用返回 HTTP 400 / code 1210；最小纯文本调用成功，定位为强制指定函数的参数兼容问题。
- 改为 bind_tools(..., tool_choice="auto")，并由 JobPilot 显式检查唯一工具名和 Pydantic 参数。
- 固定合成样例的真实 GLM-4.7 结构化调用成功，返回 jobpilot-ok；未发送简历或用户业务数据。
- 最终完整离线测试 45 项、Ruff 与格式检查通过。
- Day 1 模型连通性与结构化输出验收现已完成。


## Day 2 简历读取与结构化解析

### 已完成

- 支持读取 UTF-8 Markdown/TXT 与文本层 PDF，单文件上限 5 MB；空文件、无文本 PDF、错误编码、超限及不支持格式均返回明确错误。
- ResumeParser 复用 CandidateProfile；LLM 仅执行结构化抽取，Python 负责原文逐字段校验、证据检查及 source_id/locator 重建。
- 提供 3 份合成简历和对应 eval 期望，覆盖 Markdown、TXT、PDF。
- 新增 7 条 Day 2 失败案例，包含无文本文件、模型编造字段、证据缺失和提示注入文本。
- 新增运行入口：`python main.py --parse-resume <path>`。

### 验证结果

- Day 2 专项测试：20 passed。
- Day 1 回归测试：45 passed。
- Ruff 检查与格式检查通过。
- 真实 GLM-4.7：3/3 合成简历调用成功；关键 skills、project name、education school 与 eval 期望一致。
- 以上真实调用只使用仓库内合成数据，不包含用户简历；mock 结果未计作真实模型验证。

### 限制

- 仅支持文本层 PDF，不支持扫描件 OCR。
- 模型抽取具有非确定性；Python grounding 会阻断没有原文依据的输出，但不替代后续 Reflection。
- 尚未实现岗位解析、匹配、LangGraph 工作流、RAG、API 或 UI。

## 下一次唯一目标

Day 3 实现 JobParser：复用 JobProfile Schema，解析合成岗位文本，使用 Python 完成确定性校验，并把新增失败案例加入 eval。


## Day 3 JD Analyzer 与 v0.1

### 已完成

- JDAnalyzer 复用 JobProfile；输入 JD 文本、job_index、source_id，输出经过 grounding 的 JobProfile。
- LLM 负责标题、公司、职责和 required/preferred 语义抽取；Python 固定 job_index，逐字段核对原文，验证明示分类标记，重建证据定位。
- 可选字段中的模型占位字符串仅在原文不存在该词时确定性归一化为 None；标题、技能和列表仍严格 grounding。
- 提供 10 条脱敏合成岗位样例、期望结果与独立 UTF-8 文件；两条模糊技能明确记录并要求不分类。
- 新增 7 条 Day 3 失败/边界案例，包括空 JD、非法索引、编造事实、缺证据、分类交换、模糊技能和字符串 null。
- 新增 `--analyze-job` 与 `--demo-v01`；后者只串联 CandidateProfile 和 JobProfile，不执行匹配。

### 验证结果

- Day 3 专项离线测试：27 passed。
- 完整离线回归：92 passed。
- Ruff 检查、格式检查和两份 eval JSON 语法检查通过。
- 真实 GLM-4.7：10/10 合成 JD 的 title、company、required_skills、preferred_skills 与 eval 期望一致。
- 两条模糊样例中的 GitHub、Slack、Rust 均未进入 required/preferred。
- v0.1 真实串联：一份合成简历与一条已通过 JD 均生成合法结构化画像。
- 首轮真实验证发现缺失字段字符串 `null` 并被 grounding 拒绝；加入确定性可选字段归一化及回归案例后重新全量通过。
- mock/假模型只用于离线边界测试，未计作真实模型验证。

### 限制

- 10 条 JD 是脱敏合成、真实岗位风格样例；尚未用外部公开的实时招聘页面验证。
- required/preferred 只接受明确标记；未明确表达的技能保持未分类。
- v0.1 仅输出双画像，尚无匹配分数、Gap、批量统计、RAG 或 Graph。

## 下一次唯一目标

Day 4 实现独立 Matching Engine：由 Python 完成技能规范化、集合匹配、覆盖率和证据；项目相关性按开发文档选择可验证的最小实现。

### 正式目录 CLI 复验

- 正式目录 `--analyze-job` 首次真实调用返回安全 StructuredOutputError（退出码 1）；未记为通过，已加入 eval。
- 随后的正式目录 `--demo-v01` 真实调用成功：Resume 与 JD 两次模型调用均完成，输出合法 CandidateProfile 和 JobProfile。
- 当前不增加自动重试；受控 Retry 按开发文档保留到 Day 8。


## Day 4 Matching Engine

### 已完成

- MatchingEngine 接收 CandidateProfile + JobProfile，输出既有 MatchResult；未修改公共 Schema。
- Python 完成 Unicode/大小写/空格规范化、显式别名映射、规范值去重、matched/missing 集合和 coverage。
- 技能确定匹配只读取 CandidateProfile.skills；项目技术不暗中并入技能集合。
- `local-hash-v1` 使用标准库生成固定向量；Python 对所有项目与职责逐对计算 cosine，取最高相关配对并生成证据。
- 默认分数按 required=0.5、preferred=0.2、project=0.3；不可用维度移除后重归一化，没有有效维度时 score=None。
- 填充 7 条 matching eval 案例，新增 8 条失败/边界案例；新增 `--match-demo` 离线入口。
- 无新增依赖，无 LLM、网络或外部 Embedding 调用。

### 验证结果

- Day 4 专项测试：20 passed。
- 完整离线回归：112 passed。
- Ruff 检查与格式检查通过；matching/error eval JSON 语法检查通过。
- 离线 CLI `--match-demo` 成功，重复固定输入结果一致。
- 验证覆盖：空集合、规范重复、显式别名、无项目、无职责、相关但不等价、最高项目配对、权重重分配和异常向量。
- 首次 CLI 发现 Windows GBK 无法输出 Unicode 箭头；改为 ASCII `<->` 并加入 eval 后复验通过。
- 本迭代不调用模型，因此没有“真实模型验证”结果，也没有把 mock 结果写成真实模型通过。

### 限制

- `local-hash-v1` 是词法哈希 Embedding 基线，能稳定衡量共享词特征，但不具备通用语义模型的同义理解能力。
- 别名只认代码中的显式映射；语义相关不视为技能等价。
- 教育和经验要求未纳入分数，符合开发文档边界。
- 尚未实现 Day 5 Gap 与 BatchAnalyzer。

## 下一次唯一目标

Day 5 实现 GapAnalyzer + BatchAnalyzer：基于现有 MatchResult 生成有 JD 依据的 Gap，并对多个有效/失败岗位计算去重频率与统计口径。

## 本地 BGE 模型约束更新

### 已完成

- 用户指定后，Day 4 项目相似度从 `local-hash-v1` 切换为本地 `bge-large-zh-v1.5`。
- 默认路径：`E:/00project/02agent/models/bge-large-zh-v1.5`；支持 `EMBEDDING_MODEL_PATH` 和 `EMBEDDING_DEVICE` 配置。
- 客户端延迟加载、同进程缓存、向量归一化并设置 `local_files_only=True`；不会自动下载或切换模型。
- 新增 sentence-transformers 运行依赖，uv.lock 和 requirements.txt 已由 uv 更新。
- 本地 `bge-reranker-v2-m3` 已确认存在，默认规划路径为 `E:/00project/02agent/models/bge-reranker-v2-m3`。重排尚未实现，保留到 Day 6 纯向量检索基线评测之后。
- 开发文档的技术栈、Day 4、Day 6、RAG 流程和 Future Work 已同步指定模型。

### 实际验证

- 完整离线回归：115 passed；Ruff 检查、格式检查和 error eval JSON 校验通过。
- `bge-large-zh-v1.5` 从指定本地目录真实加载成功，没有下载模型。
- 正式合成项目/JD 推理得到 project_similarity=0.629436，证据 model_id 为 bge-large-zh-v1.5，最终 score=52.22。
- 该结果是本地 Embedding 真实推理；重排模型没有运行，不宣称 reranker 验证通过。

### 下一步边界

- Day 5 继续 GapAnalyzer + BatchAnalyzer，不提前实现重排。
- Day 6 使用同一 bge-large-zh-v1.5 建立 RAG 向量基线；只有固定 eval 证明排序不足时才接入 bge-reranker-v2-m3。

## Day 5 Gap + Batch

### 已完成

- GapAnalyzer 复用 JobProfile、MatchResult 和 SkillGap，按 job_index 绑定岗位。
- Gap 只来自 MatchingEngine 的 missing required/preferred 集合；required 优先级为 1，preferred 为 2。
- 每个 Gap 必须引用包含对应技能的 JD EvidenceRef；缺少依据时安全失败，不生成无来源 Gap。
- BatchAnalyzer 对每条有效 JD 内的规范技能去重，required/preferred 分别计数，any_count 按岗位并集计数。
- ratio 以 valid_jobs 为分母；total_jobs、valid_jobs、failed_jobs 明确展示，失败 JD 不作为空技能岗位。
- 高频阈值初始为 0.5；只将候选人 skills 中没有规范匹配的高频技能列入 high_frequency_missing_skills。
- 新增 --demo-v02：5 个合成岗位输入中 4 个有效、1 个模拟失败，输出匹配排名、目标岗位 Gap 和统计。
- 新增 batch_cases.json 和 Day 5 失败案例；未修改公共 Schema，未新增依赖。

### 实际验证

- Day 5 专项测试：14 passed。
- 正式目录完整离线回归：129 passed。
- Ruff 检查和格式检查通过；error_cases.json 与 batch_cases.json 可解析。
- --demo-v02 成功输出 5 个输入的 4 个匹配结果、1 个失败、目标岗位 Gap 和批量统计；SQL 以 2/4=0.5 成为高频缺失技能。
- Day 5 没有 LLM 调用；专项测试和合成 CLI 不记作真实模型验证。

### 限制

- 批量入口当前接收已成功解析的 JobProfile，并由 total_jobs 表达失败数量；完整批量解析编排留到 Day 7。
- 排名使用现有 MatchResult.score；相同分数维持输入顺序，不引入新的排名模型。
- Gap 当前区分 not_mentioned；insufficient 留给以后有明确证据的分析，不凭语义猜测。
- 尚未实现 Day 6 RAG、LearningPlanner 或 ResumeOptimizer。

## 下一次唯一目标

Day 6 使用本地 bge-large-zh-v1.5 建立可评测的知识库向量检索基线，实现可追溯 LearningPlanner 与最小 ResumeOptimizer；只有 eval 证明排序不足时才接入 bge-reranker-v2-m3。

## Day 6 RAG + LearningPlanner + ResumeOptimizer

### 已完成

- Loader 只读取受控知识目录中的 UTF-8 Markdown/TXT，拒绝符号链接、超限文件和非法编码。
- Splitter 按可定位 token span 进行默认 600 token、100 token overlap 分块，保留 doc_id、chunk_id 和 source。
- FaissVectorStore 使用本地 bge-large-zh-v1.5 归一化向量和 IndexFlatIP；Retriever 对每个 SkillGap 返回 Top-K RetrievedDocument。
- 人工维护 5 份小型学习资料，覆盖 FastAPI、Docker、LangGraph、PostgreSQL 和 RAG。
- LearningPlanner 只为内容中明确包含 Gap 技能的检索文档生成任务，source_chunk_ids 来自实际检索；无支持资料时只返回 warning。
- ResumeOptimizer 只使用 CandidateProfile.evidence 和候选人已具备且岗位要求的技能；没有候选人证据时不生成建议。
- 新增 5 条人工标注 rag_cases、5 条 Day 6 失败案例、--eval-rag 和 --demo-v03。
- 新增 faiss-cpu，由 uv.lock 锁定并重新导出 requirements.txt；公共 Schema 未修改。

### 实际验证

- Day 6 专项离线测试：14 passed。
- 完整离线回归：143 passed。
- Ruff 检查与格式检查通过。
- 本地 bge-large-zh-v1.5 + FAISS 真实检索：固定 5 条案例 Hit@1=5/5、Hit@4=5/5；每条期望文档均排第 1。
- --demo-v03 真实加载本地 BGE，建立 5 个 chunk 的 FAISS 索引，Docker 与 LangGraph 均生成有 chunk 引用的学习任务；简历建议引用候选人原文。
- 上述检索和演示未调用 GLM-4.7；不记作真实 LLM 验证。

### 限制

- 知识库只有 5 份人工资料，检索指标只代表该固定小样本，不能推断通用检索质量。
- LearningPlanner 和 ResumeOptimizer 当前是确定性最小实现，未使用 LLM 做表达润色。
- 纯向量基线在固定集上 Hit@1 和 Hit@4 均为 1.0，尚无证据表明需要重排，因此 bge-reranker-v2-m3 未接入、未运行。
- FAISS 索引当前在进程内构建；持久化索引不是 v0.3 验收所需。
- 尚未实现 Day 7 LangGraph 编排。

## 下一次唯一目标

Day 7 实现完整 LangGraph State、Node、Edge，将前六天模块串成 Workflow；保证简历只解析一次、selected_job_index 一致、无 Gap 时跳过学习分支。

## Day 7 LangGraph Workflow

### 已完成

- 使用 LangGraph StateGraph 实现 validate_input、parse_resume、analyze_jobs、calculate_matches、calculate_statistics、analyze_gap、retrieve_knowledge、learning_plan、optimize_resume 和 final_report 节点。
- 节点只编排既有模块并返回局部 State 更新；业务计算没有搬入 Graph。
- 单份简历每次工作流只解析一次；JD 串行处理并保留原始 job_index，单条已知失败写入 job_errors。
- selected_job_index 只指向原始 JD；选定岗位失败时不借用其他岗位 Gap，返回明确错误。
- 只有存在 Gap 且 need_advice=true 才进入学习分支；无 Gap 或关闭建议时 Retriever 不创建、不索引、不加载 BGE。
- 生成完整 FinalReport；根据核心结果和岗位失败明确区分 success、partial、failed。
- 新增真实入口 --run-workflow 和离线合成演示 --demo-v04。
- 新增 5 条 workflow eval 数据、3 条失败/路由案例和 7 个专项测试。
- 新增 langgraph 直接依赖并更新 uv.lock、requirements.txt；JobPilotState 和公共 Pydantic Schema 未修改。

### 实际验证

- Day 7 专项离线测试：7 passed。
- 完整离线回归：150 passed。
- Ruff 检查、格式检查、workflow_cases/error_cases JSON 解析与 git diff check 通过。
- --demo-v04 通过真实编译的 LangGraph 执行全部节点，生成 success FinalReport；selected_job_index=1，两个 Gap 和学习引用均属于岗位 1。
- 离线测试和 --demo-v04 使用注入式确定性适配器，不是 GLM 或真实 BGE 验证。
- 正式目录 uv sync --locked --all-groups 成功安装 langgraph==1.2.11 及锁定依赖。
- 真实 --run-workflow --no-advice 成功：GLM-4.7 完成简历/JD 两次结构化调用，本地 BGE 项目相似度=0.624298，score=68.73，Graph 正确跳过 RAG 并返回 success。
- 真实启用建议的 --run-workflow 成功：Docker 生成引用 docker:0 的学习任务；Redis 无知识覆盖，返回 warning 且未生成无来源任务；FinalReport 状态为 success。

### 限制

- Day 7 不实现 Tool Calling、Reflection、Retry 或修复循环；节点异常的受控修复属于 Day 8。
- 已知单条 JD 失败可以形成 partial/failed 报告；简历解析或基础设施异常目前仍向调用方抛出。
- 工作流当前串行执行，符合 v1.0 小批量边界。
- 尚未实现 API 和 UI。

## 下一次唯一目标

Day 8 实现受控 retrieve_knowledge_tool 调用、明确条件边、Reflection、最多 2 次业务修复和终止状态；故障注入必须可定位并返回 partial/failed。
