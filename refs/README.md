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
