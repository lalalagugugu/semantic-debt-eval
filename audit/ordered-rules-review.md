# 显式排序键逐参考审阅

排序键只在题库维护阶段从实际参考排序和现有声明映射并持久化；评分器不读SQL、不按题猜。column为参考列0起位置；方向及复合顺序逐字声明。块相等复用全局量纲固定量化，不用结果容差。EN74原SQL按未投影的行号排序，沿用此前已批准的selection.output_order（门店、产品销售额）声明，不新增隐藏列或改变原参考。

| 范围／参考 | 最终排序 | 持久化order_by | 映射来源 |
|---|---|---|---|
| 当前/refs/cube/Q07-1.csv | UnitPrice DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q25-1.csv | avg_daily_sales DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q27-1.csv | margin_pct DESC | [{"column": 3, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q33-1.csv | co_order_count DESC,product1_key,product2_key | [{"column": 4, "descending": true}, {"column": 0, "descending": false}, {"column": 1, "descending": false}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q33-2.csv | co_order_count DESC,product1_key,product2_key | [{"column": 4, "descending": true}, {"column": 0, "descending": false}, {"column": 1, "descending": false}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q45-1.csv | sales_per_sqft DESC | [{"column": 3, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q46-1.csv | profit DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q46-2.csv | profit DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q67-1.csv | avg_realized_price DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q67-2.csv | avg_realized_price DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q69-1.csv | revenue DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q69-2.csv | revenue DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q73-1.csv | gap DESC | [{"column": 3, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q78-1.csv | rnk | [{"column": 2, "descending": false}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q79-1.csv | attainment_pct DESC | [{"column": 3, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q85-1.csv | bucket, attainment_pct DESC | [{"column": 0, "descending": false}, {"column": 4, "descending": true}] | existing explicit selection.output_order |
| 当前/refs/cube/Q87-1.csv | days_of_coverage ASC | [{"column": 3, "descending": false}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q88-1.csv | s.spend_2009 DESC | [{"column": 1, "descending": true}] | outer ORDER BY uses projected ROUND value under the existing reference/tie precision contract |
| 当前/refs/cube/Q92-1.csv | gross_margin_dollars DESC | [{"column": 2, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q94-1.csv | qoq_pct_change ASC | [{"column": 3, "descending": false}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q97-1.csv | h2_vs_h1_pct DESC | [{"column": 3, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q97-2.csv | sales_increase DESC | [{"column": 4, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 当前/refs/cube/Q98-1.csv | peak_quarter_share_pct DESC | [{"column": 1, "descending": true}] | existing explicit selection.output_order |
| 当前/refs/cube/Q98-2.csv | year,peak_quarter_share_pct DESC | [{"column": 1, "descending": false}, {"column": 2, "descending": true}] | existing explicit selection.output_order |
| 当前/refs/new/Q117-1.csv | decline_pct DESC,decline_amount DESC | [{"column": 2, "descending": true}, {"column": 4, "descending": true}] | existing explicit selection.output_order |
| 原始/7 | UnitPrice DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/25 | avg_daily_sales DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/27 | margin_pct DESC | [{"column": 3, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/45 | sales_per_sqft DESC | [{"column": 3, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/46 | profit DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/67 | avg_realized_price DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/69 | revenue DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/73 | gap DESC | [{"column": 3, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/74 | s.StoreName, r.rn | [{"column": 0, "descending": false}, {"column": 2, "descending": true}] | existing explicit selection.output_order |
| 原始/78 | rnk | [{"column": 2, "descending": false}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/79 | attainment_pct DESC | [{"column": 3, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/85 | bucket, attainment_pct DESC | [{"column": 0, "descending": false}, {"column": 4, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/87 | days_of_coverage ASC | [{"column": 3, "descending": false}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/88 | s.spend_2009 DESC | [{"column": 1, "descending": true}] | outer ORDER BY uses projected ROUND value under the existing reference/tie precision contract |
| 原始/92 | gross_margin_dollars DESC | [{"column": 2, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/94 | qoq_pct_change ASC | [{"column": 3, "descending": false}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/97 | h2_vs_h1_pct DESC | [{"column": 3, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |
| 原始/98 | peak_quarter_share_pct DESC | [{"column": 1, "descending": true}] | outer ORDER BY resolved to projected reference columns/aliases |

当前25份有序参考全部补齐；原公开600条验证范围中18份有序原始参考排序键另存于配套JSON。Q33无可用公开原始参考，不伪造其排序元数据。实际英文锚点按T11规则选择：同结构逐参考rules原样透传，8份结构不同的规则由review_anchor_rules.py单独更新。
