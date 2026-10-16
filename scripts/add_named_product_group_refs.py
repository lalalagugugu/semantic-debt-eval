#!/usr/bin/env python
"""Review/apply optional empty-product-group references under the user ruling."""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path

from audit_orphan_group_rows import GROUP_COLUMNS
from build_refs import effective_rules
from check_rules_impact import csv_rows

ROOT=Path(__file__).resolve().parent.parent
# Explicitly authored eligibility; never infer business share semantics from aliases.
PURE_GROUPS={'Q05','Q11','Q61','Q62','Q67','Q71','Q86','Q92','Q102','Q104'}
LOCAL_RATIOS={'Q24','Q90','Q95','Q99','Q121'}
EXCLUDED_SHARES={'Q76','Q98','Q117'}
ARCHIVE=ROOT/'audit/reviews/2026-10-16-before-empty-group-refs.json'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--allow-local-ratios',action='store_true')
    args=parser.parse_args()
    paths=[ROOT/'questions/cube_100.yaml',ROOT/'questions/new.yaml']
    questions=sum([json.loads(p.read_text())['questions'] for p in paths],[])
    manifest=json.loads((ROOT/'refs/MANIFEST.json').read_text())
    baseline=json.loads(ARCHIVE.read_text()) if ARCHIVE.exists() else {'questions':deepcopy(questions),'manifest':manifest}
    by_path={r['result_path']:r for r in manifest['records']}
    adapter_path=Path(os.environ['SEMDEBT_MAIN_DIR'])/'scripts/validate_scorer.py'
    spec=importlib.util.spec_from_file_location('orphan_sql_order',adapter_path)
    adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    report=[]
    additions=0
    existing=0
    for q in questions:
        candidates=[]
        for ref in q['refs']:
            record=by_path[ref['result_path']]
            attrs=[c['name'] for c in record['columns'] if c['name'] in GROUP_COLUMNS]
            if not attrs:
                continue
            rows=csv_rows(record)
            indices=[i for i,c in enumerate(record['columns']) if c['name'] in attrs]
            empty=sum(any(row[i] in (None,'') for i in indices) for row in rows)
            if empty:
                candidates.append((ref,record,attrs,empty,len(rows)))
        eligible=q['id'] in PURE_GROUPS or (args.allow_local_ratios and q['id'] in LOCAL_RATIOS)
        if q['id'] in EXCLUDED_SHARES:
            reason='excluded: total/share/parent-denominator semantics'
        elif q['id'] in LOCAL_RATIOS:
            reason='allowed: within-group ratio/statistic' if args.allow_local_ratios else 'pending: within-group ratio/statistic scope'
        elif q['id'] in PURE_GROUPS:
            reason='allowed: named product-attribute groups independent of empty row'
        else:
            reason='not eligible: product identity, detail or other grouping'
        item={'question_id':q['id'],'eligible':eligible,'reason':reason,'empty_group_references':[],'additions':[],'existing_optional_references':[]}
        for ref,record,attrs,empty,total in candidates:
            detail={'source_reference':ref['result_path'],'attribute_columns':attrs,'empty_rows':empty,'named_rows':total-empty}
            item['empty_group_references'].append(detail)
            if not eligible:
                continue
            rules=effective_rules(q,ref)
            if rules['top_n'] is not None:
                raise ValueError('review fixed-N attribute ranking explicitly before adding filtered reference')
            new=deepcopy(ref)
            columns=['`'+name.replace('`','``')+'`' for name in attrs]
            predicate=' AND '.join(f"({name} IS NOT NULL AND {name} != '')" for name in columns)
            new['sql']='SELECT * FROM (\n'+ref['sql'].rstrip().rstrip(';')+'\n) AS named_product_groups\nWHERE '+predicate
            if rules['ordered']:
                order=adapter.final_order_clause(ref['sql'])
                if not order:
                    raise ValueError('missing ordered source clause')
                new['sql']+='\nORDER BY '+order
            previous=next((r for r in q['refs'] if r['sql']==new['sql']),None)
            if previous:
                item['existing_optional_references'].append(previous['result_path'])
                existing+=1
                continue
            new['interpretation']+='；按产品属性分组时不展示空属性组（有名称各组及其原分母保持不变）'
            new['result_path']=f"refs/{'cube' if q['source']=='cube' else 'new'}/{q['id']}-{len(q['refs'])+len(item['additions'])+1}.csv"
            new['rules']=deepcopy(rules)
            item['additions'].append(new)
            additions+=1
        if args.apply and item['additions']:
            q['refs'].extend(item['additions'])
            q['scoring_notes']+='\n2026-10-16空产品属性组裁决：有／无空属性组均接受；分母保持原完整定义，不扩展到产品键Top-N。详见audit/optional-product-group-refs.json。'
        report.append(item)
    result={'questions_scanned':len(questions),'baseline_references':len(baseline['manifest']['records']),'added_references':existing+additions,'added_this_invocation':additions,'final_references':sum(len(q['refs']) for q in questions) if args.apply else len(by_path)+additions,'local_ratios_allowed':args.allow_local_ratios,'applied':args.apply,'records':report}
    if args.apply:
        if not ARCHIVE.exists():
            ARCHIVE.write_text(json.dumps(baseline,ensure_ascii=False,indent=2)+'\n')
        for path,source in zip(paths,['cube','new'],strict=True):
            path.write_text(json.dumps({'questions':[q for q in questions if q['source']==source]},ensure_ascii=False,indent=2)+'\n')
        (ROOT/'audit/optional-product-group-refs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},ensure_ascii=False))
    for r in report:
        if r['empty_group_references']:
            print(r['question_id'],r['reason'],[(c['source_reference'],c['empty_rows']) for c in r['empty_group_references']],flush=True)


if __name__=='__main__':
    main()
