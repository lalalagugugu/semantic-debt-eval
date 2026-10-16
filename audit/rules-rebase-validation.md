# PR #10／#36 rebase后重新验证（2026-10-16）

## 基线与保留内容

- 题库基线origin/main：ab3b4ce（已合入#8及#9）；重放后的代码提交ceed33a。
- 主仓库基线origin/main：9fd1e6d（已合入#35）；重放后的代码提交5075d95。
- 远端#10在本轮fetch前已有一次等价改写，旧远端头aa21190；本轮先同步该远端历史，再rebase到main。旧本地和旧远端交付树内容相同。
- 两个rebase由Git自动合并完成，没有遗留需手工处理的冲突；完成后逐文件核对。
- #9的scripts/check_vendor_refs.py、scripts/check_q79_membership.py、audit/Q79-membership.md及tasks/T06-split-freeze.md与最新main逐字一致。
- #35的scripts/validate_scorer.py、tests/test_validate_scorer.py及reports/validation/scorer_check.md与最新main逐字一致。
- Q79的历史成员比较unavailable与冻结前blocked_pending_historical_members限制保留，本次验证不替代该证据。

## rebase后实际执行

运行时SEMDEBT_MAIN_DIR和SEMDEBT_EVAL_DIR分别指向本轮rebased工作树，SEMDEBT_DATA_DIR指向原数据目录；数据库命令串行使用chdb-eval。

| 检查 | 本轮结果 |
|---|---|
| uv run --locked --offline python scripts/build_refs.py --check | Verified 137 references for 122 questions；CSV及manifest严格一致 |
| uv run --locked --offline python scripts/validate_rules.py | PASS：122题、137份有效rules／类型／哈希及审阅表 |
| uv run --locked --offline python scripts/validate_t04.py | PASS：100题、113份参考与既有边界fixtures |
| rebased main的test_scorer/test_selection/test_validate_scorer/test_harness | 126 passed、16 skipped；skip项依赖数据库或渲染上下文 |

严格复算中Q101/1及Q102/2两个既有amount/other别名告警保留；声明未被推断覆盖。未使用--refresh-rules，也未更改参考CSV或manifest来通过检查。

复现时令SEMDEBT_MAIN_DIR／SEMDEBT_EVAL_DIR指向对应PR工作树，SEMDEBT_DATA_DIR指向既有数据目录。题库工作树内执行：

```sh
uv run --locked --offline python scripts/build_refs.py --check
uv run --locked --offline python scripts/validate_rules.py
uv run --locked --offline python scripts/validate_t04.py
uv run --locked --offline python "$SEMDEBT_MAIN_DIR/scripts/validate_scorer.py" \
  --output "$SEMDEBT_DATA_DIR/rules-rebase-official.json" \
  --report "$SEMDEBT_DATA_DIR/rules-rebase-official.md"
uv run --locked --offline python scripts/check_rules_impact.py \
  --clean-baseline "$SEMDEBT_DATA_DIR/rules-rebase-official.json" \
  --output "$SEMDEBT_DATA_DIR/rules-rebase-impact.json" \
  --report "$SEMDEBT_DATA_DIR/rules-rebase-impact.md"
```

每次复验应换用新的输出文件名；数据库命令不得并发。上述命令分别对应本轮实际执行的脚本，临时输出名在下节和比较摘要中记录。

## 600条复验

本轮直接重新执行rebased主仓库的scripts/validate_scorer.py，实际完成600条；以(system, question_id)逐条比较rebase前的600条，键集合完全一致，判定变化0条。

- correct251、wrong304、exec_error39、excluded6；Q33的6条仍单列，可比较分母594。
- strict一致521/594（87.7%）；analytical一致487/594；失败后关闭并重建会话43次。
- 同一批结果中exact_counts收紧前后仍只有S-S Q83一条correct→wrong，这是既有计数守卫诊断，不是rebase导致的判定变化。
- 官方复验JSON／报告已归档到$SEMDEBT_DATA_DIR/rules-backfill/20261016T035612Z/rebased-official.json／.md；同目录保存before-rebase-impact.json和before-rebase-contract-outcomes.json比较输入。JSON哈希随最终比较摘要保存。

另串行重新执行scripts/check_rules_impact.py，以本轮官方复验为clean-baseline，覆盖分组契约、逐参考rules及当前参考，实际完成600条。与rebase前audit/rules-impact.json逐条比较，baseline、contract、reference_only、combined及intentional_broader五个字段全部0变化。

- 原公开参考＋新契约仍为correct251、wrong304、exec_error39、excluded6；strict521/594、analytical487/594、排除既定更宽差异后521/583；会话重置43次。
- 同批内部四轴差异仍为仅契约0、仅参考34、联合35、旧契约复执行0。参考轴包含既有T04修订及孤儿修复，35条不是本次rebase新增变化。
- 本轮完整600条四轴记录更新在audit/rules-impact.json；旧记录已归档，并保留在rebase前提交历史中。
- 新旧输入哈希、600键集合校验及各轴判定变化清单保存在audit/rules-rebase-comparison.json；判定变化清单均为空。仓库JSON保留原键序以减小diff，与归档JSON解析后的内容相同，二者分别记录哈希。
- 本轮完整官方输出、影响输出和原始候选行均归档在$SEMDEBT_DATA_DIR/rules-backfill/20261016T035612Z，原始行没有提交入库。

这次通过的是rebase后、原chdb-eval上的重新验证；既有独立Parquet重建诊断与T05b独立pandas核对要求仍保留。

额外的整记录相等断言未通过，按字段核对发现仅O-R Q85的未知标识符别名建议和S-R Q34的超时毫秒数变化，各影响contract_reason及combined_reason；均仍为exec_error。新错误文本完整保留于本轮JSON，比较摘要单列diagnostic_only_changes，不将其计为判定变化。
