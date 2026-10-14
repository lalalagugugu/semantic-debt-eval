# T03 数据一致性校验；审计裁决落地

- 状态：未开始
- 负责：Codex
- 模式：题库（`cd ~/semdebt/semantic-debt-eval && codex "执行任务卡 T03"`）
- 依赖：T01（数据已导入，Parquet 已导出）、T01a（外部基准文件已在 `vendor/cube/`）
- 预算：0

## 第一步：数据一致性校验（交 G0）

1. 用主仓库的 `data/build_chdb_copy.py` 从 Parquet 重建一份 chDB 到 `$SEMDEBT_DATA_DIR/chdb-eval`（库名 `retail`）。
2. 逐题执行外部基准的参考 SQL，与其公布的参考结果对比行数和数值（容差 0.5%）。已知情况：有一题在对方服务器上超时（本地不设 30 秒限制，应能跑出），有两题对方的参考结果为 0 行。
3. 输出 `audit/data_check.md`：逐题一致与否；不一致的逐题解释。在主仓库的 `reports/validation/` 只放汇总（一致题数、不一致题号），不放题目内容。
4. 停下，请用户过 G0（与 T02 一起）。

## 第二步：把审计裁决变成可执行的题目文件和参考结果

1. 建本仓库的 uv 环境（chdb、pandas、pyyaml 等）。
2. `questions/schema.json`：题目文件的结构。至少包含：`id`、`source`（cube / new）、`text_en`、`text_zh`（T04 填）、`type`（指标分析 / 维度查找 / 统计 / 开放式）、`refs`（列表，每项含 `interpretation`、`sql`、`result_path`）、`scoring`（`deterministic` 或 `judge`）、`scoring_notes`、`labels`（T04 填）、`split`（T06 填）。
3. `questions/cube_100.yaml`：外部基准 100 题全部转入，按 `audit/audit_decisions.yaml` 处理：
   - `fix_reference`、`rewrite`：写新的参考 SQL，算出结果。
   - `accepted_interpretations`：每个解读一份参考 SQL 和结果；`not_accepted` 写进 `scoring_notes`。
   - `judge_with_interpretations`、`open_ended_repair`：`scoring: judge`，把解读清单写进 `scoring_notes` 供裁判使用。
   - `scoring_rule`：在 `scoring_notes` 写明规则（完整结果集、边界并列）。
   - 其余题目：原参考 SQL 与结果直接转入。
4. `refs/`：所有参考结果（Parquet 或 CSV），以及 `scripts/build_refs.py` 一条命令重算全部参考结果。
5. `audit/T03-report.md`：逐题说明做了什么；Q49 原参考为何返回 0 行；Q10 三个解读的结果是否相同；Q13 的 StoreName 是否唯一；列出所有新写或改过的参考答案（交 T05b 独立重算）。

## 验收

- 第一步：一致或已逐题解释。
- 第二步：`scripts/build_refs.py` 在干净环境下重算，结果与提交的一致；每道改动过的题都在报告里有一行说明。

## 用户确认

- [ ] G0（第一步，与 T02 一起）。
- [ ] Q43 是否列为可接受解读（见 `audit_decisions.yaml` 的 `pending_user_decision`）。
- [ ] 审阅报告。

## 不能做

- 不得读取主仓库 `semantic/` 下除 `conventions.md` 以外的文件。
- 不要打开 `$SEMDEBT_DATA_DIR/chdb`（那份给 Claude Code 用）。

## T02 裁决转交（2026-10-14）

依据主仓库 `decisions/2026-10-14-scorer-contract-and-acceptance.md` 第六节：仅跟进 G-R Q30，查明公开窗口结果与本地重执行的根因，记录于 `audit/data_check.md`。其余六条 Q14 已解释为公开工件抽样/截断差异，不再作为数据库漂移追查；本卡原有逐题数据一致性校验仍按计划执行。

## 记录（完成后填写）

- 产出：
- 偏离与理由：
- 工时：
