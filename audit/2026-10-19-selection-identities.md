# eval-v1.1 selection 身份列扫描与已批准修正

基线：`eval-v1.1`，提交 `938957f4281ddc63ba699bf15d91dcde6b71ddf0`。扫描 122 题、137 份参考；selection 涉及 7 题、8 份参考。不满足「group_columns/object_columns 必须在 required_columns」的共 **4 题、5 份参考**。以下为修正前扫描。用户随后按主仓库 PR #106 批准本报告方案及 Q98 季度必答裁决；本分支已落实元数据修正，目标 eval-v1.2，待 T05b 复核。题面、SQL 与全部 CSV 保持不变。

复现：`uv run python scripts/audit_selection_identities.py --output audit/2026-10-19-selection-identities.json`。有效规则按逐参考整体覆盖题级规则；逐份核对 CSV SHA256。名称只去首尾空格，不忽略大小写；全参考检查键→名称、名称→键两个方向。

| 参考 | 缺失身份列（0 起） | 方案及证据 |
|---|---|---|
| Q74-1 | stage 0 object_columns c4 ProductKey | 提议换必答 c1 ProductName；925 行，130 个键与 130 个名称双向一一对应，无空名称。 |
| Q98-1 | stage 0 object_columns c2 peak_quarter | **待裁决**。9 行、2 个季度、9 个品类名称；季度与必答品类名称不能一一对应，不能直接替换。 |
| Q98-2 | stage 0 object_columns c3 peak_quarter | **待裁决**。27 行、4 个季度、9 个品类名称；8 个品类名称对应多个季度；必答年份也不能表达季度身份。 |
| Q117-1 | stage 0 object_columns c0；stage 1 group_columns c0 StoreKey | 提议两处均换必答 c1 StoreName；3 行，3 个键与 3 个名称双向一一对应，无空名称。 |
| Q119-1 | stage 0 group_columns c0 StoreKey；object_columns c2 ProductKey | 提议分别换必答 c1 StoreName、c3 ProductName；310 行，306 个门店键/名称、69 个产品键/名称均双向一一对应，无空名称。 |

Q22-1、Q71-1、Q85-1 满足要求；其他 129 份参考没有 selection。逐列候选名称的对应关系、冲突数见同名 JSON。

修正前待决事项（已由 PR #106 裁决）：Q98 需要用户指定季度身份的处理：是否将季度输出列改成必答，或调整 selection 的身份表达。两者均涉及契约，尚未选择。其他三题的名称替换也仅为待确认方案；确认后另开题库 PR，进入 eval-v1.2，并交 T05b 复核。届时需同步核对与 selection 相关联的排名元数据。

## 已落实与验证

- Q74-1、Q117-1、Q119-1 按表中方案替换 selection 身份，同时同步 rankings 和 PRESENTATION 的排名身份及分组值。
- Q98-1 required_columns 为 `[0,2,4]`；Q98-2 为 `[0,1,3,5]`。同步 PRESENTATION overrides，避免 refresh-rules 丢失季度必答标注。
- 更新 MANIFEST 有效 rules、选择检查的分组身份和展示配置哈希；原始检查的对象数、严格前缀、完整边界大小不变。
- 修正后重新扫描 122 题、137 份参考，selection 身份漏标为 **0 题、0 份**。见 `2026-10-19-selection-identities-after.json`；逐份变更见 `2026-10-19-selection-identity-changes.json`。
- `scripts/validate_rules.py` 通过全部 137 份 rules、返回类型、SQL 指纹、CSV 哈希与审阅表一致性检查。未执行 SQL；这次没有修改参考结果或参考 SQL。
- 本次未打 eval-v1.2 tag；合并与 T05b 复核由用户协调。
