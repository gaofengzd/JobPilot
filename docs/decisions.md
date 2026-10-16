# 决策记录

## 2026-10-14 / 退役 Streamlit，统一 Vue 前端

- 删除 `ui/app.py`，移除 `streamlit` 与旧页面专用的 `requests` 依赖；`frontend/` 的 Vue 3 + TypeScript + Vite 页面成为唯一维护的网页客户端。
- Docker 镜像只提供 FastAPI API，移除 8501 暴露和 Streamlit 覆盖启动方式；浏览器前端独立通过 Vite 开发服务器运行。
- 原因：项目当前只需要一个可验证的浏览器入口，维护两套 UI 会重复输入校验、错误展示、文档和测试；Vue 页面已满足当前功能。
- 影响：Streamlit 启动命令、8501 端口和 `ui/app.py` 不再有效；API、`/agent/run` 契约、核心 Schema、业务计算、RAG 与模型调用无迁移变化。历史记录中的 Streamlit 仅说明过去的实现状态。

## 2026-10-14 / 单岗位分析的前端输入

- Vue 的五个岗位输入框作为 1–5 个 JD 的上限保留，但将必填条件从五个改为至少一个；空值不会发送给 API。
- 目标岗位下拉选项仅包含非空 JD，选项索引与紧凑后的 `raw_jobs` 顺序一致。
- 原因：`AgentInput` 和工作流本来支持一个或多个岗位，前端强制五个输入与后端契约不一致，阻碍单岗位验证。
- 影响：无新增依赖、无 API 或 Schema 迁移；批量分析仍可在填写多个 JD 时使用。

## 2026-10-14 / 简历 grounding 失败值的受控诊断日志

- 简历抽取字段或 evidence quote 未通过原文 grounding 时，白名单 JSON 事件记录失败字段、问题类型及最多 2000 字符的未通过值，包含 request_id 以关联工作流；普通模型内容采集开关不控制这一项诊断值。
- API 对外错误改为通用 `ResumeGroundingError` 消息，详细失败值只进入本地 `log/jobpilot.log`，不回显浏览器。
- 原因：真实运行只看到 grounding 类型，无法辨认是哪个字段被改写或拼接；定位该类失败需要检查对应抽取值。
- 影响：本地日志可能包含简历个人信息，README 要求限制日志访问并在排障后删除；核心 Schema、严格 grounding、重试次数及 502 契约不变。

## 2026-10-14 / 测试文件的多岗位边界

- `docs/岗位jd.txt` 是包含 jd1--jd5 的多岗位汇总文件，而 CLI/API 的 `raw_jobs` 约定是一项岗位一段文本。
- 测试保留该边界：整文件作为一个 JD 的调用出现 60 秒模型超时，系统返回失败报告；不通过放宽解析规则掩盖输入格式问题。
- 页面验证应将五个岗位段落拆分后分别提交；后续若需要文件导入多岗位，应新增明确的分段解析契约和测试，不在本次范围内。

## 2026-10-14 / GLM 结构化抽取关闭思考模式

- 中文长简历真实运行中，GLM-4.7 在 `function_calling` 抽取阶段耗时接近 60 秒并偶发 grounding/结构化失败。
- 对结构化抽取请求增加智谱兼容的 `thinking.type=disabled`，默认可由 `LLM_THINKING_TYPE` 配置；不改变输出 Schema 或 Python 计算职责。
- 影响是抽取请求更快、更稳定；需要复杂推理的 Future Work 不在本次范围内。

## 2026-10-14 / 文件日志与内容采集开关

- 日志写入终端和 `log/jobpilot.log`，以便后端窗口关闭后仍可追踪请求。
- 模型日志记录显式访问地址、模型名、请求/响应长度、SHA-256 和 token，不默认记录简历、JD、Prompt 或模型原文。
- 增加 `LOG_CAPTURE_CONTENT` 开关，默认 `false`；仅本地排障临时开启并限制预览长度，避免将个人信息和密钥写入日志。

## 2026-10-14 / 全流程 JSON 日志

