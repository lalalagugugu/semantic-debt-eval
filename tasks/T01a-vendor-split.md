# T01a 引入外部基准文件，分到两个仓库

- 状态：已完成（PR 待合并）
- 负责：Codex
- 模式：在两个仓库的上一级 `~/semdebt` 启动 Codex（`~/semdebt/semantic-debt/scripts/start-card.sh T01a` 会准备好下面用到的三个目录并打印启动命令）
- 依赖：T00
- 预算：0

## 目标

把外部基准仓库 `cubedevinc/semantic-layer-benchmark`（MIT 许可）的文件分到正确的仓库：写语义层的 agent 只能拿到建表语句，其余都放进题库。

## 做法

1. 外部基准已由脚本克隆到 `~/semdebt/_vendor/semantic-layer-benchmark`（两个仓库之外）。记下它的提交号。
2. **主仓库**：在脚本建好的 `~/semdebt/cards/T01a-main`（分支 `T01a-vendor-ddl`）里只放入：
   - `vendor/cube/retail_schema.sql`（来自 `fixtures/retail_schema.sql`）
   - `vendor/cube/LICENSE`
   - `vendor/cube/README.md`：来源、提交号、许可、「本目录只放建表语句」
   推送并开 PR。
3. **题库仓库** `~/semdebt/semantic-debt-eval`（分支 `T01a-work`）：放入 `vendor/cube/`：题目与参考 SQL 文件、语义文档、`published-runs/`、`REPORT.md`、`README.md`、`LICENSE`，原样保存，并在 `vendor/cube/README.md` 写明提交号。推送并开 PR。
4. 删除 `~/semdebt/_vendor/`。

## 验收

- 主仓库的 PR 只改动 `vendor/cube/` 下这三个文件。
- 题库仓库里能找到 100 道题、600 条公开候选 SQL 及其判定。
- 临时目录已删除。

## 不能做

- 不要把题目、参考 SQL、语义文档、运行结果放进主仓库，也不要在主仓库的提交信息里引用它们的内容。
- 不要读取主仓库 `semantic/` 下除 `conventions.md` 以外的文件；工作区是整个 `~/semdebt`，但只动上面说的三个目录。

## 记录（完成后填写）

- 外部基准的提交号：`4c37310f9fae65255f6d0015475b430ceea3ab1f`
- 产出：主仓库 PR https://github.com/lalalagugugu/semantic-debt/pull/5；题库 PR https://github.com/lalalagugugu/semantic-debt-eval/pull/1；`vendor/cube/` 保留 100 道题、参考 SQL、语义文档与 600 条公开候选 SQL 及逐题判定。已逐字节核对复制文件；上游 README 原文保留并追加来源记录。临时 `_vendor/` 已在两个 PR 创建后删除。
- 偏离与理由：用户于 2026-10-14 裁决：上游该提交没有 LICENSE，不补写 MIT 全文或代为署名，两个仓库各新增 NOTICE，逐字保留许可原话 `MIT.`；主仓库实际为三个 vendor 文件（DDL、README、NOTICE），并允许同一 PR 仅更新 BOARD 中 T01a 状态格。
- 工时：约 10 分钟执行时间（不含等待用户裁决）。
