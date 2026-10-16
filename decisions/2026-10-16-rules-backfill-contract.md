# 2026-10-16 rules全量补齐与逐参考覆盖

授权：用户在本聊天批准逐参考rules覆盖题级rules，缺省沿用；重申主仓库BOARD第3项的分组/嵌套选择批准及四项条件。harness读取和透传由Claude Code跟进。

## 本轮边界

- questions/cube_100.yaml全部100题持久化rules；new.yaml现行22题保留显式声明。现行new.yaml仍为第一轮工件，不能据此声称已接受的第二轮新题完成。
- 有效规则优先取完整ref.rules；没有ref.rules时取题级rules，不逐字段合并。每份参考在manifest保存展开后的完整rules、ordered、value_kinds、value_types与选择域核查。不同解读的列数、单位或类型不强行统一。
- ordered逐参考固化：主仓库ORDERED_QUESTION_IDS已裁决元数据与最终外层ORDER BY同时成立才为true。分组选择可以ordered=false，不能因窗口排序或后处理的物理行序改成true。
- 外部量纲由固定infer_value_kind及COUNT输出别名规则推断，逐题逐参考列在audit/rules-backfill-review.md供用户过目；新题声明不被推断覆盖，不一致保留告警。types来自实际查询返回元数据。
- 正常构建只校验持久化规则。显式build_refs.py --refresh-rules才刷新外部量纲与返回类型；声明的新题不会自动改单位。

## 通用选择契约

评分器接口与selection v1的权威说明在主仓库decisions/2026-10-16-reference-rules-and-selection.md：显式stage的parent、where、group_columns、object_columns、order_by、n及全局output_order。评分器不从SQL、题号或列名推断。父选择约束后续分组，独立根步骤分别满足；严格前缀不能遗漏，完整边界任选但不得漏组、重复对象或交N+k。

全局量化仍使用harness/value_units.py：Decimal十进制字符串、ROUND_HALF_EVEN；金额2位、百分比先除100再6位、比率/其余数值6位。结果比较容差不得参与边界选择。

实施前已报告7/122：Q22/Q71/Q74/Q85/Q98及新版Q117/Q119；外部5题涉及30/600条候选，30不是翻转数。本轮先将外部5题声明和完整边界落地；新版两题的正式SQL及声明由第二轮改写完成后接入同一通用契约，不套用第一轮参考。

Q74遵守先前批准的修复：完整FactSales分母、缺名保ProductKey、完整量化边界与孤儿披露。Q87/Q97等另一聊天的数据质量修复保留；参考修复不能计为纯评分契约变化。此类修复及历史公开原题的差异须T19披露。

## 复验与冻结

会话污染复验与本次规则影响复验分别记录。会话污染复验固定公开参考与原规则，600条与历史判定逐条比较；分组契约复验在同一批公开候选上分别记录旧契约、仅契约、仅参考修订和联合效果，judge示例不当封闭答案集。

所有新改参考仍是provisional；T05b必须由Claude Code用pandas从题意独立实现并核对完整边界和对象身份，不镜像SQL连接、不导入Codex选择器冒充独立计算。第二轮新题未落地、数据质量未决和Q79历史成员证据缺口均不能因本次元数据补齐自动过关。eval-v1不在本轮打tag。