- 为定位 `/agent/run` 的模型、RAG、Tool 或 Reflection 失败，增加请求、服务初始化、工作流节点和最终报告的生命周期日志。
- 统一复用现有白名单 JSON logger，日志只允许 request_id、node、status、耗时、岗位索引、token 统计和错误类型等元数据；禁止写入用户输入、Prompt、模型回复和原始异常。
- 节点包装只观察调用，不改变节点返回值和 Graph 分支；失败仍沿用现有 API 错误映射。

## 2026-10-14 / LLM 请求忽略环境代理

- 实际问题表现为独立 smoke test 与 Uvicorn 完整请求的模型请求结果不一致；代码未配置代理，但底层 HTTP 客户端默认会读取进程环境代理。
- 因项目通过 `LLM_BASE_URL` 明确指定智谱 API，`LLMClient` 使用 `httpx.Client(trust_env=False)` 直连该地址，避免不可用的 shell 代理影响模型调用。
- 影响是 JobPilot 不再使用环境代理访问 LLM；若部署环境必须经代理访问外网，需要后续增加显式、可审计的代理配置，不在本次迭代扩大范围。

## 2026-10-14 / 增加 Vue 前端并保留 Streamlit

- 为便于浏览器验证，新增独立 Vue 3 + TypeScript + Vite 客户端；现有 Streamlit 保留作为兼容 Demo，不扩大 v1.0 后端范围。
- Vue 只负责表单、HTTP 请求、错误呈现和报告展示，继续复用 `/agent/run` 与现有 FinalReport 契约；不把匹配、评分或业务计算放到浏览器。
- 前端 API 地址通过 `VITE_API_BASE_URL` 配置，默认 `http://127.0.0.1:8000`；开发服务器默认端口 5173。

## 2026-10-14 / 本地前后端跨域

- Vue 开发服务器与 FastAPI 使用不同端口，浏览器请求需要 CORS；FastAPI 仅允许本地 `localhost/127.0.0.1` 的 5173 和 8501 来源。
- 不允许任意来源、不允许凭据，不改变业务接口或数据契约；生产部署若更换域名需显式补充白名单。

## 2026-10-13 / 保留 API 受控错误并改善 UI 展示

- API 已将模型、结构化输出和 grounding 错误安全映射为 502；前端此前丢弃了响应 JSON，导致用户无法区分失败原因。
- 仅在 Streamlit 客户端读取并展示已有的 `detail.code` / `detail.message`，不暴露 provider 原始异常，不改变公共 API 契约。
- 影响范围限于 UI 诊断；真实模型调用仍需用页面显示的具体错误继续验证。

## 2026-10-13 / README 增加 CMD 启动说明

- 用户使用 Windows CMD 手动启动项目，补充后端和 Streamlit 前端的双窗口命令。
- 前端命令在当前 CMD 会话设置 `STREAMLIT_CONFIG_DIR` 到项目内的 `.streamlit`，避免默认用户目录权限问题；不新增依赖，不改变 API 或公共 Schema。
- 验证方式为 README 文档检查和 Git 差异检查。

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

## ADR-034：日志时间戳使用可配置本地时区

- 日期：2026-10-15
- 状态：已采用
- 决策：日志 JSON 时间戳默认使用 `Asia/Shanghai`，通过 `LOG_TIMEZONE` 可覆盖；始终保留 ISO 8601 时区偏移。
- 原因：原实现固定使用 UTC，容易与本地运行窗口显示的北京时间产生 8 小时误差。
- 影响：日志字段不变，默认时间显示为 `+08:00`；无效时区回退到 `Asia/Shanghai`，已有日志不改写。

## ADR-035：简历 grounding 支持有限连续行

- 日期：2026-10-15
- 状态：已采用
- 决策：CandidateProfile 非空文本和 EvidenceRef.quote 可匹配单行，或最多 3 条同页/同段且物理行号连续的原文；拼接只做空白归一化，locator 记录起止行。
- 原因：PDF 文本抽取及排版会把一个句子断成相邻物理行；原先逐行匹配会误拒绝真实原文。必须覆盖这一版式，同时避免将模型概括或跳行拼接当成事实。
- 影响：CandidateProfile/EvidenceRef/API Schema 不变；多行 locator 新增 `start-end` 表示。新增确定性 grounding eval，真实模型准确率需另行验证。
- 边界：最多 3 行，不跨页/文本段，不跨行号缺口，不允许同义改写；仍最多执行一次模型修复。

