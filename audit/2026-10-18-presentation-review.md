# eval-v1.1 展示约定与逐参考变更审计

基线455e96f；122题、137份参考。137份必答列投影后的自匹配通过。新增Q38总准确率，不删除原品类参考；不打冻结tag。

## 原来不必答、现在必答（逐列）

| 参考 | 原列号 | 新列号 | 列名 | 原因 |
|---|---:|---:|---|---|
| refs/cube/Q20-2.csv | 0 | 0 | ProductKey | 缺失或占位名称的已有对象键裁决 |
| refs/cube/Q22-1.csv | 0 | 0 | c.CustomerKey | 缺失或占位名称的已有对象键裁决 |
| refs/cube/Q22-1.csv | 5 | 5 | rn | 新系统约定：已有分母／名次／变化表达 |
| refs/cube/Q24-1.csv | 2 | 2 | total_sales | 新系统约定：已有分母／名次／变化表达 |
| refs/cube/Q34-1.csv | 2 | 2 | avg_inventory | 新系统约定：已有分母／名次／变化表达 |
| refs/cube/Q34-1.csv | 4 | 4 | ProductKey | 缺失或占位名称的已有对象键裁决 |
| refs/cube/Q38-2.csv | 1 | 1 | actual | 新系统约定：已有分母／名次／变化表达 |
| refs/cube/Q50-1.csv | 2 | 2 | growth_pct | 已裁决必答，补录原清单遗漏 |
| refs/cube/Q78-1.csv | 2 | 2 | rnk | 已裁决必答，补录原清单遗漏 |
| refs/cube/Q83-1.csv | 0 | 2 | customers（首年行） | 已裁决必答，补录原清单遗漏；首年行 |
| refs/cube/Q85-1.csv | 3 | 3 | quota_amt | 新系统约定：已有分母／名次／变化表达 |
| refs/cube/Q87-1.csv | 2 | 2 | avg_daily_qty | 新系统约定：已有分母／名次／变化表达 |
| refs/cube/Q87-1.csv | 4 | 4 | ProductKey | 缺失或占位名称的已有对象键裁决 |
| refs/cube/Q96-1.csv | 1 | 1 | cohort_size | 新系统约定：已有分母／名次／变化表达 |
| refs/cube/Q99-1.csv | 3 | 3 | weekend_lift_pct | 已裁决必答，补录原清单遗漏 |
| refs/new/Q112-1.csv | 0 | 0 | EmployeeKey | 缺失或占位名称的已有对象键裁决 |

## 由必答改为不必答（逐列）

| 参考 | 列号 | 列名 | 原因 |
|---|---:|---|---|
| refs/cube/Q27-1.csv | 1 | UnitPrice | 比率本身不必答；第15条只在输出比率时要求分母 |
| refs/cube/Q79-1.csv | 2 | quota | 比率本身不必答；第15条只在输出比率时要求分母 |
| refs/cube/Q92-1.csv | 1 | revenue | 比率本身不必答；第15条只在输出比率时要求分母 |
| refs/cube/Q98-1.csv | 3 | annual_sales_amount | 比率本身不必答；第15条只在输出比率时要求分母 |
| refs/cube/Q98-2.csv | 4 | annual_sales_amount | 比率本身不必答；第15条只在输出比率时要求分母 |
| refs/cube/Q84-1.csv | 4 | total_revenue_amount | 比率本身不必答；第15条只在输出比率时要求分母 |
| refs/cube/Q84-2.csv | 4 | total_revenue_amount | 比率本身不必答；第15条只在输出比率时要求分母 |
| refs/cube/Q65-2.csv | 1 | StoreName | 原裁决只要求经理标识，不要求门店 |

## 逐参考改动

