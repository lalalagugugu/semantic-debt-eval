# T05b 参考答案独立重算（pandas）

- 状态：未开始
- 负责：Claude Code（必须与写 SQL 参考答案的 Codex 不同家）
- 模式：题库 clone，**只能在 G1（主仓库 tag `semantic-v1`）之后**（`~/semdebt/semantic-debt/scripts/start-card.sh T05b`）
- 依赖：G1、T05
- 预算：0

## 目标

不看 Codex 写的 SQL，只看问句、可接受解读和约定清单，用 pandas 从 Parquet 独立算出参考答案，与 SQL 版本逐一对比。参考答案错了，后面所有单元的分数都会错，所以这一步要由另一家来做。

## 范围

1. 我们新写或改过的全部参考答案：T05 的新题；T03 报告里列出的修参考答案、改写、可接受解读的各个解读。
2. 外部基准原样保留的题中，按固定随机种子抽 10 道做抽查。

## 做法

1. 对每道题，先只读 `questions/` 里的问句、`scoring_notes` 和可接受解读、主仓库的 `semantic/conventions.md`，**不要打开 `sql` 字段和 `refs/` 下的结果**。
2. 用 pandas 从 `$SEMDEBT_DATA_DIR/parquet/` 计算，脚本放 `scripts/recheck_pandas.py`，一条命令重算。
3. 算完后再与 `refs/` 对比（0.5% 容差，规则同评分器）。

## 交付物

- `scripts/recheck_pandas.py` 及其输出。
- `audit/T05b-recheck.md`：逐题一致与否；不一致的题列出两边的理解差异，交用户裁决。裁决后由 Codex 改参考答案（T06 之前）。

## 验收

- 全部一致或已裁决、已修正。

## 不能做

- 不得修改 `questions/` 和 `refs/`（那是 Codex 的）；只报告差异。
- 不得用子 agent 或 Codex 代替本卡。

## 并列组确定性复核（2026-10-14 用户裁决）

依据主仓库 `decisions/2026-10-14-scorer-contract-and-acceptance.md` 第三节：独立 pandas 重算时，使用题目记录的确定性并列判据并记录运行条件，核对完整边界组的成员集合，不能只核对第 N 名数值或行数。无法复现的题逐题报告，交 T06 在冻结前解决；本转交不要求提前执行本卡。

## 记录（完成后填写）

- 产出：
- 偏离与理由：
- 工时：