## ADR-036：Grounding 查找统一清洗不可见字符

- 日期：2026-10-15
- 状态：已采用
- 决策：原文行与模型抽取值在 grounding 查找前使用同一 lookup 规范化：Unicode NFKC、大小写折叠，仅保留可见字母、数字和组合标记，忽略空白、标点、符号及 Unicode 控制/格式字符（包括零宽字符、BOM、软连字符）。
- 原因：PDF 文本层和模型输出可能在换行、空格或不可见字符上存在表示差异，单边或仅空白折叠会误报事实不一致。
- 影响：只影响 `contains_exact_span`、`locate_quote` 及 evidence 去重的查找口径；原始 `ResumeDocument`、CandidateProfile 和 EvidenceRef 内容保持不变，Schema/API 不变。新增不可见字符、空白和标点差异回归测试。

## ADR-037：JD grounding 复用可见文字与连续行口径

- 日期：2026-10-16
- 状态：已采用
- 决策：`JobDocument` 与 `ResumeDocument` 共享同一查找语义：lookup 只使用可见字母/数字/组合标记（NFKC + casefold），字段值与 evidence.quote 可匹配单行或最多 3 条行号连续的 JD 行，locator 支持 `line:N-line:M`；marker 分类校验与占位符集合也统一在 normalize 后比较。
- 原因：ADR-036 把 lookup 改成仅保留可见字符后，JD 侧三处隐式假设失效——原始英文 marker 中的空格在无空格行内不再匹配，占位符集合按原文写法比较，以及 Reflection 词边界正则在无分隔符文本上永远失败；这些共同导致真实请求中 JD 全量 grounding 误拒（前端表现为 "Selected job index 0 could not be analyzed"）。
- 影响：JobProfile/EvidenceRef Schema 不变；JD 证据引用从仅单行放宽为最多 3 条相邻行，与简历口径一致；`_mentions` 分词边界修复覆盖 Reflection 全部检查。新增确定性回归测试，真实模型结果需另行验证。
- 边界：最多 3 行、不跳行、不允许语义改写；连续性按物理行号判定，与简历实现一致。

## ADR-038：JD grounding 失败写入独立诊断日志

- 日期：2026-10-16
- 状态：已采用
- 决策：JD 原文校验失败时写入 `jobs.grounding.failed`，字段与 resume 侧 `resume.grounding.failed` 对齐（request_id、job_index、node、error_type、grounding_issue、unsupported_count/fields/preview），且不受 `LOG_CAPTURE_CONTENT` 控制。
- 原因：`analyze_jobs` 会捕获 `JobGroundingError` 并写入 `job_errors`，节点仍标记为 success，最终只表现为 `analyze_gap` 的 "Selected job index N could not be analyzed"。原日志不记录失败原因，必须临时开启内容捕获才能定位，排障成本高且容易误判为索引错位。
- 影响：新增 `job_index` 日志字段（已在 `EVENT_FIELDS` 白名单内）；`ground_job_profile` 新增可选 `request_id` 参数，兼容既有调用；`JobProfile`/`EvidenceRef`/API Schema 不变。新增字段路径感知的 `_profile_string_items` 供日志精确标注字段。
- 边界：日志只记录未通过校验的字段名和最多 2000 字符的值预览；仍属含业务文本的本地文件，建议排障后删除。

## ADR-039：工作流输入收紧为单 JD

- 日期：2026-10-16
- 状态：已采用
- 决策：`AgentInput.raw_jobs` / `InternalInput.raw_jobs` / `JobBatchRequest.raw_jobs` 均限制为恰好一项，`Settings.max_jobs` 固定为 1，`selected_job_index` 恒为 0；前端只保留一个 JD 输入框。
- 原因：维护者决定 v1.0 以「一次分析一个岗位」为交互模型。原 5 输入框设计让用户容易把含多个岗位的整份文件粘进单个输入框，模型只能产出混合画像，分类判定必然失败并表现为「选定岗位无法分析」。
- 影响：`create_initial_state` 去掉 `max_jobs` 参数；空数组或多 JD 在模型调用前返回 422。`job_errors`、`job_profiles`、`batch_statistics` 字段与批量统计模块保留，语义改为「请求规模恒为 1 时的退化情形」；单岗位失败时报告为 `failed`，`valid_jobs=0`、`failed_jobs=1`。核心业务 Schema 与评分/RAG/Graph 拓扑不变，但**这是破坏性契约变更**：任何提交多 JD 的调用方需要改为逐岗位多次请求。
- 边界：恢复多岗位需同时放开三个 Schema 上限、`MAX_JOBS` 和前端输入，三者缺一不可。

