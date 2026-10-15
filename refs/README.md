# 参考结果

这些 CSV 是题目查询的派生参考结果，不是原始数据。所有结果仍为暂定，新增或修改的答案必须在 G1 后由 Claude Code 在 T05b 使用 pandas 独立重算。

```bash
uv sync --locked
uv run --locked python scripts/build_refs.py
uv run --locked python scripts/build_refs.py --check
```

运行前设置 `SEMDEBT_MAIN_DIR` 与 `SEMDEBT_DATA_DIR`。只使用 `$SEMDEBT_DATA_DIR/chdb-eval`，不要同时打开该目录。主仓库只读取 `harness/value_units.py` 的全局量纲/并列规则，不读取语义层。

CSV 使用 UTF-8、逗号分隔，第一行为列名，SQL NULL 编码为 `\N`，非有限浮点按引擎输出保存为 `inf`/`-inf`/`nan`。列类型、量纲和 SQL/文件哈希见 `MANIFEST.json`。结果按行集规范化存储；需要的输出排序从题干和参考 SQL 判断，不能由 CSV 物理顺序推断。

固定单线程、不设参考计算超时。单层 Top-N 保存按全局量化键选取的完整边界；Q85 的两路 Top/Bottom 原 SQL 保留，冻结前仍须在 T06 处理。Q33 的 89 秒是参考计算耗时，不能据此替 T11 决定模型查询超时。

英文锚点始终使用 `vendor/cube/` 的原题和原参考，不能使用这里经过审计修订的中文主题集参考。

## T04批准的确定性参考后处理

题目ref可显式声明`postprocess`。仅Q74（`store_top3`）、Q84（`abc_groups`）、Q100（`power_customers`）使用；此时`sql`返回完整聚合域，而非最终作答行集。`scripts/build_refs.py`随后调用共享Decimal量化规则计算分组边界、ABC分类或精确线性插值分位。CSV才是最终比较结果；不能把原始SQL域直接传给评分器。清单记录后处理名、输入行数、阈值/分组信息及结果哈希。

这是为了执行用户已批准的跨引擎确定性规则，不在SQL里使用引擎默认round。T05b须用pandas从原始表独立实现规则，不能导入本构建器作为独立核对。

Q40已按用户方案A及乘法公式替换历史0参考：仅31天同日汇率覆盖的部分金额，必须披露1065天缺失，不代表全期间总额。评分同时核验金额与覆盖声明；详见`audit/T04-closeout.md`。全部新改参考仍须T05b独立重算。
