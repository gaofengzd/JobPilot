# JobPilot 协作规则

每次会话先读取 docs/开发文档.md、docs/progress.md、docs/decisions.md、README.md 和相关代码。
以开发文档为事实来源，只实现当前迭代。修改前说明模块、契约、依赖和验证方式。
保持 Schema 和层间边界；计算、统计与评分由 Python 完成。
新失败案例加入 eval，不能捏造简历事实或测试结果。
架构变更先说明理由和影响；不擅自增加多 Agent、自动投递、爬虫等范围。
每完成一部分功能，更新 docs/progress.md 的完成项和实际验证；
同步在 docs/decisions.md 记录本部分决策及影响（无新决策时也注明）。
明确区分离线验证、mock、真实模型和未完成事项。
使用 uv 管理依赖和 .venv；提交 pyproject.toml 与 uv.lock。
requirements.txt 只通过 uv export 生成，不手工修改。
