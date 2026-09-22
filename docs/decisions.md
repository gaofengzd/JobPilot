# 决策记录

## 2026-09-18 / Day 1 骨架

- 用户本次指定完整 Day 1，并要求 uv 初始化、虚拟环境及持续记录。
- 使用 uv init 创建项目，依赖由 uv add / uv sync 维护；锁文件由工具生成。
- 保留完整目录，Day 2–12 模块仅占位；不安装对应未来框架。
- docs/开发文档.md 已在目标目录存在，作为唯一事实来源，不覆盖。

## Day 1 数据契约

- 保持文档字段，增加 schemas/input.py 分离外部文本请求和内部文件路径输入。
- model_validator 检查集合、计数、覆盖率及引用关联；业务匹配计算留到 Day 4。
- State 初始化校验输入并为每次调用创建独立列表/字典。
- 原文未提及的字段用 None/空列表；证据引用需非空，禁止空引用伪装支持。
- 仅文档已经规定的结构规则进入 Day 1；事实真实性由后续 Reflection 校验。

## Day 1 基础设施

- 先提供 langchain-openai 的标准协议适配器，不写死模型；自定义服务需验证兼容性。
- 用户尚未选择模型；不主动查找其他项目凭据，也不发送真实简历。
- Structured Output 方法显式配置；不支持时明确失败，不暗中降级。
- SDK 传输重试默认 0；业务修复与总预算由 Day 8 工作流实现。
- 只记录白名单元数据，错误信息不包含提供商原始消息或候选人文本。
- 未扩展业务范围，无数据迁移。适配器变化只影响 services 层。

## Day 1 验证完成

- Python 3.11.15，Pydantic 2.13.5、pydantic-settings 2.15.0、langchain-openai 1.6.2，具体版本以 uv.lock 为准。
- 完整离线测试 45 项通过；不为获得通过而放宽契约。
- 依赖适配器通过 HTTPX MockTransport 实测序列化/解析，不伪装成真实模型验证。
- 模型配置尚未提供，真实调用保留为 Day 1 验收待办。
- 此部分无架构变更；后续继续按开发文档推进。

- 原始开发文档保持逐字不变；Ruff 排除 Markdown，避免格式化器修改其中的示例代码。

## Day 1 目标目录落地与环境修复

- .venv 在目标目录由 uv 重新创建，未复制准备目录虚拟环境。
- 系统 pytest 临时目录存在 ACL 限制，复验使用项目 .pytest_cache 下全新唯一目录；
  不改系统权限，不删除既有临时目录，不修改业务断言。
- 此故障为测试环境问题，无 Schema/架构变更。README 记录临时目录覆盖方法。
- 每部分完成持续更新本文件与 progress.md；真实模型仍待配置。


## 模型服务选择：智普 GLM-4.7

- 用户指定标准 PaaS v4 地址，通过现有 OpenAI 兼容客户端调用。
- 本次只修改本地 .env 的模型名和接口地址，不更改 Schema、客户端或结构化方法。
- 保留密钥，不把密钥或 .env 内容记录到文档。无架构变更。

## GLM-4.7 结构化输出策略

- 智谱标准 PaaS v4 使用 OpenAI 兼容协议，GLM-4.7 的结构化契约采用函数调用。
- 不向兼容端点发送 OpenAI 原生 json_schema response_format，避免协议不支持。
- 不做运行时静默降级；配置方法固定且失败显式上报，便于评测和定位。
- 关闭 stream_usage 扩展以减少兼容端点差异；token 用量仍读取普通同步响应。
- 影响范围仅为配置、LLM 客户端、示例和客户端测试；业务 Schema 无变更。

## GLM-4.7 工具选择兼容性修正

