> 第六、七节追加：Q14/Q21/Q122现为汇总参考1/306/1行，Q14门槛10万美元，Q122包含原总体订单数；参考总份数仍136。见audit/2026-10-17-summary-rewrites.md。

> 17项缺口已按新裁决落实；本轮执行、四题A/B/C及超50行题单见 audit/2026-10-17-gap-ruling-review.md。旧审计中的133份及待裁决状态仅属历史。

> 当前规则（2026-10-17，题库PR #15待审）：122题136份有效参考。全部行均算交易（含纯退货），空品类保留，新客按[T-89,T]，经理只留姓名；排序值在规范CSV中不提前取整。现行清单为MANIFEST.json，已移除参考不再被评分器加载。旧双解报告只保留作历史，不能据此重新添加已撤销参考。逐份43项审阅、122题面审阅及缺口见audit/2026-10-17-single-policy-review.md和audit/2026-10-17-semantic-gaps.md。
>
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

## T05 新题草稿

`questions/new.yaml`为Q101–Q122；`refs/new/`共24份，另含Q114/Q115端点解读。新题逐题带`rules`：`ordered`、`top_n`、`tie_columns`、`value_kinds`、`value_types`，清单逐参考保存同一规则。所有新题无排序/Top-N要求，`ordered=false`、`top_n=null`；CSV物理行序无判定效力。

量纲只用显式声明；英文词表推断仅作交叉检查。Q101/1与Q102/2的amount/other告警是已解释的别名词表缺口，声明不会被推断覆盖；查询输出类型不符声明则直接报错。运行同一`build_refs.py`命令会覆盖外部100题与新题，`--check`严格验证全部CSV和清单。

新题仍待用户在`audit/T05-review.md`审阅，端点多解、全零参考不自动视为获批。`audit/T05b-handoff.md`只列交接事项，不代表已跨厂商验证。

## 2026-10-16 全量 rules 与分组选择

题级`rules`为必填；每个`ref.rules`整份覆盖题级rules，必须完整；缺省沿用题级。不同参考的量纲向量和返回类型跟随各自列顺序。manifest每份参考保存展开后的完整rules及ordered/types。构建器保留声明的行序，不以物理行序推断排序要求。

外部量纲审阅表见`audit/rules-backfill-review.md`。正常重算验证持久化量纲与返回类型；明确更新外部推断及返回类型时使用`uv run --locked python scripts/build_refs.py --refresh-rules`，新题的显式声明不会被覆盖。刷新后运行`uv run --locked python scripts/validate_rules.py --write-review`，随后不带该选项可核对表格是否过期。

分组/嵌套选择以`rules.selection`声明，`postprocess=selection`表示SQL返回完整排名域；Q74的`store_top3`保留孤儿披露后再执行同一选择校验。不得把域SQL直接当最终答案。主仓库通用实现和接口契约见`decisions/2026-10-16-reference-rules-and-selection.md`，harness透传由Claude Code跟进。构建时`SEMDEBT_MAIN_DIR`须指向包含该实现的主仓库checkout。

本节取代上文“Q85仅保留截断SQL待T06”的旧状态。Q101–Q122的现行文件仍是第一轮工件，第二轮正式替换后必须重新声明rules和全量重算；规则覆盖不代表T05或T05b验收完成。

600条影响复验使用`uv run --locked python scripts/check_rules_impact.py --clean-baseline audit/session-clean-rules-baseline.json`。此命令要求主仓库checkout同时包含会话重置修复（主仓库PR #35的validate_scorer接口）及通用选择实现（PR #36）；串行独占chdb-eval。原始候选行留在SEMDEBT_DATA_DIR，题库报告只保存题号、判定与哈希。公开参考＋仅新契约是T02一致率轴；当前题库参考修订另列，不将judge示例当封闭答案。
