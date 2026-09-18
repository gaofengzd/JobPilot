# 开发进度

更新时间：2026-09-18
当前迭代：Day 1
版本：0.0.1（基础设施，不是 v0.1 业务里程碑）
状态：本地实现及离线验证完成，真实模型连通性待配置和验收。
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
