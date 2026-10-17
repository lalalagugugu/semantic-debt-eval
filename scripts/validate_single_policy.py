#!/usr/bin/env python
"""Database-free acceptance checks for the 2026-10-17 bank ruling."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

from build_refs import effective_rules, load_unit_policy
from check_rules_impact import csv_rows

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,os.environ['SEMDEBT_MAIN_DIR'])
from harness.scorer import _boundary_start, score


def main():
    policy=json.loads((ROOT/'audit/2026-10-17-single-policy-review.json').read_text())
    baseline=json.loads((ROOT/'audit/reviews/2026-10-17-before-single-policy.json').read_text())
    questions={q['id']:q for name in ('cube_100','new') for q in json.loads((ROOT/f'questions/{name}.yaml').read_text())['questions']}
    manifest=json.loads((ROOT/'refs/MANIFEST.json').read_text());records={r['result_path']:r for r in manifest['records']}
    assert len(questions)==122 and len(records)==policy['final_references']==133
    assert len(policy['extra_reference_inventory'])==43
    assert Counter(r['category'] for r in policy['extra_reference_inventory'])=={'口径歧义':30,'展示方式':2,'问法歧义':11}
    retired={r['reference'] for r in policy['removed_references']}
    assert len(retired)==32 and not retired.intersection(records)
    assert not any((ROOT/path).exists() for path in retired)
    assert {str(p.relative_to(ROOT)) for directory in ('cube','new') for p in (ROOT/f'refs/{directory}').glob('*.csv')}==set(records)
    for q in questions.values():
        assert all('购买事件=SalesQuantity>0' not in r['interpretation'] for r in q['refs'])
        assert '保留全部行与正销量两种参考' not in q['scoring_notes']
        assert '空产品属性组裁决：有／无' not in q['scoring_notes']
    original={q['id']:q for q in baseline['questions']}
    vendor=json.loads((ROOT/'vendor/cube/text_to_sql_benchmark.json').read_text())['questions']
    assert all(questions[f"Q{int(q['id']):02d}"]['text_en']==q['question'] for q in vendor)
    assert questions['Q114']['text_zh']==original['Q114']['text_zh']
    assert len(questions['Q114']['refs'])==len(questions['Q116']['refs'])==len(questions['Q65']['refs'])==1
    assert questions['Q65']['refs'][0]['result_path']=='refs/cube/Q65-2.csv'
    assert questions['Q114']['refs'][0]['result_path']=='refs/new/Q114-1.csv'
    assert records['refs/cube/Q100-1.csv']['row_count']==108
    previous={r['result_path']:r for r in baseline['manifest']['records']}
    assert questions['Q93']['refs']==original['Q93']['refs']
    assert records['refs/cube/Q93-1.csv']==previous['refs/cube/Q93-1.csv']
    for name,digest in policy['source_sha256'].items():
        assert hashlib.sha256((Path(os.environ['SEMDEBT_MAIN_DIR'])/'semantic'/name).read_bytes()).hexdigest()==digest
    for name,digest in policy['current_question_sha256'].items():
        assert hashlib.sha256((ROOT/f'questions/{name}.yaml').read_bytes()).hexdigest()==digest
    for qid in ('Q27','Q45','Q79','Q87'):
        q=questions[qid];ref=q['refs'][0];rule=effective_rules(q,ref);rows=csv_rows(records[ref['result_path']])
        n=rule['top_n'];candidate=deepcopy(rows if n is None else rows[:n])
        assert score(candidate,[rows],rule)=='correct'
        rank_column=rule['order_by'][0]['column']
        for row in candidate:row[rank_column]=round(row[rank_column],2)
        assert score(candidate,[rows],rule)=='correct',qid
    q=questions['Q85'];ref=q['refs'][0];rows=csv_rows(records[ref['result_path']]);candidate=[]
    for bucket in ('BOTTOM','TOP'):candidate.extend(deepcopy([r for r in rows if r[0]==bucket][:5]))
    for row in candidate:row[4]=round(row[4],2)
    assert score(candidate,[rows],effective_rules(q,ref))=='correct'
    q=questions['Q27'];ref=q['refs'][0];rows=csv_rows(records[ref['result_path']]);rule=effective_rules(q,ref)
    assert len(rows)==12 and _boundary_start(rows,10,tuple(rule['tie_columns']),tuple(rule['value_kinds']))==9
    snapshot=json.loads((ROOT/'audit/Q79-boundary-members.json').read_text())
    assert snapshot['row_count']==len(snapshot['rows'])
    assert snapshot['reference_sha256']==records['refs/cube/Q79-1.csv']['sha256']
    assert snapshot['sql_sha256']==records['refs/cube/Q79-1.csv']['sql_sha256']
    assert policy['Q79_boundary_check']['same_store_member_set']
    # A reproducible statistic used by the gap audit, checked against expansion.
    from audit_semantic_gaps import weighted_correlations,correlation,ranks
    frequencies=[(0,2,2),(1,1,1),(1,3,3)]
    expanded=[(x,y) for x,y,n in frequencies for _ in range(n)]
    a,b=weighted_correlations(frequencies)
    xs=[r[0] for r in expanded];ys=[r[1] for r in expanded]
    assert abs(a-correlation(xs,ys))<1e-12 and abs(b-correlation(ranks(xs),ranks(ys)))<1e-12
    from check_purchase_event_impact import apply
    try:
        apply({})
    except ValueError as error:
        assert '2026-10-17' in str(error)
    else:
        raise AssertionError('withdrawn purchase-event alternatives must not be reapplied')
    print('PASS: 43 extra-reference decisions, 122 prompt reviews, 133 active references, retired files, Q93 unchanged, unrounded/rounded scorer compatibility and Q79 provenance')


if __name__=='__main__':main()