## ADR-040：required/preferred 支持中文分节标题

- 日期：2026-10-16
- 状态：已采用
- 决策：required 标记增加 `任职要求`/`岗位要求`/`职位要求`/`任职资格`/`硬性要求`/`必备`/`必须`；preferred 增加 `加分项`/`加分`/`优先`。除同行标记外，新增分节标题识别：某行去除首尾标点后恰好等于某个标记即视为标题，其后各行归入该节直到下一个标题。行内相反标记优先于父节归属。
- 原因：真实中文 JD 的常见版式是 `任职要求：` 单独成行、编号条款在下方，与英文 `Required skills: ...` 的同行版式不同。既有的同行匹配对这种版式结构性失效，导致本可正确抽取的技能被判定为「缺少明示分类标记」而拒绝。
- 影响：`_has_marked_support` 改为委托 `JobDocument.has_marked_support`，分节状态在同一方法内维护；required 与 preferred 各自只接受本类型标记，标题不会跨类型串扰。同行标记行为不变，向后兼容。`JobProfile` Schema 不变。
- 边界：标题必须独占一行（允许尾随标点）；标题只在其后的行内生效，不会回溯到标题之前的关键词区。`优先` 等短标记仍可能命中正文措辞，因此保留了「行内相反标记优先」规则来降低误判，未引入任何语义相似度判定。

## ADR-041：CLI 与本地 env 模板纳入单 JD 契约

- 日期：2026-10-16
- 状态：已采用
- 决策：`main.py` 三处 `create_initial_state` 调用删除 `max_jobs` 传参；`--run-workflow` 由 `nargs="+"` 改为 `nargs=2`（一个简历 + 恰好一个 JD），`--selected-job-index` 增加 `choices=[0]`；`.env` 与 `.env.example` 的 `MAX_JOBS` 由 20 改为 1；新增测试 `test_shipped_env_example_loads_with_project_defaults` 用 `Settings(_env_file=...)` 真实加载两个模板文件并断言 `max_jobs == 1`。
- 原因：ADR-038/039 收紧 Schema 与 `Settings.max_jobs` 后，测试套件仍全绿（211 passed），但真实入口是坏的——CLI 会因 `create_initial_state` 不再接受 `max_jobs` 抛 `TypeError`，本地 `.env` 的 `MAX_JOBS=20` 会让 `load_settings()` 抛 `ConfigurationError`。根因是**所有测试都显式构造 `Settings` 与直接调用 API/Graph，从不经过 CLI，也不读 `.env`**，配置模板与入口脚本因而处于测试盲区。这类「契约变更只改了一半」的漏改代价是发布即不可用，必须在收尾阶段用真实入口冒烟验证而非只看测试计数。
- 影响：CLI 与真实配置加载对齐单 JD 契约；`MAX_JOBS` 成为有测试守卫的字段，模板陈旧值会在 CI 阶段而非用户首次运行时暴露。`--demo-v02` 保持 5 个合成岗位用于批量统计演示，但其帮助文案已标注「合成批量演示，实时链路为单 JD」，避免被误读为支持多岗位输入。
- 边界：`check_release.py` 需要 `PYTHONPATH=.` 才能 import `app`，直接运行会报 `No module named 'app'`；这是脚本既有的调用约定，未在本次改动中调整。

## ADR-042：术语匹配统一为「仅 ASCII 边缘要求词边界」

