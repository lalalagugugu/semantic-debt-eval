# T05收尾验收记录

题库新分支codex/t05-finalize，起点491ef16；主仓库基线95575fd，包含已合并#36。第二轮采用已批准audit/T05-rewrite-draft.md的22题，第一轮文件另存audit/reviews/，不继承其复算结论。

## 条件(d)

7/122题包含分组或嵌套Top-N：外部5题Q22、Q71、Q74、Q85、Q98，新题2题Q117、Q119。#36同批600条的仅契约判定变化0；strict521/594、analytical487/594。参考修复轴另列，不能将其归为契约翻转。

## Q79快照

audit/Q79-boundary-members.json保存外部原始参考域的306个完整边界成员，量纲策略SHA256为7413327151dc85b9ff08233a191ce238dfe6722058b0c1fa71c0649facc540db。这是裁决要求追踪的历史公开域；现行中文参考的域另由MANIFEST标识，不能混用。

`uv run --locked python scripts/snapshot_q79_boundary.py --check`重新计算并按量化成员多重集合检查；`--freeze-check --independent-snapshot <T05b输出JSON>`比较独立pandas结果。没有T05b证据时拒绝冻结放行，不再要求找回10月15日不存在的行快照，也不以跨引擎原始哈希相同为条件。

当前状态：快照已保存，T05b独立复现待执行。后续所有完整边界参考CSV及MANIFEST中的规则／量纲版本共同保存为可复核快照。
