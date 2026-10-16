# 评分规则补齐：600条影响复验

本报告仅题号及汇总，不含题干、SQL或结果行。会话污染复验另存；本次固定全局量化与容差。

执行600条；Q33的6条历史excluded保留（当前题库Q33已完整复算；该题仍为judge，不能凭示例替代开放评分），可比较分母594。执行失败即关闭并重建会话，共43次。

原公开参考＋新分组契约：strict一致521/594；analytical一致487/594；排除有意更宽后的描述性分母为521/583。

历史strict一致521/594（87.7%）、排除11条有意更宽后521/583（89.4%）保留，不覆盖。

reference_only固定旧扁平比较，combined为当前题库参考＋新契约；二者只在确定性题记录。judge参考仅是示例，不能用“与例子不同”代替judge结论。参考修复轴同时包含T04既有修订及本次孤儿修复，不将其全部归为Q74或模型改善。

调用生产评分核心取得判定／原因，代码版本由scorer_sha256记录，不执行未写入本报告的numeric sensitivity投影；大行集该诊断会出现平方级匹配。NULL必要条件早拒绝和判定均与正式score_detailed合成对照一致。每条四轴判定保存在配套JSON。下表逐条列出任何判定变化；historical_clean差异是复执行稳定性轴，不能直接归为新契约。

| 系统 | 题号 | 干净历史 | 本轮旧契约 | 仅契约 | 仅参考 | 联合 |
|---|---|---|---|---|---|---|
| O-R | Q19 | correct | correct | correct | wrong | wrong |
| O-R | Q21 | correct | correct | correct | wrong | wrong |
| O-R | Q76 | correct | correct | correct | wrong | wrong |
| O-R | Q83 | wrong | wrong | wrong | correct | correct |
| O-R | Q94 | wrong | wrong | wrong | correct | correct |
| O-S | Q10 | wrong | wrong | wrong | correct | correct |
| O-S | Q19 | wrong | wrong | wrong | correct | correct |
| O-S | Q25 | correct | correct | correct | wrong | wrong |
| O-S | Q28 | wrong | wrong | wrong | correct | correct |
| O-S | Q43 | wrong | wrong | wrong | correct | correct |
| O-S | Q75 | wrong | wrong | wrong | correct | correct |
| O-S | Q76 | correct | correct | correct | wrong | wrong |
| O-S | Q83 | wrong | wrong | wrong | correct | correct |
| O-S | Q87 | correct | correct | correct | wrong | wrong |
| O-S | Q90 | correct | correct | correct | wrong | wrong |
| S-R | Q13 | correct | correct | correct | wrong | wrong |
| S-R | Q19 | wrong | wrong | wrong | correct | correct |
| S-R | Q20 | correct | correct | correct | wrong | wrong |
| S-R | Q75 | wrong | wrong | wrong | correct | correct |
| S-R | Q76 | correct | correct | correct | wrong | wrong |
| S-S | Q10 | wrong | wrong | wrong | correct | correct |
| S-S | Q19 | wrong | wrong | wrong | correct | correct |
| S-S | Q21 | correct | correct | correct | wrong | wrong |
| S-S | Q24 | correct | correct | correct | wrong | wrong |
| S-S | Q25 | correct | correct | correct | wrong | wrong |
| S-S | Q28 | wrong | wrong | wrong | correct | correct |
| S-S | Q34 | correct | correct | correct | wrong | wrong |
| S-S | Q43 | wrong | wrong | wrong | correct | correct |
| S-S | Q75 | wrong | wrong | wrong | correct | correct |
| S-S | Q76 | correct | correct | correct | wrong | wrong |
| S-S | Q87 | correct | correct | correct | wrong | wrong |
| S-S | Q90 | correct | correct | correct | wrong | wrong |
| S-S | Q99 | correct | correct | correct | wrong | wrong |
| G-R | Q19 | wrong | wrong | wrong | correct | correct |
| G-R | Q74 | wrong | wrong | wrong | wrong | correct |
| G-R | Q75 | wrong | wrong | wrong | correct | correct |
| G-R | Q76 | correct | correct | correct | wrong | wrong |
| G-R | Q83 | wrong | wrong | wrong | correct | correct |
| G-S | Q19 | wrong | wrong | wrong | correct | correct |
| G-S | Q21 | correct | correct | correct | wrong | wrong |
| G-S | Q25 | wrong | wrong | wrong | correct | correct |
| G-S | Q34 | correct | correct | correct | wrong | wrong |
| G-S | Q43 | wrong | wrong | wrong | correct | correct |
| G-S | Q65 | wrong | wrong | wrong | correct | correct |
| G-S | Q75 | wrong | wrong | wrong | correct | correct |
| G-S | Q76 | correct | correct | correct | wrong | wrong |
| G-S | Q83 | wrong | wrong | wrong | correct | correct |
| G-S | Q87 | correct | correct | correct | wrong | wrong |
| G-S | Q99 | correct | correct | correct | wrong | wrong |

汇总：contract_changed=0；reference_changed=48；combined_changed=49；baseline_reexecution_changed=0

G0已通过的历史事实保留；新的契约／参考影响交用户评估，不能自动撤销或重批G0。第二轮22题已正式落地，当前155份参考已重算。T05b跨引擎核对及Q79独立成员复现仍为冻结前置。

固定旧参考下评分器变化：0；可选空组参考变化：25；原43条恢复：25。此600对照只核对判定，未执行数值敏感性投影；完整score_detailed耗时单独测试。