- 日期：2026-10-17
- 状态：已采用
- 决策：在 `app/utils/resume_files.py` 新增唯一术语匹配器 `mentions_term(text, term)`，`app/agents/reflection.py` 与 `app/agents/gap_analyzer.py` 共用它。匹配前两侧均走 `normalize_text`；边界检查只在 needle 的 ASCII 字母/数字边缘生效，CJK 边缘不要求边界。Reflection 原有的本地 `_mentions` 实现删除。`frontend/src/App.vue` 的匹配分数字段由 `overall_score` 更正为 `score`。
- 原因：`GapAnalyzer._evidence_for_skill` 用归一化子串附加证据，`Reflection._mentions` 用词边界复查同一条证据，二者结论相反。中文没有分词符，`\w+` 会把整句并成一个 token，因此 `熟悉<技能>；` 这类最常见的版式下每个中文技能都被判为缺少 JD 证据。由于 `repair_outputs` 只是确定性重跑，两次修复必然无效，最终 `finalize_reflection_failure` 清空 gaps、检索上下文、学习计划与简历建议并返回 `partial`。根因不是某个正则写错，而是**同一事实存在两个判定器**——这一条比任何单点修复都重要。
- 影响：中文与中英混排 JD 的技能 gap 能通过校验，报告恢复 `success` 并保留学习计划与简历建议；`Java` 不命中 `JavaScript`、`SQL` 不命中 `MySQL` 的防护保持不变。`mentions_term` 不再对 needle 施加 `normalize_skill` 别名映射：匹配对象是 JD 原文措辞，别名展开会让 `K8s` 一类技能找不到自己的原文。`_evidence_for_skill` 保留归一化子串回退，只放宽「哪些引用算作支撑」，使已被测试与 eval 固定的 `lacks JD evidence` 契约不会新增触发（详见边界）。`JobProfile`/`MatchResult`/`SkillGap` Schema 与 Graph 拓扑不变。
- 边界：`Java` 仅作为 `JavaScript` 片段出现时，回退仍会附加证据而 Reflection 仍会拒绝，理论上可再次触达修复循环；真正的修法是让 `JdAnalyzer` 拒绝「技能仅为更长拉丁词片段」的抽取，属上游独立问题。前端 `overall_score` 之所以能长期静默存在，是因为 `type Report = Record<string, any>` 让 `vue-tsc` 失去检查能力，补类型是后续建议而非本次改动。另外 `eval/run_eval.py` 会覆盖被 `check_release` 断言为 33 例的冻结报告，运行 eval 会使发布检查失败，二者口径待对齐。

## ADR-043：eval 默认输出与冻结发布报告解耦

- 日期：2026-10-17
- 状态：已采用
- 决策：`eval/run_eval.py` 的默认输出前缀由 `eval/reports/day9-v0.6` 改为 `eval/reports/latest`，新增 `REPORTS`/`FROZEN_REPORT` 常量并抽出 `build_parser()`；冻结报告仅在显式传入 `--output-prefix eval/reports/day9-v0.6` 时才会被重写。新增 2 条测试锁定该契约。
- 原因：同一文件被**同时**当作「eval 的默认输出目标」与「`check_release` 断言的只读发布证据」。ADR-040 把 JD 案例由 10 增至 12 后，实跑 case 数变为 35，而冻结报告记 33，于是不带参数运行一次 eval 就会覆盖证据并使发布检查报 `must contain 33 base cases`。这不会影响应用运行（前端/API/工作流都不读 `eval/`），但会让发布闸门因与质量无关的原因变红；若新报告被提交，闸门会长期为红，进而掩盖真实回归。选择改默认输出而非改断言数字，是因为断言 33 是刻意的 freeze guard，每次数据集变动都去改数字会把守卫降级为噪声。
- 影响：日常运行 eval 不再有副作用，输出落到被 `.gitignore` 排除的 `eval/reports/latest.{json,md}`；`check_release` 的冻结语义与断言值保持不变。刷新正式报告需显式指定前缀，命令已在 `README.md` 与 `eval/reports/README.md` 注明。`build_parser()` 的抽取使默认值可被测试直接断言。
- 边界：冻结报告与当前数据集仍存在 33 与 35 的口径差异，这是历史快照语义而非缺陷；若将来要重新冻结，需跑 `full` 模式真实调用 GLM 并显式覆盖，本 ADR 不改变该成本。`scripts/check_release.py` 需 `PYTHONPATH=.` 才能 import `app`，属既有调用约定。