| 参考 | SQL变化 | CSV变化 | 行数（旧→新） | 必答列 |
|---|---|---|---|---|
| refs/cube/Q01-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q02-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q03-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q04-1.csv | False | False | 644→644 | [0] |
| refs/cube/Q05-1.csv | False | False | 8→8 | [0, 1] |
| refs/cube/Q06-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q07-1.csv | False | True | 14→14 | [0, 2] |
| refs/cube/Q08-1.csv | False | False | 17→17 | [0, 1] |
| refs/cube/Q09-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q10-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q11-1.csv | False | False | 9→9 | [0, 1] |
| refs/cube/Q12-1.csv | False | False | 12→12 | [0, 1] |
| refs/cube/Q13-1.csv | False | False | 306→306 | [1, 2, 3, 4] |
| refs/cube/Q14-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q15-1.csv | False | False | 29→29 | [0, 1] |
| refs/cube/Q16-1.csv | False | False | 2→2 | [0, 1] |
| refs/cube/Q17-1.csv | True | True | 2→2 | [0, 2, 3] |
| refs/cube/Q18-1.csv | False | False | 1→1 | [0, 1] |
| refs/cube/Q19-1.csv | False | False | 2→2 | [0, 1] |
| refs/cube/Q20-2.csv | False | False | 429→429 | [0, 1] |
| refs/cube/Q21-1.csv | False | False | 306→306 | [1, 2] |
| refs/cube/Q22-1.csv | True | False | 65→65 | [0, 1, 2, 3, 5] |
| refs/cube/Q23-1.csv | False | False | 12→12 | [0, 2] |
| refs/cube/Q24-1.csv | False | False | 9→9 | [0, 2, 3] |
| refs/cube/Q25-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q26-1.csv | False | True | 2→2 | [0, 1] |
| refs/cube/Q27-1.csv | False | True | 12→12 | [0, 4] |
| refs/cube/Q28-1.csv | False | False | 2→2 | [0, 1] |
| refs/cube/Q29-1.csv | True | True | 1→1 | [0, 1] |
| refs/cube/Q30-1.csv | False | False | 31→31 | [0, 2] |
| refs/cube/Q31-1.csv | True | True | 8→16 | [0, 1, 2] |
| refs/cube/Q32-1.csv | False | False | 1→1 | [1] |
| refs/cube/Q33-1.csv | False | True | 20→20 | [0, 1, 2, 3, 4, 5] |
| refs/cube/Q34-1.csv | False | False | 2508→2508 | [0, 2, 3, 4] |
| refs/cube/Q35-1.csv | False | False | 293→293 | [0, 1, 3, 4] |
| refs/cube/Q36-1.csv | False | False | 3→3 | [0, 1] |
| refs/cube/Q37-1.csv | False | False | 306→306 | [0, 1, 2] |
| refs/cube/Q38-2.csv | False | False | 8→8 | [0, 1, 3] |
| refs/cube/Q38-3.csv | True | True | None→1 | [0, 2] |
| refs/cube/Q39-1.csv | False | False | 30→30 | [0, 1, 2, 3, 4, 5] |
| refs/cube/Q39-2.csv | False | False | 30→30 | [0, 1, 2, 3, 4, 5] |
| refs/cube/Q40-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q41-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q42-1.csv | True | True | 3→3 | [0, 1, 2, 3] |
| refs/cube/Q42-2.csv | False | False | 3→3 | [0, 1] |
| refs/cube/Q43-1.csv | False | False | 3→3 | [0, 1] |
| refs/cube/Q43-2.csv | False | False | 29→29 | [0, 1] |
| refs/cube/Q44-1.csv | True | True | 3→3 | [0, 1, 2, 3] |
| refs/cube/Q44-2.csv | False | True | 36→36 | [0, 1, 2] |
| refs/cube/Q45-1.csv | False | True | 306→306 | [0, 1, 2, 3, 4] |
| refs/cube/Q46-1.csv | False | False | 1→1 | [0, 1] |
| refs/cube/Q46-2.csv | False | False | 1→1 | [0, 1] |
| refs/cube/Q47-1.csv | False | False | 299→299 | [0, 1] |
| refs/cube/Q48-1.csv | False | False | 2→2 | [0, 1, 2] |
| refs/cube/Q48-2.csv | False | False | 1→1 | [0] |
| refs/cube/Q48-3.csv | False | False | 1→1 | [0] |
| refs/cube/Q49-2.csv | False | False | 420→420 | [1, 2] |
| refs/cube/Q50-1.csv | False | False | 1→1 | [2, 3] |
| refs/cube/Q51-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q52-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q53-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q54-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q55-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q56-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q57-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q58-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q59-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q60-1.csv | False | False | 1→1 | [0] |
| refs/cube/Q61-1.csv | False | False | 31→31 | [0] |
| refs/cube/Q62-1.csv | False | False | 12→12 | [0, 1, 2] |
| refs/cube/Q63-1.csv | False | False | 5→5 | [0, 1] |
| refs/cube/Q64-1.csv | True | True | 12→12 | [0, 1, 2, 3] |
| refs/cube/Q65-2.csv | True | True | 303→303 | [0, 3] |
| refs/cube/Q66-1.csv | False | True | 4→4 | [0, 1] |
| refs/cube/Q67-1.csv | False | True | 18→18 | [0, 3] |
| refs/cube/Q68-1.csv | False | False | 2→2 | [0, 1, 2] |
| refs/cube/Q69-1.csv | True | True | 1→1 | [0, 3, 4] |
| refs/cube/Q70-1.csv | False | False | 4→4 | [0, 1, 2] |
| refs/cube/Q71-1.csv | False | False | 8→8 | [0, 1, 2] |
| refs/cube/Q72-1.csv | False | True | 12→12 | [0, 1, 3] |
| refs/cube/Q73-1.csv | False | True | 10→10 | [0, 4] |
| refs/cube/Q74-1.csv | True | True | 925→925 | [0, 1, 3, 5, 6] |
| refs/cube/Q75-1.csv | True | True | 1470→1470 | [0, 1, 5] |
| refs/cube/Q76-1.csv | True | True | 9→9 | [0, 1, 2, 3] |
| refs/cube/Q76-2.csv | True | True | 9→9 | [0, 1, 2, 3] |
| refs/cube/Q77-1.csv | True | True | 12→12 | [0, 3, 4] |
| refs/cube/Q78-1.csv | True | True | 1→1 | [0, 2, 3, 4] |
| refs/cube/Q79-1.csv | False | True | 42→42 | [0, 4] |
| refs/cube/Q80-1.csv | False | False | 29→29 | [0, 2] |
| refs/cube/Q81-1.csv | False | False | 2→2 | [0, 1, 2] |
| refs/cube/Q82-1.csv | False | False | 11→11 | [0, 2, 3] |
| refs/cube/Q83-1.csv | True | True | 1→3 | [0, 1, 2] |
| refs/cube/Q84-1.csv | False | True | 3→3 | [0, 1] |
| refs/cube/Q84-2.csv | False | True | 3→3 | [0, 1] |
| refs/cube/Q85-1.csv | False | True | 97→97 | [0, 1, 3, 4, 5] |
| refs/cube/Q86-1.csv | False | False | 31→31 | [0, 1, 2] |
| refs/cube/Q86-3.csv | False | False | 31→31 | [0, 1, 2] |
| refs/cube/Q87-1.csv | False | True | 20→20 | [0, 2, 3, 4, 5] |
| refs/cube/Q88-1.csv | True | True | 26→26 | [0, 2, 3] |
| refs/cube/Q89-1.csv | False | False | 3→3 | [0, 2, 3] |
| refs/cube/Q90-1.csv | True | True | 9→27 | [0, 1, 2, 3, 4] |
| refs/cube/Q91-1.csv | False | False | 1→1 | [0, 1] |
| refs/cube/Q91-2.csv | False | False | 1→1 | [0, 1] |
| refs/cube/Q92-1.csv | False | True | 12→12 | [0, 4] |
| refs/cube/Q93-1.csv | False | False | 1→1 | [0, 1, 2] |
| refs/cube/Q94-1.csv | False | False | 99→99 | [0] |
| refs/cube/Q95-1.csv | True | True | 9→9 | [0, 1, 2, 3, 4] |
| refs/cube/Q96-1.csv | False | False | 2→2 | [0, 1, 3] |
| refs/cube/Q97-1.csv | True | True | 15→15 | [0, 1, 2, 3, 4, 5, 6] |
| refs/cube/Q97-2.csv | True | True | 15→15 | [0, 1, 2, 3, 4, 5, 6] |
| refs/cube/Q98-1.csv | True | True | 9→9 | [0, 4] |
| refs/cube/Q98-2.csv | True | True | 27→27 | [0, 1, 5] |
| refs/cube/Q99-1.csv | False | False | 9→9 | [0, 3, 4] |
| refs/cube/Q100-1.csv | True | True | 108→108 | [1, 2, 4] |
| refs/new/Q101-1.csv | False | False | 1→1 | [0] |
| refs/new/Q102-1.csv | False | False | 9→9 | [0, 1] |
| refs/new/Q103-1.csv | True | True | 1→1 | [0, 1, 2, 3] |
| refs/new/Q104-1.csv | True | True | 1→1 | [0, 1, 2, 3, 4] |
| refs/new/Q105-1.csv | False | False | 1→1 | [0] |
| refs/new/Q106-1.csv | True | True | 1→1 | [0, 1] |
| refs/new/Q107-1.csv | True | True | 1→1 | [0, 1, 2] |
| refs/new/Q108-1.csv | False | False | 29→29 | [0, 1, 2] |
| refs/new/Q109-1.csv | True | True | 4→4 | [0, 1, 2] |
| refs/new/Q110-1.csv | True | True | 1→2 | [0, 1, 2, 3] |
| refs/new/Q111-1.csv | True | True | 306→306 | [0, 1, 2, 3, 4, 5] |
| refs/new/Q112-1.csv | True | True | 262→262 | [0, 1, 2, 3] |
| refs/new/Q113-1.csv | False | False | 33→33 | [0, 1, 2, 3] |
| refs/new/Q114-1.csv | False | False | 6→6 | [0, 1] |
| refs/new/Q115-1.csv | False | False | 9→9 | [0, 1, 2] |
| refs/new/Q116-1.csv | True | True | 4→4 | [0, 1, 2, 3] |
| refs/new/Q117-1.csv | True | True | 3→3 | [1, 2, 3, 4, 5, 6, 7, 8, 9] |
| refs/new/Q118-1.csv | False | True | 1→1 | [0, 1, 2] |
| refs/new/Q119-1.csv | False | False | 310→310 | [1, 3, 5] |
| refs/new/Q120-1.csv | False | False | 6→6 | [0, 1, 2, 3] |
| refs/new/Q121-1.csv | False | False | 9→9 | [0, 1, 2] |
| refs/new/Q121-2.csv | False | False | 9→9 | [0, 1, 2] |
| refs/new/Q122-1.csv | False | True | 17→17 | [1, 3, 4, 5, 6] |

