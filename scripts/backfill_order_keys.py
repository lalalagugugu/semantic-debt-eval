#!/usr/bin/env python
"""Persist reviewed reference-order keys; never infer them inside the scorer."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from build_refs import effective_rules, load_unit_policy

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[os.environ['SEMDEBT_MAIN_DIR'],str(Path(os.environ['SEMDEBT_MAIN_DIR'])/'scripts')]
from harness.questions import bank_anchor_rules
from harness.scorer import _parse_rules
from validate_scorer import final_order_clause, question_rules


def reference_order(sql,columns,declared=None):
    clause=final_order_clause(sql)
    if not clause:raise ValueError('ordered reference lacks an outer ORDER BY')
    if declared:
        return deepcopy(declared),'existing explicit selection.output_order'
    keys=[]
    rounded=False
    for part in clause.split(','):
        match=re.fullmatch(r'\s*([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)(?:\s+(ASC|DESC))?\s*',part,re.I)
        if not match:raise ValueError('review non-column ordering expression explicitly: '+part)
        expression,direction=match.groups(); tail=expression.split('.')[-1].lower()
        positions=[i for i,c in enumerate(columns) if c['name'].lower()==expression.lower() or c['name'].split('.')[-1].lower()==tail]
        if not positions:
            aliases=set(re.findall(r'\b'+re.escape(expression)+r'\s+AS\s+([A-Za-z_]\w*)\b',sql,re.I))
            rounded_aliases=set(re.findall(r'\bround\(\s*'+re.escape(expression)+r'\s*,\s*\d+\s*\)\s+AS\s+([A-Za-z_]\w*)\b',sql,re.I))
            rounded|=bool(rounded_aliases)
            aliases.update(rounded_aliases)
            positions=[i for i,c in enumerate(columns) if c['name'].lower() in {a.lower() for a in aliases}]
        if len(positions)!=1:raise ValueError('ordering column is not uniquely projected: '+expression)
        keys.append({'column':positions[0],'descending':direction is not None and direction.upper()=='DESC'})
    return keys,('outer ORDER BY uses projected ROUND value under the existing reference/tie precision contract' if rounded else 'outer ORDER BY resolved to projected reference columns/aliases')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    paths=[ROOT/'questions/cube_100.yaml',ROOT/'questions/new.yaml']
    questions=sum([json.loads(path.read_text())['questions'] for path in paths],[])
    manifest=json.loads((ROOT/'refs/MANIFEST.json').read_text())
    by_path={r['result_path']:r for r in manifest['records']}
    current=[]
    for q in questions:
        for ref in q['refs']:
            rules=deepcopy(effective_rules(q,ref))
            if not rules['ordered']:continue
            rec=by_path[ref['result_path']]
            keys,source=reference_order(ref['sql'],rec['columns'],rules.get('selection',{}).get('output_order'))
            rules['order_by']=keys;_parse_rules(rules)
            current.append({'question_id':q['id'],'reference':ref['result_path'],'order_clause':final_order_clause(ref['sql']),
                            'order_by':keys,'columns':rec['columns'],'source':source,'sql_sha256':rec['sql_sha256']})
            if args.apply:ref['rules']=rules;rec['rules']=rules
        if args.apply:q['rules']=deepcopy(effective_rules(q,q['refs'][0]))
    public=json.loads((ROOT/'vendor/cube/text_to_sql_benchmark.json').read_text())['questions']
    folder=Path(os.environ['SEMDEBT_DATA_DIR'])/'anchor-refs/paper-2026-04-22'
    cached={int(r['vendor_id']):r for r in json.loads((folder/'MANIFEST.json').read_text())['records']}
    own=bank_anchor_rules(ROOT)
    originals=[]
    for q in public:
        qid=int(q['id']);sql=q['expected_sql'];rules=question_rules(qid,sql)
        if not rules['ordered'] or qid==33:continue
        payload_path=folder/f'q{qid:02d}.json'; raw=payload_path.read_bytes();entry=cached[qid]
        if hashlib.sha256(raw).hexdigest()!=entry['sha256'] or hashlib.sha256(sql.strip().rstrip(';').encode()).hexdigest()!=entry['sql_sha256']:
            raise ValueError('original reference provenance differs')
        payload=json.loads(raw);declared=own.get(qid,{}).get('rules',{}).get('selection',{}).get('output_order')
        keys,source=reference_order(sql,payload['meta'],declared)
        originals.append({'question_id':qid,'order_clause':final_order_clause(sql),'order_by':keys,'columns':payload['meta'],
                          'source':source,'sql_sha256':entry['sql_sha256'],'payload_sha256':entry['sha256']})
    if args.apply:
        for path,source in zip(paths,['cube','new'],strict=True):
            path.write_text(json.dumps({'questions':[q for q in questions if q['source']==source]},ensure_ascii=False,indent=2)+'\n')
        (ROOT/'refs/MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        _,policy_hash=load_unit_policy()
        review={'unit_policy_sha256':policy_hash,'current_ordered_references':len(current),'original_ordered_validation_references':len(originals),
                'current_records':current,'original_records':originals}
        (ROOT/'audit/ordered-rules-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
        lines=['# 显式排序键逐参考审阅','',
               '排序键只在题库维护阶段从实际参考排序和现有声明映射并持久化；评分器不读SQL、不按题猜。column为参考列0起位置；方向及复合顺序逐字声明。块相等复用全局量纲固定量化，不用结果容差。EN74原SQL按未投影的行号排序，沿用此前已批准的selection.output_order（门店、产品销售额）声明，不新增隐藏列或改变原参考。','',
               '| 范围／参考 | 最终排序 | 持久化order_by | 映射来源 |','|---|---|---|---|']
        for prefix,items in [('当前',current),('原始',originals)]:
            for r in items:lines.append('| '+' | '.join([prefix+'/'+str(r.get('reference',r['question_id'])),r['order_clause'],json.dumps(r['order_by']),r['source']])+' |')
        lines+=['',f'当前{len(current)}份有序参考全部补齐；原公开600条验证范围中{len(originals)}份有序原始参考排序键另存于配套JSON。Q33无可用公开原始参考，不伪造其排序元数据。实际英文锚点按T11规则选择：同结构逐参考rules原样透传，8份结构不同的规则由review_anchor_rules.py单独更新。','']
        (ROOT/'audit/ordered-rules-review.md').write_text('\n'.join(lines))
    print(json.dumps({'ordered_current':len(current),'ordered_original':len(originals),'applied':args.apply}))


if __name__=='__main__':main()