- 实测智谱接口拒绝 OpenAI 的强制指定函数对象（HTTP 400 / code 1210），但接受 tool_choice="auto"。
- 客户端不再依赖 LangChain 的强制函数结构化封装；显式 bind_tools 后校验恰好一个同名 schema 工具调用。
- json_schema 分支继续保留给支持该协议的其他提供商，GLM 配置固定走 function_calling。
- 该修正不改变业务 Schema；异常仍脱敏并区分模型调用失败与结构化输出失败。

## ADR-006：Day 2 简历文件边界

- 日期：2026-09-19
- 状态：已采用
- 决策：仅接受 UTF-8 `.md`/`.txt` 与含文本层的 `.pdf`，单文件上限 5 MB；PDF 使用 pypdf。
- 原因：满足 Day 2 的最小可运行范围，并能为证据生成稳定的行号或页码定位。
- 影响：扫描 PDF、OCR、DOCX 和网页简历返回明确错误，后续如扩展须单独决策。

## ADR-007：抽取结果必须经 Python grounding

- 日期：2026-09-19
- 状态：已采用
- 决策：LLM 只输出 CandidateProfile；Python 检查全部非空字符串是否能在原文中找到，要求至少一条有效证据，并重建 evidence 的 source_id 与 locator。
- 原因：防止模型编造事实或伪造引用，把确定性校验留在业务代码。
- 影响：当前采用抽取式字段，模型改写或归纳会被拒绝；CandidateProfile 公共 Schema 不变，无迁移成本。

## ADR-008：简历内容视为不可信数据

- 日期：2026-09-19
- 状态：已采用
- 决策：prompt 明确简历中的命令不是系统指令，且任何新增事实必须通过原文 grounding。
- 原因：简历可能含提示注入文本，模型提示与 Python 校验需共同限制影响。
- 影响：失败案例已加入 eval；未引入额外 Agent 或安全框架。

## ADR-009：Day 3 JD 抽取边界

- 日期：2026-09-20
- 状态：已采用
- 决策：JDAnalyzer 复用 JobProfile，不新增公共 Schema；job_index 由 Python 输入并覆盖模型值，所有文本字段必须能在 JD 原文中找到。
- 原因：岗位索引属于流程确定性数据，事实字段才属于模型抽取职责。
- 影响：无 Schema 迁移；调用方需提供非负整数 job_index。

## ADR-010：required/preferred 必须有明示标记

- 日期：2026-09-20
- 状态：已采用
- 决策：模型负责语义抽取，Python 要求 required_skills 出现在 required/must-have/mandatory/necessary 标记行，preferred_skills 出现在 preferred/nice-to-have/bonus/a plus 标记行。
- 原因：Day 3 需要稳定区分两类技能，且不能凭上下文猜测模糊要求。
- 影响：未明确标记的技能保持未分类；后续如扩展自然语言强弱规则须新增 eval 和决策。

## ADR-011：模型缺失值占位符归一化

- 日期：2026-09-20
- 状态：已采用
- 决策：仅对 company、education_requirement、experience_requirement 三个可选字段处理 null/None/N/A/unknown/not specified；只有占位词不在原文时才转为 None。
- 原因：真实 GLM-4.7 两次将 JSON null 输出成字符串 null；仅提示约束无法稳定消除。
- 影响：标题、技能、职责、关键词和证据不做此归一化，仍严格拒绝无原文支持内容；公共 Schema 不变。

## ADR-012：Day 3 样例来源

- 日期：2026-09-20
- 状态：已采用
- 决策：仓库保存 10 条脱敏合成、真实岗位风格 JD，覆盖 10 类岗位和多种 required/preferred 明示措辞，不复制外部招聘页面全文。
- 原因：形成可提交、可复现且无实时页面漂移的 v0.1 验收集。
- 影响：真实 GLM 调用已验证这些合成样例；外部公开实时 JD 的泛化能力仍未验证。

## Day 3 正式 CLI 非确定性观察

