#!/usr/bin/env python
"""Classify all 43 regressions against references with the empty group removed.

This diagnostic does not decide reference eligibility. It checks the original
candidate outputs retained by the complete prior 600-query execution.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

from build_refs import effective_rules, load_selection_policy
from check_rules_impact import csv_rows, verdict_only

ROOT=Path(__file__).resolve().parent.parent
GROUP_COLUMNS={'ProductCategoryName','ProductSubcategoryName','BrandName','ColorName','category','subcategory'}


def main():
    load_selection_policy()
    source=ROOT/'audit/T05-final-reference-delta.json'
    delta=json.loads(source.read_text())['records']
    if len(delta)!=43:
        raise ValueError('expected original 43-regression cohort')
    baseline=json.loads((ROOT/'audit/rules-final-impact.json').read_text())
    raw_path=Path(baseline['raw_candidates_path'])
    if hashlib.sha256(raw_path.read_bytes()).hexdigest()!=baseline['raw_candidates_sha256']:
        raise ValueError('candidate audit hash mismatch')
    archived=ROOT/'audit/reviews/2026-10-16-before-empty-group-refs.json'
    bank=json.loads(archived.read_text())
    questions={int(q['id'][1:]):q for q in bank['questions'] if q['source']=='cube'}
    manifest={r['result_path']:r for r in bank['manifest']['records']}
    for rec in manifest.values():
        if rec['question_id'] not in {q['id'] for q in questions.values()}:
            continue  # New-question rewrites are outside this external cohort.
        if hashlib.sha256((ROOT/rec['result_path']).read_bytes()).hexdigest()!=rec['sha256']:
            raise ValueError('original reference changed: '+rec['result_path'])
    targets={(r['system'],r['question_id']):r for r in delta}
    records=[]
    for line in raw_path.open():
        candidate=json.loads(line)
        key=candidate['system'],candidate['question_id']
        if key not in targets:
            continue
        q=questions[key[1]]
        item={**targets[key],'attribute_group_only':False,'empty_group_only':False,'reference_checks':[]}
        for ref in q['refs']:
            rec=manifest[ref['result_path']]
            columns=[i for i,c in enumerate(rec['columns']) if c['name'] in GROUP_COLUMNS]
            if not columns:
                continue
            item['attribute_group_only']=True
            rows=csv_rows(rec)
            named=[r for r in rows if all(r[i] not in (None,'') for i in columns)]
            removed=len(rows)-len(named)
            if removed==0:
                continue
            result=verdict_only(candidate['rows'],[named],effective_rules(q,ref))
            check={'reference':ref['result_path'],'removed_empty_group_rows':removed,'named_group_rows':len(named),'named_groups_match':result.outcome=='correct','outcome_without_empty_group':result.outcome,'reason':result.reason}
            item['reference_checks'].append(check)
            item['empty_group_only']|=result.outcome=='correct'
        item['category']='only_empty_group_row' if item['empty_group_only'] else 'product_identity_or_detail_rows' if not item['attribute_group_only'] else 'named_group_values_or_structure_also_differ'
        records.append(item)
        print(key,item['category'],flush=True)
    if len(records)!=43:
        raise ValueError('missing regression candidates')
    records.sort(key=lambda r:(r['system'],r['question_id']))
    result={'source_delta_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'previous_bank_sha256':hashlib.sha256(archived.read_bytes()).hexdigest(),'raw_candidates_sha256':baseline['raw_candidates_sha256'],'classified':43,'counts':dict(Counter(r['category'] for r in records)),'records':records}
    (ROOT/'audit/orphan-group-regressions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    lines=['# 43条correct→wrong逐条分类','', '固定此前148份参考及同批600条原始候选，不执行新SQL。此表先核对“唯一差别是否为空组行”；可否增加替代参考仍按裁决的总额／占比／产品键Top-N边界单独判定。NULL和空串均视为缺失产品属性，不更改有名称组的值、类型或选择约束。','', '| 系统 | 题号 | 类别 | 去掉空组后的逐参考结果 |','|---|---|---|---|']
    for r in records:
        checks='；'.join(f"{Path(c['reference']).stem}: -{c['removed_empty_group_rows']}行, {c['outcome_without_empty_group']}" for c in r['reference_checks']) or '产品键／明细任务，不是空属性分组'
        lines.append(f"| {r['system']} | Q{r['question_id']:02d} | {r['category']} | {checks} |")
    lines+=['','汇总：'+json.dumps(result['counts'],ensure_ascii=False),'']
    (ROOT/'audit/orphan-group-regressions.md').write_text('\n'.join(lines))
    print(json.dumps(result['counts'],ensure_ascii=False))


if __name__=='__main__':
    main()
