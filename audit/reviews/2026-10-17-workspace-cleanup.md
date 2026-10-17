# T05-work 工作区清点（2026-10-17）

基线：T05-work 4f13cb7；对照 main e3aaed630aed48ff0069c5ec24d8d7d2a0765f9d（#15、#16已合并）。

## 保留但不合入当前 main

- 原样保留独有审计：audit/T05-scoring-contract-gap.md、audit/T05-self-check.json、audit/T05-self-check.md。
- 原样保留历史工具：scripts/check_grouped_topn_contract.py、scripts/check_t05_design_audit.py。前者复现旧全局Top-N表达缺口，后者校验旧设计稿；均不是当前题库验收命令。
- decisions/open-questions.md 与 tasks/T05-new-questions.md 的本地备注保存为同目录 local-workspace-notes.patch；只作历史证据，不恢复过时状态。
- T05-grouped-topn-preflight.md仅缺少main新增的完成状态，无新增证据，使用main版本。

## 已入库内容

逐文件原始SHA256、Git对象及历史路径见配套JSON；完整blob在main历史出现过的不重复提交。audit/T05-review.md的本地批注已完整保存在audit/reviews/2026-10-16-t05-first-review.md。

## 临时文件与回退

唯一临时文件.DS_Store（6148字节）已向用户请求删除许可，未获许可不删除；可移出题库保留。清理前全部51个文件另有仓库外tar备份，位置见JSON。

## 逐文件分类

| 文件 | 归类 |
|---|---|
| .DS_Store | unique_local |
| audit/T05-candidate-design.md | identical_main |
| audit/T05-grouped-topn-preflight.md | unique_local |
| audit/T05-reference-data-quality.json | identical_main |
| audit/T05-reference-data-quality.md | identical_main |
| audit/T05-rewrite-draft.md | in_main_history |
| audit/T05-scoring-contract-gap.md | unique_local |
| audit/T05-self-check.json | unique_local |
| audit/T05-self-check.md | unique_local |
| audit/reviews/2026-10-16-t05-candidate-design-approved.md | identical_main |
| audit/reviews/2026-10-16-t05-first-questions.yaml | identical_main |
| audit/reviews/2026-10-16-t05-first-reference-manifest.json | identical_main |
| audit/reviews/2026-10-16-t05-first-review.md | identical_main |
| audit/rules-backfill-review.md | in_main_history |
| audit/rules-impact.json | in_main_history |
| audit/rules-impact.md | identical_main |
| audit/rules-validation.md | identical_main |
| audit/session-clean-rules-baseline.json | identical_main |
| audit/session-clean-rules-baseline.md | identical_main |
| decisions/2026-10-16-orphan-key-audit-and-ranked-refs.md | identical_main |
| decisions/2026-10-16-q74-orphan-products-reference-correction.md | identical_main |
| decisions/2026-10-16-rules-backfill-contract.md | identical_main |
| decisions/2026-10-16-t05-redesign-approval.md | in_main_history |
| scripts/audit_reference_data_quality.py | in_main_history |
| scripts/check_grouped_topn_contract.py | unique_local |
| scripts/check_rules_impact.py | in_main_history |
| scripts/check_t05_design_audit.py | unique_local |
| scripts/validate_rules.py | in_main_history |
| audit/T05-review.md | in_main_history |
| audit/T05b-handoff.md | in_main_history |
| decisions/open-questions.md | unique_local |
| questions/cube_100.yaml | in_main_history |
| questions/schema.json | in_main_history |
| refs/MANIFEST.json | in_main_history |
| refs/README.md | in_main_history |
| refs/cube/Q33-1.csv | in_main_history |
| refs/cube/Q45-1.csv | in_main_history |
| refs/cube/Q67-1.csv | in_main_history |
| refs/cube/Q74-1.csv | identical_main |
| refs/cube/Q85-1.csv | in_main_history |
| refs/cube/Q87-1.csv | in_main_history |
| refs/cube/Q92-1.csv | in_main_history |
| refs/cube/Q94-1.csv | identical_main |
| refs/cube/Q97-1.csv | identical_main |
| refs/cube/Q97-2.csv | identical_main |
| refs/cube/Q98-1.csv | in_main_history |
| refs/cube/Q98-2.csv | in_main_history |
| scripts/build_refs.py | in_main_history |
| scripts/check_vendor_refs.py | identical_main |
| scripts/validate_t04.py | in_main_history |
| tasks/T05-new-questions.md | unique_local |
