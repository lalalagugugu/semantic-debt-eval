# T06 划分、汇总层覆盖标注、冻结

- 状态：未开始
- 负责：Codex
- 模式：题库（`cd ~/semdebt/semantic-debt-eval && codex "执行任务卡 T06"`）
- 依赖：G1（主仓库 `semantic-v1`）、T05b（参考答案已独立核对）
- 预算：0

## 目标

把约 120 道中文题分成调优题和留出题，抽出最小样本，标注每道题「汇总层能否回答」，冻结题集。

## 做法

1. **划分**：按 `q_level` × `persona` × `type` 分层，固定随机种子（写进脚本），对半分成 `tuning` 和 `heldout`，写进每题的 `split`。外部基准题和新题都参与划分。
2. **最小样本**：从 `tuning` 里分层抽 24 道：Q1、Q2、Q3 各 8 道，尽量覆盖不同的复杂度来源；只从指标分析和维度查找题里抽。写进 `questions/pilot.yaml`。
3. **汇总层覆盖**：读主仓库的 `semantic/summary/summary.yaml` 和 `summary.sql`（G1 之后允许），用 `render/build_summary.py` 在 `chdb-eval` 里建出 `ads` 库。对每道题，尝试只用 `ads` 库里的汇总表和维度表写出查询并复现参考答案（任一可接受解读即可）。能复现标 `summary_coverage: covered`，不能标 `not_covered`，并写一句原因（缺粒度、缺指标、缺维度、需要明细）。这一步看得到参考答案，没有关系：它只是事后的分析标签。
4. **`questions/MANIFEST.md`**：总题数；按 split、type、q_level、persona、complexity_source、semantic_dependency、summary_coverage 的计数；主结论题（指标分析 + 维度查找）的数量。
5. 用户确认后打 tag `eval-v1`，并在主仓库的 `decisions/` 记录该 tag 对应的提交号。

## 验收

- 两半在各分层上的题数相差不超过 1。
- 最小样本 24 道全部属于 `tuning`。
- 每道题都有 `summary_coverage`；`MANIFEST.md` 与题目文件一致（脚本校验）。

## 用户确认

- [ ] G2：同意划分、最小样本和覆盖标注，打 tag `eval-v1`。

## 不能做

- 不得修改主仓库的 `semantic/`（已冻结）。

## 冻结前并列组检查（2026-10-14 用户裁决）

依据主仓库 `decisions/2026-10-14-scorer-contract-and-acceptance.md` 第三节：检查所有 Top-N 题已记录运行条件、确定性并列判据，并具有 T05b 对同一完整边界成员集合的独立复核记录。重算不出同一个并列组的题，不得带着 Top-N 并列进入 `eval-v1`。

## 记录（完成后填写）

- 产出：
- 偏离与理由：
- 工时：
