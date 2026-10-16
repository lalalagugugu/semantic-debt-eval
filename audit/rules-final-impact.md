# 评分规则补齐：600条影响复验

本报告仅题号及汇总，不含题干、SQL或结果行。会话污染复验另存；本次固定全局量化与容差。

执行600条；Q33的6条历史excluded保留（当前题库Q33已完整复算；该题仍为judge，不能凭示例替代开放评分），可比较分母594。执行失败即关闭并重建会话，共43次。

原公开参考＋新分组契约：strict一致521/594；analytical一致487/594；排除有意更宽后的描述性分母为521/583。

历史strict一致521/594（87.7%）、排除11条有意更宽后521/583（89.4%）保留，不覆盖。

reference_only固定旧扁平比较，combined为当前题库参考＋新契约；二者只在确定性题记录。judge参考仅是示例，不能用“与例子不同”代替judge结论。参考修复轴同时包含T04既有修订及本次孤儿修复，不将其全部归为Q74或模型改善。

仅调用未改动评分核心取得判定／原因，不执行未写入本报告的numeric sensitivity投影；大行集该诊断会出现平方级匹配。NULL必要条件早拒绝和判定均与正式score_detailed合成对照一致。每条四轴判定保存在配套JSON。下表逐条列出任何判定变化；historical_clean差异是复执行稳定性轴，不能直接归为新契约。

| 系统 | 题号 | 干净历史 | 本轮旧契约 | 仅契约 | 仅参考 | 联合 |
|---|---|---|---|---|---|---|
| O-R | Q19 | correct | correct | correct | wrong | wrong |
| O-R | Q21 | correct | correct | correct | wrong | wrong |
| O-R | Q61 | correct | correct | correct | wrong | wrong |
| O-R | Q62 | correct | correct | correct | wrong | wrong |
| O-R | Q67 | correct | correct | correct | wrong | wrong |
| O-R | Q71 | correct | correct | correct | wrong | wrong |
| O-R | Q76 | correct | correct | correct | wrong | wrong |
| O-R | Q83 | wrong | wrong | wrong | correct | correct |
| O-R | Q94 | wrong | wrong | wrong | correct | correct |
| O-S | Q10 | wrong | wrong | wrong | correct | correct |
| O-S | Q11 | correct | correct | correct | wrong | wrong |
| O-S | Q19 | wrong | wrong | wrong | correct | correct |
| O-S | Q25 | correct | correct | correct | wrong | wrong |
| O-S | Q28 | wrong | wrong | wrong | correct | correct |
| O-S | Q43 | wrong | wrong | wrong | correct | correct |
| O-S | Q61 | correct | correct | correct | wrong | wrong |
| O-S | Q62 | correct | correct | correct | wrong | wrong |
| O-S | Q67 | correct | correct | correct | wrong | wrong |
| O-S | Q71 | correct | correct | correct | wrong | wrong |
| O-S | Q75 | wrong | wrong | wrong | correct | correct |
| O-S | Q76 | correct | correct | correct | wrong | wrong |
| O-S | Q83 | wrong | wrong | wrong | correct | correct |
| O-S | Q87 | correct | correct | correct | wrong | wrong |
| O-S | Q90 | correct | correct | correct | wrong | wrong |
| S-R | Q13 | correct | correct | correct | wrong | wrong |
| S-R | Q19 | wrong | wrong | wrong | correct | correct |
| S-R | Q20 | correct | correct | correct | wrong | wrong |
| S-R | Q61 | correct | correct | correct | wrong | wrong |
| S-R | Q62 | correct | correct | correct | wrong | wrong |
| S-R | Q67 | correct | correct | correct | wrong | wrong |
| S-R | Q71 | correct | correct | correct | wrong | wrong |
| S-R | Q75 | wrong | wrong | wrong | correct | correct |
| S-R | Q76 | correct | correct | correct | wrong | wrong |
| S-S | Q10 | wrong | wrong | wrong | correct | correct |
| S-S | Q11 | correct | correct | correct | wrong | wrong |
| S-S | Q19 | wrong | wrong | wrong | correct | correct |
| S-S | Q21 | correct | correct | correct | wrong | wrong |
| S-S | Q24 | correct | correct | correct | wrong | wrong |
| S-S | Q25 | correct | correct | correct | wrong | wrong |
| S-S | Q28 | wrong | wrong | wrong | correct | correct |
| S-S | Q34 | correct | correct | correct | wrong | wrong |
| S-S | Q43 | wrong | wrong | wrong | correct | correct |
| S-S | Q61 | correct | correct | correct | wrong | wrong |
| S-S | Q62 | correct | correct | correct | wrong | wrong |
| S-S | Q67 | correct | correct | correct | wrong | wrong |
| S-S | Q71 | correct | correct | correct | wrong | wrong |
| S-S | Q75 | wrong | wrong | wrong | correct | correct |
| S-S | Q76 | correct | correct | correct | wrong | wrong |
| S-S | Q87 | correct | correct | correct | wrong | wrong |
| S-S | Q90 | correct | correct | correct | wrong | wrong |
| S-S | Q99 | correct | correct | correct | wrong | wrong |
| G-R | Q19 | wrong | wrong | wrong | correct | correct |
| G-R | Q61 | correct | correct | correct | wrong | wrong |
| G-R | Q62 | correct | correct | correct | wrong | wrong |
| G-R | Q71 | correct | correct | correct | wrong | wrong |
| G-R | Q74 | wrong | wrong | wrong | wrong | correct |
| G-R | Q75 | wrong | wrong | wrong | correct | correct |
| G-R | Q76 | correct | correct | correct | wrong | wrong |
| G-R | Q83 | wrong | wrong | wrong | correct | correct |
| G-S | Q11 | correct | correct | correct | wrong | wrong |
| G-S | Q19 | wrong | wrong | wrong | correct | correct |
| G-S | Q21 | correct | correct | correct | wrong | wrong |
| G-S | Q25 | wrong | wrong | wrong | correct | correct |
| G-S | Q34 | correct | correct | correct | wrong | wrong |
| G-S | Q43 | wrong | wrong | wrong | correct | correct |
| G-S | Q61 | correct | correct | correct | wrong | wrong |
| G-S | Q62 | correct | correct | correct | wrong | wrong |
| G-S | Q65 | wrong | wrong | wrong | correct | correct |
| G-S | Q71 | correct | correct | correct | wrong | wrong |
| G-S | Q75 | wrong | wrong | wrong | correct | correct |
| G-S | Q76 | correct | correct | correct | wrong | wrong |
| G-S | Q83 | wrong | wrong | wrong | correct | correct |
| G-S | Q87 | correct | correct | correct | wrong | wrong |
| G-S | Q99 | correct | correct | correct | wrong | wrong |