## 标识列与名次列（0起）

| 参考 | identifier_columns | rank_columns |
|---|---|---|
| refs/cube/Q07-1.csv | [] | [2] |
| refs/cube/Q13-1.csv | [0] | [] |
| refs/cube/Q20-2.csv | [0] | [] |
| refs/cube/Q21-1.csv | [0] | [] |
| refs/cube/Q22-1.csv | [0] | [5] |
| refs/cube/Q27-1.csv | [] | [4] |
| refs/cube/Q33-1.csv | [0, 1] | [5] |
| refs/cube/Q34-1.csv | [4] | [] |
| refs/cube/Q39-1.csv | [0] | [] |
| refs/cube/Q39-2.csv | [0] | [] |
| refs/cube/Q45-1.csv | [] | [4] |
| refs/cube/Q49-2.csv | [0] | [] |
| refs/cube/Q65-2.csv | [3] | [] |
| refs/cube/Q67-1.csv | [] | [3] |
| refs/cube/Q73-1.csv | [] | [4] |
| refs/cube/Q74-1.csv | [4] | [6] |
| refs/cube/Q75-1.csv | [5] | [] |
| refs/cube/Q78-1.csv | [] | [2] |
| refs/cube/Q79-1.csv | [] | [4] |
| refs/cube/Q85-1.csv | [] | [5] |
| refs/cube/Q87-1.csv | [4] | [5] |
| refs/cube/Q88-1.csv | [2] | [3] |
| refs/cube/Q92-1.csv | [] | [4] |
| refs/cube/Q97-1.csv | [4] | [6] |
| refs/cube/Q97-2.csv | [0] | [6] |
| refs/cube/Q98-1.csv | [] | [4] |
| refs/cube/Q98-2.csv | [] | [5] |
| refs/cube/Q100-1.csv | [4] | [] |
| refs/new/Q112-1.csv | [0] | [] |
| refs/new/Q117-1.csv | [0] | [8, 9] |
| refs/new/Q119-1.csv | [0, 2] | [5] |
| refs/new/Q122-1.csv | [0, 2] | [6] |

