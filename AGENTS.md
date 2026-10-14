# AGENTS.md — semantic-debt-eval（私有题库）

这是实验 `semantic-debt` 的私有题库仓库：题目、参考答案、审计记录和含题目示例的完整设计。它和主仓库是**两个并列的文件夹**（`~/semdebt/semantic-debt-eval` 与 `~/semdebt/semantic-debt`），不是子模块。主仓库的程序通过环境变量 `SEMDEBT_EVAL_DIR` 找到这里。

主仓库的 `AGENTS.md` 全部适用（开工自检、分工、子 agent、硬规则），本文件只补充题库侧的规则。

## 谁在这里工作

- **Codex**：T01a、T03、T04、T05、T06（负责方以主仓库 `tasks/cards.yaml` 为准）。题库卡在本仓库里启动：`cd ~/semdebt/semantic-debt-eval && codex "执行任务卡 Txx"`；T01a 例外，在上一级 `~/semdebt` 启动。
- **Claude Code**：只有 T05b（参考答案独立重算），而且只能在 G1（主仓库 tag `semantic-v1`）之后，在它自己的 clone 里做。G1 之前 Claude Code 不得读取本仓库的任何内容。

## 这里有什么

- `docs/design-v5.md`：完整实验设计（含题目示例）。定稿后的修订以主仓库 `decisions/` 为准。
- `tasks/`：题库侧任务卡 T01a、T03–T06、T05b。
- `audit/`：22 道疑点题的审计记录与用户裁决。
- `vendor/cube/`：外部基准的题目、参考 SQL、语义文档、公开运行结果（MIT 许可，保留署名；T01a 放入）。
- `questions/`：审计、中文化、补题后的题集（T03–T06 产出）。
- `refs/`：每道题每个可接受解读的参考结果。

## 规则

1. 本仓库的任何内容都不得复制进主仓库，也不得出现在主仓库的提交信息、日志或任务卡里。主仓库的日志与报告只能引用题号和汇总数字。
2. G1 之前，写题、改题、标注的 agent 不得读取主仓库 `semantic/` 下除 `conventions.md` 以外的文件。G1 之后，T06 可以读主仓库的 `semantic/summary/`，用来标注「汇总层能否回答」。
3. 题集打 tag `eval-v1` 后冻结。冻结后发现参考答案错误：在 `audit/post-freeze.md` 记录，交用户决定是否发布 `eval-v1.1`，并在报告中说明影响了哪些结果。
4. 参考答案必须能由一条命令重新计算出来。凡是我们新写或改过的参考答案，都要经 Claude Code 在 T05b 用 pandas 独立重算，一致才算定稿。
5. 执行 SQL 用 `$SEMDEBT_DATA_DIR/chdb-eval`（由主仓库 `data/build_chdb_copy.py` 从 Parquet 重建），不要打开 `$SEMDEBT_DATA_DIR/chdb`。
6. 本仓库的 Python 环境用 uv 单独管理（T03 建）。
