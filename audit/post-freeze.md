# eval-v1 冻结后修复记录

## 2026-10-18：用户批准的参考修复（拟 eval-v1.1，草稿）

- 冻结基线：07dca9af414295205b0ae5f4a220bda44682af71（main，eval-v1 的题库内容）。本次不移动冻结 tag，不发布 eval-v1.1；由用户决定合并与新版本冻结。
- 依据：主仓库 decisions/2026-10-18-reference-columns-asked-only.md 第五节第4条、decisions/2026-10-18-judge-stratum-and-t12-audit.md 第三节及用户本轮指令。
- Q50：保留两年同店总额与增长率，追加增长额 growth_amount（2009减2008）。
- Q99：保留日均及百分比，追加 weekend_difference_amount（周末日均减工作日日均）。
- Q34：由2009年库存产品域驱动左连接同年成本；无销售的成本按0，库存均值粒度不变；新增ProductKey 365、353、351、408共4行，周转率均0。原2504行全部不变，现2508行。
- Q71：挑选对象为NULL不回答任何子品类，从选择域中排除；仅删除1行，现8行。此项不改变其他汇总题保留空分组的规则。
- Q69：中英文明确“促销类别”，不是“促销名称”；无合理名称解读，不新增参考、不改题面或原参考。有效类别1个、名称9个，排名退化；按最新裁决标低区分度A。省略类别分组仍能按冻结评分规则判对；原始浮点求和约差0.04美元，完整原值保存在配套JSON，不声称完全相等。旧T06审计保留为eval-v1历史，Q69现行证据以本报告为准。
- 版本影响：122题、136份参考，4份参考修改，1题仅低区分度标注变化；全部题面、划分和其他参考保持。未加required_columns，未读独立标注，未重评600条、T12或主准确率。
- 审计/交接：audit/2026-10-18-reference-fixes.json；验证命令：`uv run --offline --no-sync python scripts/validate_t12_reference_fixes.py`。生成该证据含只读Q69探查时加`--write`；设置SEMDEBT_DATA_DIR，只用chdb-eval。
- 本轮数据依据仅数据与参考；暴露来源为T12，按裁决在T19披露。独立pandas复算由T05b后续完成，不以本次SQL严格复算代替。

验收：`build_refs.py --check` 全部122题136份严格复算通过；`validate_rules.py` 全部rules/类型/哈希及审阅表通过；`validate_t12_reference_fixes.py` 差异/范围/差值/标注校验通过；`validate_t04.py --fixtures-only` 合成守卫通过；5题参考自匹配通过。已更新规则审阅表，旧T04/T05/T06脚本中的未划分/参考不得改等阶段性断言不作为这次已批准冻结后参考补丁的验收口径。
