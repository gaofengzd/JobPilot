# 评测数据集

数据集使用合成或脱敏输入及人工期望，不把模型当前输出直接当标准答案。

Day 9 基础口径固定为 33 条：3 个简历、10 个 JD、10 个匹配、5 个 RAG、5 个异常案例。仓库还保留批量、工作流、引用支持和超过基础数量的回归案例；额外案例不改变 33 条基线定义。

`citation_cases.json` 保存人工 Citation Support 判断；`failure_analyses.json` 保存已观察失败的原因、修复、回归入口和来源。`error_cases.json` 持续追加新失败案例。

运行器支持 deterministic、local、full 三种模式，结果写入 `eval/reports`。只有 full 会调用 GLM；只有 local/full 会真实加载本地 BGE。报告必须保留模式和限制，不能把不同运行类型合并成同一种验证。