- 日期：2026-09-20
- 记录：同一 backend-python 样例此前批量真实验证通过，正式 `--analyze-job` 单次调用出现 StructuredOutputError，随后 `--demo-v01` 对同一样例成功。
- 决策：保持安全失败与零 SDK 重试，不在 Day 3 提前实现 Day 8 的 Retry/Reflection；失败案例加入 eval。
- 影响：CLI 调用方当前可能收到可处理的退出码 1；不宣称所有单次真实调用稳定成功。

## ADR-013：Day 4 技能匹配口径

- 日期：2026-09-20
- 状态：已采用
- 决策：确定匹配只使用 CandidateProfile.skills；先做 NFKC、去空格、大小写规范和规范值去重，再应用代码内显式别名字典。
- 原因：项目技术可以支持项目相关性，但不能在没有明确画像字段时暗中提升技能覆盖率；语义相关也不等价于掌握目标技能。
- 影响：Python3/Python、Postgres/PostgreSQL、K8s/Kubernetes 等审阅过的别名可匹配；LangChain/LangGraph 保持不同。扩展别名必须新增 eval；required/preferred 在别名规范化后重叠时明确失败，避免重复计分。

## ADR-014：项目相关性的本地固定基线

- 日期：2026-09-20
- 状态：已被 ADR-016 取代
- 决策：Day 4 默认使用 `local-hash-v1`，对规范词和相邻词对做稳定哈希向量，再由 Python 计算项目与职责的全部 cosine 并取最大值。EmbeddingClient Protocol 保留替换边界。
- 原因：当前没有独立 Embedding 服务配置；本地基线无需新依赖、网络或凭据，能满足确定性和失败注入验证。
- 影响：该分数主要反映词法相关性，不宣称具备通用语义能力。未来替换固定 Embedding 模型时保持 MatchingEngine 输入输出不变，并更新 model_id、eval 基线和决策。

## ADR-015：Match Score 维度与证据

- 日期：2026-09-20
- 状态：已采用
- 决策：使用文档默认权重 required=0.5、preferred=0.2、project=0.3；仅对可用维度重归一化。coverage 空集合为 0.0 但不参与分数，无有效维度则 score=None。
- 原因：严格落实开发文档公式，并避免把“不适用”当成零能力。
- 影响：evidence 写明技能规范匹配、最高项目/职责配对、Embedding model_id 及可用权重；score_version 保持 1.0。教育/经验不进入分数。

## Day 4 Windows 输出兼容性

- 日期：2026-09-20
- 决策：机器生成证据使用 ASCII `<->` 连接项目与职责。
- 原因：真实离线 CLI 在默认 GBK 控制台输出 Unicode 箭头时触发 UnicodeEncodeError。
- 影响：只改变可读证据字符，不改变 Schema 或计算结果；失败案例已加入 eval。


## ADR-016：固定本地 BGE Embedding 与 Reranker

- 日期：2026-09-20
- 状态：已采用
- 决策：所有现有及后续 Embedding 统一使用本地 `bge-large-zh-v1.5`，默认路径 `E:/00project/02agent/models/bge-large-zh-v1.5`；需要重排时统一使用本地 `bge-reranker-v2-m3`，默认路径 `E:/00project/02agent/models/bge-reranker-v2-m3`。
- 实现：Embedding 通过 sentence-transformers 延迟加载，`local_files_only=True`、归一化输出、默认 CPU、同实例缓存。模型路径可配置，模型身份不得静默替换。
- 原因：用户已提供固定本地模型；真实语义 Embedding 取代临时词法哈希基线，同时保持数据不离开本机。
- 影响：新增 sentence-transformers 及其锁定依赖；项目相似度数值基线变化，MatchResult/MatchingEngine 公共契约不变。ADR-014 的 `local-hash-v1` 被取代。
- 重排边界：当前没有 reranker 业务代码。Day 6 先运行纯向量检索 eval，仅在排序不足时接入 bge-reranker-v2-m3，不提前实现 Future Work。
- 验证：bge-large-zh-v1.5 已从指定目录真实加载并完成合成项目/JD 推理；bge-reranker-v2-m3 仅确认文件存在，尚未执行推理。

