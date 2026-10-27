# Q65 原题对照（私有）

- 核查日期：2026-10-28。
- Cube 原文：Which store managers run stores with more than $5M in total all-channel sales?
- 我们的中文：哪些门店经理管理的门店，其全渠道销售总额超过 500 万美元？
- 原文来源：vendor/cube/text_to_sql_benchmark.json，第623行；上游 cubedevinc/semantic-layer-benchmark，提交 4c37310f9fae65255f6d0015475b430ceea3ab1f，来源记录见 vendor/cube/NOTICE.md。
- 对照事实：题库 text_en 与原文完全一致。英文使用复数 stores，未写 each store、per store 或 combined per manager；中文同样未明确逐店或按经理合并。上游 expected_sql 按 StoreManager、StoreName 分组，采用逐店口径。
- 结论：分组粒度未明示的问题已存在于英文问法，未发现中文新增经理汇总口径；上游 SQL 表明其参考采用逐门店解读。此结论区分了问法与参考SQL，不将参考SQL视为问法唯一解释的证明。
- 裁定依据：主仓库 decisions/2026-10-28-reference-rulings-five-questions.md 第一节 Q65；两种问法解读均接受。
