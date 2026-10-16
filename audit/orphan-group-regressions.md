# 43条correct→wrong逐条分类

固定此前148份参考及同批600条原始候选，不执行新SQL。此表先核对“唯一差别是否为空组行”；可否增加替代参考仍按裁决的总额／占比／产品键Top-N边界单独判定。NULL和空串均视为缺失产品属性，不更改有名称组的值、类型或选择约束。

| 系统 | 题号 | 类别 | 去掉空组后的逐参考结果 |
|---|---|---|---|
| claude_claude_opus_4_7_raw | Q21 | product_identity_or_detail_rows | 产品键／明细任务，不是空属性分组 |
| claude_claude_opus_4_7_raw | Q61 | only_empty_group_row | Q61-1: -1行, correct |
| claude_claude_opus_4_7_raw | Q62 | only_empty_group_row | Q62-1: -1行, correct |
| claude_claude_opus_4_7_raw | Q67 | only_empty_group_row | Q67-1: -1行, correct |
| claude_claude_opus_4_7_raw | Q71 | only_empty_group_row | Q71-1: -1行, correct |
| claude_claude_opus_4_7_raw | Q76 | only_empty_group_row | Q76-1: -1行, correct；Q76-2: -1行, wrong；Q76-3: -1行, wrong |
| claude_claude_opus_4_7_semantic | Q11 | only_empty_group_row | Q11-1: -1行, correct |
| claude_claude_opus_4_7_semantic | Q61 | only_empty_group_row | Q61-1: -1行, correct |
| claude_claude_opus_4_7_semantic | Q62 | only_empty_group_row | Q62-1: -1行, correct |
| claude_claude_opus_4_7_semantic | Q67 | only_empty_group_row | Q67-1: -1行, correct |
| claude_claude_opus_4_7_semantic | Q71 | only_empty_group_row | Q71-1: -1行, correct |
| claude_claude_opus_4_7_semantic | Q76 | only_empty_group_row | Q76-1: -1行, correct；Q76-2: -1行, wrong；Q76-3: -1行, wrong |
| claude_claude_opus_4_7_semantic | Q90 | only_empty_group_row | Q90-1: -1行, correct |
| claude_claude_sonnet_4_6_raw | Q61 | only_empty_group_row | Q61-1: -1行, correct |
| claude_claude_sonnet_4_6_raw | Q62 | only_empty_group_row | Q62-1: -1行, correct |
| claude_claude_sonnet_4_6_raw | Q67 | only_empty_group_row | Q67-1: -1行, correct |
| claude_claude_sonnet_4_6_raw | Q71 | only_empty_group_row | Q71-1: -1行, correct |
| claude_claude_sonnet_4_6_raw | Q76 | only_empty_group_row | Q76-1: -1行, correct；Q76-2: -1行, wrong；Q76-3: -1行, wrong |
| claude_claude_sonnet_4_6_semantic | Q11 | only_empty_group_row | Q11-1: -1行, correct |
| claude_claude_sonnet_4_6_semantic | Q20 | product_identity_or_detail_rows | 产品键／明细任务，不是空属性分组 |
| claude_claude_sonnet_4_6_semantic | Q21 | product_identity_or_detail_rows | 产品键／明细任务，不是空属性分组 |
| claude_claude_sonnet_4_6_semantic | Q24 | only_empty_group_row | Q24-1: -1行, correct |
| claude_claude_sonnet_4_6_semantic | Q34 | product_identity_or_detail_rows | 产品键／明细任务，不是空属性分组 |
| claude_claude_sonnet_4_6_semantic | Q61 | only_empty_group_row | Q61-1: -1行, correct |
| claude_claude_sonnet_4_6_semantic | Q62 | only_empty_group_row | Q62-1: -1行, correct |
| claude_claude_sonnet_4_6_semantic | Q67 | only_empty_group_row | Q67-1: -1行, correct |
| claude_claude_sonnet_4_6_semantic | Q71 | only_empty_group_row | Q71-1: -1行, correct |
| claude_claude_sonnet_4_6_semantic | Q76 | only_empty_group_row | Q76-1: -1行, correct；Q76-2: -1行, wrong；Q76-3: -1行, wrong |
| claude_claude_sonnet_4_6_semantic | Q90 | only_empty_group_row | Q90-1: -1行, correct |
| claude_claude_sonnet_4_6_semantic | Q99 | only_empty_group_row | Q99-1: -1行, correct |
| codex_gpt_5_4_raw | Q61 | only_empty_group_row | Q61-1: -1行, correct |
| codex_gpt_5_4_raw | Q62 | only_empty_group_row | Q62-1: -1行, correct |
| codex_gpt_5_4_raw | Q71 | only_empty_group_row | Q71-1: -1行, correct |
| codex_gpt_5_4_raw | Q76 | only_empty_group_row | Q76-1: -1行, correct；Q76-2: -1行, wrong；Q76-3: -1行, wrong |
| codex_gpt_5_4_semantic | Q11 | only_empty_group_row | Q11-1: -1行, correct |
| codex_gpt_5_4_semantic | Q20 | product_identity_or_detail_rows | 产品键／明细任务，不是空属性分组 |
| codex_gpt_5_4_semantic | Q21 | product_identity_or_detail_rows | 产品键／明细任务，不是空属性分组 |
| codex_gpt_5_4_semantic | Q34 | product_identity_or_detail_rows | 产品键／明细任务，不是空属性分组 |
| codex_gpt_5_4_semantic | Q61 | only_empty_group_row | Q61-1: -1行, correct |
| codex_gpt_5_4_semantic | Q62 | only_empty_group_row | Q62-1: -1行, correct |
| codex_gpt_5_4_semantic | Q71 | only_empty_group_row | Q71-1: -1行, correct |
| codex_gpt_5_4_semantic | Q76 | only_empty_group_row | Q76-1: -1行, correct；Q76-2: -1行, wrong；Q76-3: -1行, wrong |
| codex_gpt_5_4_semantic | Q99 | only_empty_group_row | Q99-1: -1行, correct |

汇总：{"product_identity_or_detail_rows": 7, "only_empty_group_row": 36}
