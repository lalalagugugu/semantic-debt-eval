# eval-v1.3 五题参考变更与独立复算交接

依据：用户2026-10-28指令及主仓库 decisions/2026-10-28-reference-rulings-five-questions.md 第一节的五行裁定（PR #198）。本分支只实施题库修改，不修改评分器和主仓库，不移动 eval-v1.2。

| 题号 | 参考 | 变更与依据 |
|---|---|---|
| Q71 | Q71-2（新增）；保留Q71-1 | 第一节Q71：未归属组可列可不列，两份均接受 |
| Q65 | Q65-3（新增）；保留Q65-2 | 第一节Q65：新增经理级汇总后筛500万美元，与逐门店解读并存；经理按键区分 |
| Q82 | Q82-2（新增）；保留Q82-1 | 第一节Q82：仅断开18→1，原始成环关系亦接受；截止2009-12-31，天数÷365.25，不接受整年差 |
| Q30 | Q30-1（替换） | 第一节Q30：含当日及前6天，先算完整窗口，再筛12月；旧截断窗口不再接受 |
| Q117 | Q117-1（必答规则修改） | 第一节Q117：仅去除c7 category_decline_pct的必答；其余必答列1、2、3、4、5、6、8、9不变，结果CSV不需变化 |

Q65的原文与中文逐字对照、来源及核查结论见同目录 2026-10-28-q65-source-check.md，不在公开回复复制留出题原文。

SQL 位于 questions/cube_100.yaml 对应 refs[].sql；结果在 refs/cube/；Q117规则位于 questions/new.yaml。refs/PRESENTATION.json 同步Q117覆盖规则，防止以后刷新恢复取消的必答列。CSV/SQL哈希与类型由 refs/MANIFEST.json 记录。

## 跨厂商复算要求

由用户交给现有T14卡目录的Claude Code普通模式会话，遵守T05b：先只读题面、可接受解读、口径约定，不看SQL与参考CSV；从Parquet用pandas独立计算，完成后再比较。本会话只写SQL和生成SQL结果，不写pandas核对、不以SQL重跑充当独立复核。

新改数值参考为Q71-2、Q65-3、Q82-2、Q30-1；既有另一解读可同时回归核对。Q117只核验必答列集合，其余规则与结果不变。独立脚本和报告不得复制题库内容到主仓库；主仓库记录限题号、汇总数字。独立复算输出按主仓库会话的允许路径管理。

尚未通过跨厂商复算，不打eval-v1.3 tag。通过后记录核对提交及报告，再打新tag并开PR，由用户合并。当前状态为待独立复算，不能作为已定稿版本使用。

## SQL产出与结构检查

SQL构建产出：Q30-1 31行；Q65-2 303行（保留）、Q65-3 260行；Q71-1 8行（保留）、Q71-2 9行；Q82-1 11行（保留）、Q82-2 11行；Q117-1 3行（CSV保留）。预期行数取自SQL产出，不是pandas独立结论。

生成命令（环境变量由调用环境提供）：

```bash
uv run --offline --no-sync python scripts/build_refs.py --question Q30 --question Q65 --question Q71 --question Q82 --question Q117
```

构建器原来不允许定向新增参考；本次保留运行时/量化版本保护，允许选中题增加参考，仍禁止删除或未选中题新增参考。展示配置变动时，以HEAD中的旧配置校验清单哈希，并要求未选中参考配置完全不变。

全量SQL构建尝试在无关Q119因“selection object has inconsistent ranking values”失败，未写盘；不修改Q119。随后使用上述定向构建成功。重算既有参考时Q65-2、Q117-1出现浮点字符串差异；按本次范围保留其旧CSV及相应清单字段（Q117仅更新rules），没有将重算噪声混入补丁。新数值参考保存本轮SQL产出，不声称跨引擎数值已核对。

已执行 `uv run --offline --no-sync python scripts/validate_rules.py --write-review` 更新现有审阅表，再执行 `uv run --offline --no-sync python scripts/validate_rules.py`：122题140份参考rules、类型、SQL/CSV哈希及审阅表一致。没有运行pandas独立复算，没有重评模型结果，没有打tag。

## 2026-10-28：跨厂商独立核对通过

用户在本会话转交Claude Code协调会话（主仓库semantic-debt）的独立核对结论：通过。以下为收到的验收证据，本Codex会话未执行或代做pandas独立复算。

- 核对的题库提交：`4846d8ff34436223319ee7cc557d677435bebfb5`。核对方以git archive导出refs/，另读questions/new.yaml与refs/PRESENTATION.json的改动。
- 独立性：执行方只依据题面口径与主仓库decisions/2026-10-28-reference-rulings-five-questions.md独立实现；算完后才读结果CSV，未读SQL与计算脚本。
- Q71-2：9/9行一致，未归属组NULL行金额一致。
- Q65-3：260/260行一致，经理集合与合计一致。
- Q82-2：11/11行一致，直属人数与平均年限逐行一致。
- Q30-1：31/31行一致，日销售额与跨月7日均值逐日一致。
- 上述数值相对误差均≤1e-9。
- Q117-1：必答列仅删除c7，其余c1–c6、c8、c9不变；展示配置覆盖为[1,2,3,4,5,6,8,9]；CSV未改动。与裁定一致。
- 独立脚本：`$SEMDEBT_DATA_DIR/recompute_eval_v13_refs.py`。
- 复现命令：`uv run python "$SEMDEBT_DATA_DIR/recompute_eval_v13_refs.py" <仓库外输出目录>`。

用户已授权记录通过证据、打eval-v1.3 tag并开PR，由用户合并。本节取代上文历史的“待独立复算”状态；自核对提交以来仅追加审计文档，参考数据与规则保持核对版本。eval-v1.2保持原指向。
