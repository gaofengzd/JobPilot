# Evaluation reports

`day9-v0.6.json` 是机器可读的正式评测结果，`day9-v0.6.md` 是同一结果的审阅版。

报告记录运行模式、数据量、指标、基线差异、失败列表、重复运行观察和限制。报告内不包含简历全文、JD 全文、API 密钥或模型原始回复。

重新生成：

```powershell
uv run --locked python -m eval.run_eval --mode full --output-prefix eval/reports/day9-v0.6
```

`full` 会调用已配置的模型并产生真实用量；不应在无意联网时运行。