## ADR-017：Day 5 Gap 的来源与优先级

- 日期：2026-09-20
- 状态：已采用
- 决策：Gap 只从已验证 MatchResult 的 missing 分区生成；required priority=1、preferred priority=2，每项必须绑定包含该技能的 JobProfile.evidence。
- 原因：避免 LLM 或新规则再次解释匹配结果，并保证 Gap 能在 JD 中定位。
- 影响：JobProfile 与 MatchResult 的 job_index 不一致、缺失技能不属于岗位、或 JD 证据缺失时返回 GapAnalysisError；公共 Schema 无迁移。

## ADR-018：Day 5 批量统计口径

- 日期：2026-09-20
- 状态：已采用
- 决策：技能按 MatchingEngine 的显式规范化规则聚合；同一岗位内每个规范技能只计一次，required/preferred 分别计数，any_count 使用岗位并集。ratio 分母为 valid_jobs，高频初始阈值为 0.5。
- 原因：与开发文档 C.7 保持一致，使部分解析失败不会降低技能频率，并保持统计可复现。
- 影响：BatchAnalyzer 接收 CandidateProfile、成功解析的 JobProfile 列表和 total_jobs；失败数由 total_jobs-valid_jobs 得出。完整 job_errors 编排留到 Day 7，公共 Schema 无迁移。

## ADR-019：Day 6 学习知识库与分块边界

- 日期：2026-09-21
- 状态：已采用
- 决策：知识库只接受人工维护的 UTF-8 Markdown/TXT；默认分块 600 token、overlap 100，保留稳定 doc_id/chunk_id/source。拒绝符号链接、单文件超过 1 MB 和非法编码。
- 原因：满足可追溯学习资料与最小安全输入边界，不引入爬虫或复杂文档管线。
- 影响：新增 5 份小型学习资料和 RetrievalError；公共 Schema 无迁移。

## ADR-020：Day 6 纯向量 FAISS 基线与重排决策

- 日期：2026-09-21
- 状态：已采用
- 决策：使用本地 bge-large-zh-v1.5 归一化向量和 FAISS IndexFlatIP，Top-K 默认 4。固定 5 条人工标注案例真实结果为 Hit@1=5/5、Hit@4=5/5，因此不接入 bge-reranker-v2-m3。
- 原因：开发文档要求先建立纯向量基线，只有固定 eval 证明排序不足时才增加重排。
- 影响：新增 faiss-cpu 依赖；reranker 仍未运行，不能宣称已验证。小样本满分只说明当前固定集无需重排。

## ADR-021：Day 6 建议生成采用确定性最小实现

- 日期：2026-09-21
- 状态：已采用
- 决策：LearningPlanner 只组合明确包含 Gap 技能的 RetrievedDocument 并引用实际 chunk；ResumeOptimizer 只使用 CandidateProfile.evidence 和候选人已具备的目标技能。两者当前不调用 LLM。
- 原因：先满足来源可追踪、空检索降级和不新增经历的 Day 6 验收，再在 Day 8 Reflection 前保持事实边界可验证。
- 影响：建议表达较模板化；不改变 LearningPlan 或 ResumeSuggestion Schema。未来如引入 LLM 润色，必须保留相同 grounding 校验。

## ADR-022：Day 7 Graph 只负责编排既有模块

- 日期：2026-09-21
- 状态：已采用
- 决策：LangGraph 节点返回局部 State 更新，按固定主干调用 ResumeParser、JDAnalyzer、MatchingEngine、BatchAnalyzer、GapAnalyzer、RAG、LearningPlanner 和 ResumeOptimizer；不在节点内复制业务规则。
- 原因：遵守六层依赖方向，并使各模块继续能够独立测试。
- 影响：新增 langgraph 依赖和 WorkflowDependencies 注入边界；JobPilotState 与公共 Pydantic Schema 无迁移。