## 六题改写与A/B/C证据

- Q45：按销售坪效从高到低列出各门店。
  - Q69保留单类别退化A；其他题非零/非空，不以单行计算结果本身当常数；六题均不涉及首购/复购或节假日与周末互换，B条两组必测口径不适用。
  - 排序取值及逐参考记录：[{"all_zero_required_numeric": "wrong", "reference": "refs/cube/Q45-1.csv", "rows": 306, "order_key_distinct": {"3": 306}, "empty_candidate": "wrong", "declared_low_discrimination": [], "C_scope": "full ordered list, no new Top-N cutoff; existing internal selection constraints retained"}]
- Q67：仅考虑销量至少 1000 件的产品颜色，按线上实际成交均价从高到低列出各颜色。
  - Q69保留单类别退化A；其他题非零/非空，不以单行计算结果本身当常数；六题均不涉及首购/复购或节假日与周末互换，B条两组必测口径不适用。
  - 排序取值及逐参考记录：[{"all_zero_required_numeric": "wrong", "reference": "refs/cube/Q67-1.csv", "rows": 18, "order_key_distinct": {"1": 18}, "empty_candidate": "wrong", "declared_low_discrimination": [], "C_scope": "full ordered list, no new Top-N cutoff; existing internal selection constraints retained"}]
