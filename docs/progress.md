# 开发进度

更新时间：2026-09-20
当前迭代：Day 4
版本：0.1.1（确定性匹配能力）
状态：Day 4 实现完成；Matching Engine、项目相关性基线与离线演示验证通过。
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
