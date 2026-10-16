> 2026-10-16更正：按主仓库Q79裁决第四节，当前中文参考的冻结快照已改为ScenarioKey=2的42成员（0严格前缀＋42并列）。306是旧ScenarioKey=1的全体并列，仅作EN79／历史记录。门禁从当前有效参考推导数量，核对完整成员多重集及版本，不再硬编码306。下文此前306表述保留为历史，现行修正见audit/Q79-orphan-followup.md。

# Q79 成员复现性核对（2026-10-16）

## 后续用户裁决：现行冻结门槛

主仓库decisions/2026-10-16-q79-release-and-anchor-refs.md第一节已批准以跨厂商复现代替历史追溯。当前306个完整公开参考边界成员已重新计算，保存于audit/Q79-boundary-members.json，附量纲规则SHA256。T05b独立pandas计算的量化成员多重集合一致即放行，不比较跨引擎原始行哈希；缺独立证据或成员不一致仍阻止冻结。检查命令及本轮状态见audit/T05-finalization.md。下文历史证据缺口保留，不再把找回历史行快照作为前置条件。

会话污染修复重跑600条后，判定变化0条。用户确认G0无需重新确认；本记录只处理Q79的eval-v1冻结条件。

## 先核对规则版本

核对产物：2026-10-15的 `/tmp/t02-integer-count-check.json` 与2026-10-16的 `/tmp/t11-clean-session.json`。两份产物均只有边界行数/哈希，没有 `unit_policy_sha256`，也没有保存306行原始快照，不能把缺失版本填成当时已经记录。

按10月15日对应主仓库提交 `e6f0ef7` 及本次所用源码追溯：

| 项目 | 10月15日源码 | 本次源码 |
|---|---|---|
| `harness/value_units.py` SHA256 | `7413327151dc85b9ff08233a191ce238dfe6722058b0c1fa71c0649facc540db` | 相同 |
| Q79量纲向量 | `other, amount, amount, percentage` | 相同 |
| 量化规则 | 金额2位；百分比除100后6位；ROUND_HALF_EVEN | 相同 |
| 原始行编码 | UTF-8 JSON、ensure_ascii=False、紧凑分隔符 | 相同 |

没有证据支持量纲识别、量化精度或编码规则在两次运行间变化。边界实现版本以后使用校验脚本源码SHA256标识；本次更改只增加会话隔离和版本记录，不改边界选取算法。

## 再比较成员，而不是用哈希判定成员是否变化

原运行的Q79边界都为306行；其原始行编码哈希分别为 `d854…` 与 `50ab…`。它们缺少原始快照，无法直接对两次历史运行的成员集合做差集。

原 `chdb-eval` 正被另一个题库进程占用，因此使用主仓库已有 `data/build_chdb_copy.py` 从同一份Parquet重建独立副本：25表、34,326,191行。在该副本上，分别用旧版本和新版本校验代码执行Q79，每次独立建Session，每个版本内部仍做3次重算检查。实际比较使用逐单元量化后的完整行多重集合，并另比较StoreName成员多重集合，均保留重复次数。

| 比较项 | 旧代码重建 | 新代码重建 | 直接集合比较 |
|---|---:|---:|---|
| 完整边界行数 | 306 | 306 | 相同 |
| 唯一StoreName成员 | 306 | 306 | 相同 |
| 量化后的完整行 | 306 | 306 | 新增0、缺失0 |
| 恢复出对应历史快照 | 否 | 否 | 历史比较证据仍缺失 |

**结论：同一重建数据上旧、新代码的成员集合相同；尚不能将此写成“两次历史运行成员集合相同”。** 无法从这次核对定位历史原始行编码差异的根因，也不能据此断言成员曾经改变。

306行来自外部原始基准SQL。题库审定后Q79参考SQL已改场景，当前参考CSV为42行；它不是这两次306行历史运行的快照，不能拿它替代历史集合比较。

## eval-v1 条件

- 将“跨会话哈希一致”更正为：原始行编码哈希仅用于运行内重复检查，跨会话比较完整量化成员集合。
- 后续每个边界哈希记录 `unit_policy_sha256`、`boundary_policy_sha256`、`serialization_version`；原始行快照保存在仓库之外。
- 本次脚本返回 `historical_member_comparison=unavailable`、`eval_v1_top_n_gate=blocked_pending_historical_members`，没有把重建一致当成历史一致，也没有声称已发现成员不同。
- Q79带Top-N并列进入eval-v1前，仍须补齐可核对的成员证据，并经T05b独立核对审定后的参考；若成员集合不同，不得带着该Top-N并列冻结。该限制不影响G0。

## 复现

先设置指向已合并本次改动源码的 `SEMDEBT_MAIN_DIR`、`SEMDEBT_EVAL_DIR` 以及原Parquet所在的 `SEMDEBT_DATA_DIR`。以下命令不会打开其他进程正在用的数据库：

```bash
q79_tmp="$(mktemp -d)"
uv run --project "$SEMDEBT_EVAL_DIR" python "$SEMDEBT_MAIN_DIR/data/build_chdb_copy.py" "$q79_tmp/data/chdb-eval"
SEMDEBT_DATA_DIR="$q79_tmp/data" uv run --project "$SEMDEBT_EVAL_DIR" python "$SEMDEBT_EVAL_DIR/scripts/check_q79_membership.py" \
  --old-results /tmp/t02-integer-count-check.json \
  --new-results /tmp/t11-clean-session.json \
  --old-main-ref e6f0ef7 \
  --output-dir "$q79_tmp/evidence"
```

两份历史JSON只读，脚本不修改它们；重建的原始行快照与 `comparison.json` 写入新建的输出目录。若找到10月15日原始行快照，可加 `--old-snapshot`；脚本会先验证其确实对应原记录，再进行成员差集比较。没有确切恢复两个历史快照时不会给出历史一致或冻结放行结论。

## 同批会话修复验证

- 评分校验：600条、43次Session重置（39条exec_error及4条排除评分的Q33失败），逐条判定变化0；117个原分支测试通过。
- `build_refs.py --check`：122题、137份参考结果及manifest全部一致；任一SQL失败立即退出，不存在失败后继续复用会话的路径。
- `check_vendor_refs.py`：补上失败后关闭/重建Session及恢复设置；100条复核为87 matched、12 mismatch、1 published_unavailable_local_success，本地执行失败0次。
- PR分支补充规则版本后，评分器与校验脚本相关77个测试通过。