汇总：contract_changed=0；reference_changed=73；combined_changed=74；baseline_reexecution_changed=0

G0已通过的历史事实保留；新的契约／参考影响交用户评估，不能自动撤销或重批G0。第二轮22题已正式落地、全部148份参考已重算。T05b跨引擎核对及Q79独立成员复现仍为冻结前置。

## 与#36当时修订题库的增量比较

原公开参考基线与#36的历史数字均保留。本轮相对#36修订参考的43条均correct→wrong，其中37条行数不同、6条分组覆盖不全，分别对应完整事实域／未分类组恢复；不是仅字符串差异。73／74是相对原公开参考，43是相对#36修订参考，两个比较起点不同，不能相加。联合轴相对原公开参考共74条（49条correct→wrong、25条wrong→correct）。

600条仅涵盖外部100题。原Q33六条历史排除保留；12道其他judge题共72条只留非封闭示例，不把示例与候选不同当judge错误。修订参考的闭集确定性范围为522条。当前参考＋契约在该范围为220 correct、272 wrong、30 exec_error。T02原公开参考范围为594条，251 correct、304 wrong、39 exec_error；两个分母不同，不能直接比较准确率。

| 系统 | 题号 | #36修订参考 | 本轮修订参考 | 原因 |
|---|---|---|---|---|
| O-R | Q21 | correct | wrong | row_count |
| O-R | Q61 | correct | wrong | row_count |
| O-R | Q62 | correct | wrong | row_count |
| O-R | Q67 | correct | wrong | row_count |
| O-R | Q71 | correct | wrong | selection_group_coverage |
| O-R | Q76 | correct | wrong | row_count |
| O-S | Q11 | correct | wrong | row_count |
| O-S | Q61 | correct | wrong | row_count |
| O-S | Q62 | correct | wrong | row_count |
| O-S | Q67 | correct | wrong | row_count |
| O-S | Q71 | correct | wrong | selection_group_coverage |
| O-S | Q76 | correct | wrong | row_count |
| O-S | Q90 | correct | wrong | row_count |
| S-R | Q61 | correct | wrong | row_count |
| S-R | Q62 | correct | wrong | row_count |
| S-R | Q67 | correct | wrong | row_count |
| S-R | Q71 | correct | wrong | selection_group_coverage |
| S-R | Q76 | correct | wrong | row_count |
| S-S | Q11 | correct | wrong | row_count |
| S-S | Q20 | correct | wrong | row_count |
| S-S | Q21 | correct | wrong | row_count |
| S-S | Q24 | correct | wrong | row_count |
| S-S | Q34 | correct | wrong | row_count |
| S-S | Q61 | correct | wrong | row_count |
| S-S | Q62 | correct | wrong | row_count |
| S-S | Q67 | correct | wrong | row_count |
| S-S | Q71 | correct | wrong | selection_group_coverage |
| S-S | Q76 | correct | wrong | row_count |
| S-S | Q90 | correct | wrong | row_count |
| S-S | Q99 | correct | wrong | row_count |
| G-R | Q61 | correct | wrong | row_count |
| G-R | Q62 | correct | wrong | row_count |
| G-R | Q71 | correct | wrong | selection_group_coverage |
| G-R | Q76 | correct | wrong | row_count |
| G-S | Q11 | correct | wrong | row_count |
| G-S | Q20 | correct | wrong | row_count |
| G-S | Q21 | correct | wrong | row_count |
| G-S | Q34 | correct | wrong | row_count |
| G-S | Q61 | correct | wrong | row_count |
| G-S | Q62 | correct | wrong | row_count |
| G-S | Q71 | correct | wrong | selection_group_coverage |
| G-S | Q76 | correct | wrong | row_count |
| G-S | Q99 | correct | wrong | row_count |

配套T05-final-reference-delta.json逐条保留；原题意／参考修订与本轮修复均不归为模型改善。
