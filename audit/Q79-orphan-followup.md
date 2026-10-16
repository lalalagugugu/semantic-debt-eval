# Q79与空产品属性组裁决落实

本文件保留PR #13第一阶段161份参考及600条复验的历史验收。随后按新裁决逐道自查22道新题并改写5题，当前为162份参考；最新题意及独立重算交接见audit/T05-degeneracy-review.md。该改写不涉及外部100题问句或SQL，不以此宣称已复验新的排序契约。

## Q79

当前中文参考ScenarioKey=2重新执行完整排序范围，再按规则top_n和tie_columns量化排序：严格高于第10名0个、第10名同档42个，共42成员。量纲规则SHA256为7413327151dc85b9ff08233a191ce238dfe6722058b0c1fa71c0649facc540db。

新快照绑定当前SQL、参考CSV哈希及完整有效rules版本。冻结先核验快照仍对应当前参考，再比较T05b独立成员多重集；数量由当前参考推导，无42/306硬编码。旧306快照归档audit/reviews/2026-10-16-Q79-published-boundary-306.json，不能用于中文冻结；EN79仍保持外部原始口径。T06卡已完整同步低区分度A/B/C裁决，实际标注等T05b比对完成后执行。

## 43条逐条分类

使用上轮完整600条保存的原始候选及148份参考，逐份删除NULL／空字符串产品属性组后按相同规则核对。36条只有空属性组差别，7条是产品键／明细差别。逐条证据见orphan-group-regressions.json/md。36条中Q76的6条为跨组占比，不适用新替代参考；Q24／Q90／Q99共5条的组内比率已按补充裁决批准。分类事实不等于所有36条都获准恢复。

全122题替代参考盘点在optional-product-group-refs.json。已增加13份：7份独立属性分组，6份组内比率／统计（含Q121两个统计解读）。全部161份参考从头重算并严格复算，validate_t04、validate_t05、validate_rules通过。基准148份题目及manifest不可变归档在audit/reviews/2026-10-16-before-empty-group-refs.json。155份参考的中间600条复验已归档audit/reviews/2026-10-16-orphan-group-impact-pure.*，不充作本轮161份参考的结论。

## 本轮161份参考的完整600条复验

执行600条，失败后重建会话43次，基准复执行判定变化0。原43条退步恢复30条；剩余13条为Q76的6条跨组占比，以及Q20的2条、Q21的3条、Q34的2条产品键／明细差异。恢复的30条均来自新增可接受参考，固定旧148份参考的判定变化0。

分组／嵌套Top-N共有7题：Q22、Q71、Q74、Q85、Q98、Q117、Q119。仅契约轴的600条判定变化仍为0，与#36结论一致。相对于原公开参考，本轮仅参考轴共43条变化，联合轴44条变化；这些轴包含T04既有修订、保行修复及多解，不把全部差异归为本次空组裁决。逐条四轴结果见orphan-group-impact.json/md。

当前确定性题的522条可比较记录：联合轴250 correct、242 wrong、30 exec_error；另有Q33历史excluded 6条及judge示例72条。Q33当前两份SQL参考均已完整复算，不以旧公开参考不可用为由放行未验证题。原公开参考＋新契约strict一致521/594、analytical一致487/594；这些数字与当前题库确定性准确率用途不同。

本轮原始候选保存在外部数据目录，SHA256为b04e2e006e8eb2518142c621a89a6d9cd05ce72d2f8ff92b283d8c10ebc8dff3。JSON同时记录题库、manifest、量纲和评分代码版本。本轮影响审计不执行数值投影诊断，不能代替主仓库评分器性能PR所需的完整ScoreResult逐条对照。

## 可复现命令与冻结前置

设置SEMDEBT_MAIN_DIR、SEMDEBT_EVAL_DIR、SEMDEBT_DATA_DIR后，在题库目录串行执行：

```sh
uv run --locked python scripts/build_refs.py --refresh-rules
uv run --locked python scripts/build_refs.py --check
uv run --locked python scripts/validate_rules.py --write-review
uv run --locked python scripts/validate_t04.py
uv run --locked python scripts/validate_t05.py
uv run --locked python scripts/snapshot_q79_boundary.py --check
uv run --locked python scripts/check_rules_impact.py \
  --clean-baseline "$SEMDEBT_DATA_DIR/rules-backfill/20261016T035612Z/rebased-official.json" \
  --previous-bank audit/reviews/2026-10-16-before-empty-group-refs.json \
  --previous-impact audit/rules-final-impact.json \
  --output audit/orphan-group-impact.json --report audit/orphan-group-impact.md
```

重跑须为影响报告选新路径，保留此前轮次。13份新增参考仍待T05b独立pandas核对；Q79须提供独立成员集合，运行snapshot_q79_boundary.py的--freeze-check及--independent-snapshot。未提供独立文件时门禁已实测拒绝放行；合成对照不能充作跨厂商证据。T06只更新任务卡，不提前标注或打eval-v1。