- Q69：哪个促销类别带来的线上促销营收最高？其平均折扣比例是多少？
  - Q69保留单类别退化A；其他题非零/非空，不以单行计算结果本身当常数；六题均不涉及首购/复购或节假日与周末互换，B条两组必测口径不适用。
  - 排序取值及逐参考记录：[{"all_zero_required_numeric": "wrong", "reference": "refs/cube/Q69-1.csv", "rows": 1, "order_key_distinct": {"1": 1}, "empty_candidate": "wrong", "declared_low_discrimination": ["A"], "C_scope": "full ordered list, no new Top-N cutoff; existing internal selection constraints retained"}]
- Q92：按上季度盈利能力从高到低列出各产品品牌。
  - Q69保留单类别退化A；其他题非零/非空，不以单行计算结果本身当常数；六题均不涉及首购/复购或节假日与周末互换，B条两组必测口径不适用。
  - 排序取值及逐参考记录：[{"all_zero_required_numeric": "wrong", "reference": "refs/cube/Q92-1.csv", "rows": 12, "order_key_distinct": {"3": 12}, "empty_candidate": "wrong", "declared_low_discrimination": [], "C_scope": "full ordered list, no new Top-N cutoff; existing internal selection constraints retained"}]
- Q97：2009 年，按下半年的销售反弹从高到低列出产品，即下半年销售额大幅超过上半年。
  - Q69保留单类别退化A；其他题非零/非空，不以单行计算结果本身当常数；六题均不涉及首购/复购或节假日与周末互换，B条两组必测口径不适用。
  - 排序取值及逐参考记录：[{"all_zero_required_numeric": "wrong", "reference": "refs/cube/Q97-1.csv", "rows": 15, "order_key_distinct": {"3": 15}, "empty_candidate": "wrong", "declared_low_discrimination": [], "C_scope": "full ordered list, no new Top-N cutoff; existing internal selection constraints retained"}, {"all_zero_required_numeric": "wrong", "reference": "refs/cube/Q97-2.csv", "rows": 15, "order_key_distinct": {"4": 15}, "empty_candidate": "wrong", "declared_low_discrimination": [], "C_scope": "full ordered list, no new Top-N cutoff; existing internal selection constraints retained"}]
- Q98：按全年销售对单个季度的依赖程度从高到低列出各产品品类。
  - Q69保留单类别退化A；其他题非零/非空，不以单行计算结果本身当常数；六题均不涉及首购/复购或节假日与周末互换，B条两组必测口径不适用。
  - 排序取值及逐参考记录：[{"all_zero_required_numeric": "wrong", "reference": "refs/cube/Q98-1.csv", "rows": 9, "order_key_distinct": {"1": 9}, "empty_candidate": "wrong", "declared_low_discrimination": [], "C_scope": "full ordered list, no new Top-N cutoff; existing internal selection constraints retained"}, {"all_zero_required_numeric": "wrong", "reference": "refs/cube/Q98-2.csv", "rows": 27, "order_key_distinct": {"1": 3, "2": 27}, "empty_candidate": "wrong", "declared_low_discrimination": [], "C_scope": "full ordered list, no new Top-N cutoff; existing internal selection constraints retained"}]

## 其余同类句式（只列不改）

- Q07：最贵的前10款产品是哪些？；已明示前N：True
- Q73：当前库存与安全库存的差额最大的 10 款产品是哪些？；已明示前N：True
- Q79：2009 年销售目标达成率最高的 10 家门店是哪些？；已明示前N：True

21份含名次的参考分别构造竞赛、稠密、位置编号三种完整答案并全部自匹配通过；分组及筛选总体保持原排名域。排名按全局固定量化计算竞赛排名1、1、3；名次不参与原有选择边界。月分群显示年和月份数字，季度用语义上下文Q1–Q4，不合并跨年组。Q112空集合缺口为0，无分母的比例、无基期变化保留NULL。第八节边界不补相应列。

T05b的PR92已复核6234d29，本轮落实其9份问题及用户裁决，修正后待T05b跟进；旧T06覆盖/低区分度报告保留为eval-v1历史。本报告是新参考与改写的变更证据，不宣称已重新冻结或完成600条/T12重评。
