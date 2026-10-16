# Evaluation reports

`day9-v0.6.json` 是机器可读的正式评测结果，`day9-v0.6.md` 是同一结果的审阅版。

该文件是**冻结的发布证据**：`scripts/check_release.py` 会断言它的 `report_version`、`base_case_count` 与 `failure_analyses`。因此它只在明确要求时重写，不会被日常运行覆盖。

报告记录运行模式、数据量、指标、基线差异、失败列表、重复运行观察和限制。报告内不包含简历全文、JD 全文、API 密钥或模型原始回复。

## 默认输出

不带 `--output-prefix` 时，报告写入 `eval/reports/latest.{json,md}`。该路径落在 `.gitignore` 的 `eval/reports/*` 规则内，属于可随意覆盖的临时产物，不会污染版本库，也不会让发布检查失败。

```powershell
uv run --locked python -m eval.run_eval --mode deterministic
```

## 重新生成正式报告

必须显式指定前缀：

```powershell
uv run --locked python -m eval.run_eval --mode full --output-prefix eval/reports/day9-v0.6
```

`full` 会调用已配置的模型并产生真实用量；不应在无意联网时运行。该命令会改写被 `check_release` 断言的正式报告，只有在有意重新冻结时才执行。