## ADR-023：Day 7 岗位失败、选定岗位和学习路由

- 日期：2026-09-21
- 状态：已采用
- 决策：JD 串行解析并保留原始索引；单条已知失败写入 job_errors。selected_job_index 失败时不选择替代岗位。学习分支只在存在所选岗位 Gap 且 need_advice=true 时执行，Retriever 延迟创建并在单次依赖容器中缓存。
- 原因：避免岗位错位、详情混用和无必要的 BGE/FAISS 加载。
- 影响：部分岗位失败返回 partial，全部核心岗位失败返回 failed；Day 8 再加入异常修复、Reflection 和工具调用，不在 Day 7 提前实现。

## ADR-024：真实 Tool Calling 只用于学习检索分支

- 日期：2026-09-21
- 状态：已采用
- 决策：固定 Graph 主干直接调用薄 Tool/业务模块；只有学习分支由 GLM 请求 `retrieve_knowledge_tool`。参数必须等于 selected job 的现有 Gap，最多一次参数修复；执行结果用原 tool_call_id 返回模型后结束，不开放任意工具循环。
- 原因：满足文档的真实 Tool Calling 演示，同时避免模型重新决定评分、统计或整个工作流。
- 影响：真实启用建议会为每个 Gap 增加工具请求及结果确认调用；离线工作流直接执行同一 Tool。公共 Schema 无迁移。

## ADR-025：Reflection 使用确定性规则和两次局部修复

- 日期：2026-09-21
- 状态：已采用
- 决策：Reflection 由 Python 检查 Match/JD 分区、Gap 依据、候选人证据和学习 chunk；按第一个问题模块局部重建，整个请求最多两次。超过上限后删除未通过的建议，保留可验证结果并标 partial。
- 原因：事实一致性属于规则验证，不应交给模型主观自评；有限环防止无限重试和成本失控。
- 影响：启用既有 State 运行字段，不增加公共 Schema；持续基础设施错误仍明确失败或 partial，不通过改规则放行。

## ADR-026：Day 9 评测基线与模式分离

- 日期：2026-09-22
- 状态：已采用
- 决策：基础评测固定为 3 简历 + 10 JD + 10 Matching + 5 RAG + 5 Error，共 33 条人工期望案例。运行器区分 deterministic、local、full；报告显式记录是否调用 LLM、Embedding 和 reranker。
- 原因：相同数字必须能够追溯到同一种运行条件，避免把 mock、确定性规则、本地模型和线上模型结果混为一谈。
- 影响：新增独立 Evaluation 内部结构、JSON/Markdown 报告和测试；业务 Schema、评分公式和 Graph 无迁移。

## ADR-027：指标、基线与失败报告口径

- 日期：2026-09-22
- 状态：已采用
- 决策：required/preferred 分别计算 P/R/F1；Matching 计算匹配集合 P/R 和 coverage MAE；RAG 报 Hit@1/Hit@4；Citation Support 只聚合人工标签；Structured Output、Tool、Workflow 分别记录。v0.5 基线来源和样本限制随报告保存。
- 原因：失败调用必须计入分母，引用支持不能由词面重叠自动冒充人工事实判断，单次工作流也不能外推为可靠性。
- 影响：真实运行首轮 12/13、复跑 13/13 均如实记录；不因首次失败放宽 grounding。无可信价格表时成本为 unknown。

## ADR-028：Day 10 API 为薄传输层

- 日期：2026-09-22
- 状态：已采用
- 决策：四个 FastAPI 端点直接复用 CandidateProfile、JobProfile、AgentInput、FinalReport、既有业务模块和已编译 LangGraph；API 只负责输入输出、依赖装配和错误映射。批量接口增加三个仅用于 HTTP 传输的模型，不改变核心业务 Schema。
- 原因：保持开发文档的六层依赖方向，避免 API 重新实现匹配、统计或工作流规则。
- 影响：新增 `app/api/contracts.py`，无核心 Schema 迁移；业务规则变更应继续发生在业务模块并由 API 自动复用。

