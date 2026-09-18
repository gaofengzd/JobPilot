# JobPilot

智能求职岗位分析 Agent。项目事实来源：[开发文档](docs/开发文档.md)。

当前迭代：**Day 1 基础设施与数据契约**。业务解析、匹配、RAG、Graph 编排、API、UI 尚未实现。
真实模型调用尚未验收；离线及模拟传输验证与真实服务验证分开记录。

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
