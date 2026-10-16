# 评分规则补齐：600条影响复验

本报告仅题号及汇总，不含题干、SQL或结果行。会话污染复验另存；本次固定全局量化与容差。

600条执行记录；Q33的6条历史excluded保留（当前题库Q33已完整复算；该题仍为judge，不能凭示例替代开放评分），可比较分母594。候选SQL执行阶段失败即重建会话43次；复用已完整重执行且哈希匹配的缓存=True，本次参考构造阶段重置0次。

原公开参考＋新契约（分组及提供的有序并列键）：strict一致520/594；analytical一致486/594；排除有意更宽后的描述性分母为520/581。

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
| O-S | Q27 | wrong | wrong | correct | wrong | correct |
| O-S | Q28 | wrong | wrong | wrong | correct | correct |
| O-S | Q43 | wrong | wrong | wrong | correct | correct |
| O-S | Q75 | wrong | wrong | wrong | correct | correct |
| O-S | Q76 | correct | correct | correct | wrong | wrong |
| O-S | Q83 | wrong | wrong | wrong | correct | correct |
| O-S | Q87 | correct | correct | correct | wrong | wrong |
| S-R | Q13 | correct | correct | correct | wrong | wrong |
| S-R | Q19 | wrong | wrong | wrong | correct | correct |
| S-R | Q20 | correct | correct | correct | wrong | wrong |
| S-R | Q75 | wrong | wrong | wrong | correct | correct |
| S-R | Q76 | correct | correct | correct | wrong | wrong |
| S-R | Q88 | wrong | wrong | correct | wrong | correct |
| S-S | Q10 | wrong | wrong | wrong | correct | correct |
| S-S | Q19 | wrong | wrong | wrong | correct | correct |
| S-S | Q21 | correct | correct | correct | wrong | wrong |
| S-S | Q25 | correct | correct | correct | wrong | wrong |
| S-S | Q27 | wrong | wrong | correct | wrong | correct |
| S-S | Q28 | wrong | wrong | wrong | correct | correct |
| S-S | Q34 | correct | correct | correct | wrong | wrong |
| S-S | Q43 | wrong | wrong | wrong | correct | correct |
| S-S | Q75 | wrong | wrong | wrong | correct | correct |
| S-S | Q76 | correct | correct | correct | wrong | wrong |
| S-S | Q87 | correct | correct | correct | wrong | wrong |
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

汇总：contract_changed=3；reference_changed=43；combined_changed=47；baseline_reexecution_changed=0

G0已通过的历史事实保留；新的契约／参考影响交用户评估，不能自动撤销或重批G0。第二轮22题已正式落地，当前162份参考已重算。T05b跨引擎核对及Q79独立成员复现仍为冻结前置。

固定旧参考下评分器变化：0；可选空组参考变化：30；原43条恢复：30。此600对照只核对判定，未执行数值敏感性投影；完整score_detailed耗时单独测试。

同一新执行缓存下：有序并列块3条wrong→correct，0条反向；仅参考43条变化包含24条转正／19条转错，联合47条包含28条转正／19条转错。契约与参考交互，不能将3和43相加。原43条correct→wrong队列相对于#36修订参考，其中36条仅差空组，恢复30、剩13；它与参考轴43不是同一集合。固定当前参考、有序块追加的变化3另存JSON的current_reference_ordered_tie_changes。

可选空组参考的30条恢复按新增有序键之前的当前参考计算，避免把排序契约算成参考修复。新22题不在外部600条范围，本报告不代替逐题退化自查或T05b独立重算。

复现采用scripts/check_rules_impact.py的--previous-bank与--previous-impact固定旧148份和旧判定；--order-registry指定audit/ordered-rules-review.json；--candidate-cache及--candidate-cache-report指向主仓完整600条重执行缓存及其报告。两者须成对给出并验证SHA、记录数和逐条键；不提供时脚本重新执行SQL。基准使用会话污染复验的干净报告，旧报告不覆盖。所有SQL串行打开chdb-eval。