## ADR-029：上传采用内存解析与服务端路径隔离

- 日期：2026-09-22
- 状态：已采用
- 决策：`/resume/parse` 最多读取 5 MB + 1 byte，在内存中解析 UTF-8 Markdown/TXT 和文本层 PDF；客户端文件名只保留 basename 作为 source_id，不拼接或读取客户端提供的路径。
- 原因：API 不应把外部文件名解释为服务器文件路径，同时保持 Day 2 文件类型和大小边界一致。
- 影响：不持久化上传文件；扫描 PDF、错误编码、空文件、不支持扩展名及超限输入返回受控 400/413。未来若需要对象存储须另行决策。

## ADR-030：共享服务对象与请求 State 隔离

- 日期：2026-09-22
- 状态：已采用
- 决策：应用首次业务请求时延迟创建并缓存 LLM、Embedding、Retriever、业务模块和已编译 Graph；每次完整分析仍通过 `create_initial_state` 创建独立可变 State 和 request_id。测试可通过应用工厂注入确定性依赖。
- 原因：本地 BGE、FAISS 和 Graph 构建成本适合进程内复用，请求产物则必须隔离以防串数据。
- 影响：当前同步服务适合 v1.0 小批量运行；多进程部署时每个 worker 各自加载模型和索引。无任务队列或跨进程共享状态。

## ADR-031：Day 10 HTTP 错误口径与多行技能观察

- 日期：2026-09-22
- 状态：已采用
- 决策：配置错误映射 503，模型、结构化输出及 grounding 错误映射 502，上传问题映射 400/413，请求校验和动态批量上限映射 422。错误响应只返回异常类型和安全消息，不暴露底层 provider 内容。
- 原因：客户端需要区分输入、配置、上游模型和内部业务失败，同时保持现有安全异常边界。
- 影响：真实 Uvicorn + GLM 验证确认标准同一行明示标记 JD 返回 200；技能标题与项目符号分行时会触发 ADR-010 的同一行 grounding 并返回 502。该版式已加入 eval，Day 10 不修改既有抽取契约；后续只有在评测证明需要时才调整规则并补迁移说明。

## ADR-032：Day 11 薄 UI、健康检查与单镜像启动

- 日期：2026-09-22
- 状态：已采用
- 决策：Streamlit 只收集简历、5 个 JD 和目标岗位，调用既有 `/agent/run` 并展示 `FinalReport`；`/health` 为不初始化模型的传输层探针。Dockerfile 默认启动 API，UI 通过同一镜像覆盖命令启动，密钥和本地模型由运行时注入。
- 原因：完成 Day 11 Demo 与部署验收，同时保持业务规则只存在于 Graph/Business Module。
- 影响：新增 `requests`、`streamlit` 运行依赖和 UI/容器入口；无核心 Schema 迁移。健康检查只证明 API 进程可响应，不代表模型调用成功。

## ADR-033：Day 12 版本收口与发布检查

- 日期：2026-09-22
- 状态：已采用
- 决策：将项目元数据、FastAPI OpenAPI 和健康检查版本统一为 `1.0.0`；保留 Day 9 的 `0.6` 评测报告作为历史验证产物；使用 `scripts/check_release.py` 检查必需文件、版本、评测报告、敏感文件、Docker 标记和 API 路径。
- 原因：Day 12 是 v1.0 交付候选，需要一个可重复的本地收口入口，同时不能把评测报告版本误改成产品版本。
- 影响：只改发布元数据和文档/维护脚本，核心 Schema、评分、Graph、RAG 检索契约无变化；已有 API 客户端不需要迁移，健康检查响应中的版本从 `0.7.0` 变为 `1.0.0`。
- 限制：发布检查不能证明 Docker daemon、GLM/BGE 服务或录屏已经运行；这些仍需按 progress.md 逐项记录实际环境结果。
