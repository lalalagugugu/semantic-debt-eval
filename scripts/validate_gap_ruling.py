#!/usr/bin/env python
"""Validate the approved gap ruling against current refs and measured evidence."""
import hashlib
import argparse
import json
import math
import os
import sys
from pathlib import Path

from build_refs import effective_rules
from check_rules_impact import csv_rows

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,os.environ['SEMDEBT_MAIN_DIR'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sql-fixtures',action='store_true',help='also run constant SQL fixtures in an in-memory chDB')
    args=parser.parse_args()
    questions={q['id']:q for name in ('cube_100','new') for q in json.loads((ROOT/f'questions/{name}.yaml').read_text())['questions']}
    records={r['result_path']:r for r in json.loads((ROOT/'refs/MANIFEST.json').read_text())['records']}
    expected={'Q13':1,'Q28':1,'Q38':1,'Q39':2,'Q40':1,'Q47':1,'Q48':3,'Q76':2,'Q84':2,
              'Q86':2,'Q91':2,'Q92':1,'Q95':1,'Q97':2,'Q98':2,'Q100':1,'Q117':1,'Q118':1,'Q119':1,'Q121':2}
    review=json.loads((ROOT/'audit/2026-10-17-gap-ruling-review.json').read_text())
    topn=review.get('q122_topn')
    assert len(questions)==122 and len(records)==(137 if topn else 136)
    for qid,count in expected.items():
        assert len(questions[qid]['refs'])==count,(qid,count)
    assert review['final_references']==len(records) and len(review['added_references'])==(6 if topn else 5) and len(review['removed_references'])==2
    assert len(review['over_50_rows'])==(20 if review.get('summary_rewrites') else 22)
    assert [r['question_id'] for r in review['over_50_rows'] if r['exceeds_50_due_to_ties']]==['Q85']
    for check in review['rewritten_question_checks']:
        assert not any(check[k]['hit'] for k in ('A','B','C'))
        assert check['text']==questions[check['question_id']]['text_zh']
    for name,digest in review['current_question_sha256'].items():
        assert hashlib.sha256((ROOT/f'questions/{name}.yaml').read_bytes()).hexdigest()==digest
    if review.get('summary_rewrites'):
        summary=json.loads((ROOT/'audit/2026-10-17-summary-rewrites.json').read_text())
        assert summary['unchanged_questions_verified']==119
        assert {r['question_id'] for r in summary['records']}=={'Q14','Q21','Q122'}
        for item in summary['records']:
            if item['question_id']=='Q122' and topn:
                assert topn['old_text_zh']==item['new_text_zh']
                assert topn['new_text_zh']==questions['Q122']['text_zh']
            else:
                assert item['new_text_zh']==questions[item['question_id']]['text_zh']
            assert not any(item[k]['hit'] for k in ('A','B','C'))
            assert item['capability']['retained'] is True
        assert csv_rows(records['refs/cube/Q14-1.csv'])==[[385]]
        assert records['refs/cube/Q21-1.csv']['row_count']==306
        row=csv_rows(records['refs/new/Q122-1.csv'])[0]
        q122=questions['Q122'];rule=effective_rules(q122,q122['refs'][0])
        if topn:
            assert len(q122['refs'])==2 and len(row)==6
            assert rule['top_n']==10 and rule['tie_columns']==[4]
            assert rule['value_kinds']==['other','other','other','other','count','ratio']
            assert topn['unchanged_questions_verified']==121
            for item in topn['references']:
                assert item['reference_rows']==17 and item['nth_common_orders']==13
                assert item['strict_prefix_members']==7 and item['boundary_members']==10 and not item['C_hit']
        else:
            assert len(row)==5 and row[0]==378070
            assert rule['value_kinds']==['count','ratio','ratio','ratio','ratio']
            from harness.scorer import score
            assert score([[376026,*row[1:]]],[[row]],rule)=='wrong'
    for qid in ('Q13','Q28'):
        q=questions[qid];sql=q['refs'][0]['sql']
        assert '平均单价' in q['text_zh'] and all(s not in q['text_zh'] for s in ('订单','交易','除以','÷'))
        assert 'FactSales' in sql and 'FactOnlineSales' not in sql and 'sum(f.SalesQuantity)' in sql
    assert records['refs/cube/Q13-1.csv']['row_count']==306
    assert records['refs/cube/Q28-1.csv']['row_count']==2
    assert questions['Q38']['refs'][0]['result_path']=='refs/cube/Q38-2.csv'
    assert 'ASOF LEFT JOIN' in questions['Q40']['refs'][0]['sql']
    assert effective_rules(questions['Q92'],questions['Q92']['refs'][0])['order_by']==[{'column':3,'descending':True}]
    assert 'ORDER BY gross_margin_pct DESC' in questions['Q92']['refs'][0]['sql']
    correlations={r['question_id']:r for r in json.loads((ROOT/'audit/2026-10-17-correlation-gap-final.json').read_text())['records']}
    for qid in ('Q48','Q91'):
        row=csv_rows(records[questions[qid]['refs'][-1]['result_path']])[0]
        assert math.isclose(float(row[0]),correlations[qid]['spearman'],abs_tol=1e-12),qid
    rows={r[0]:r for r in csv_rows(records[questions['Q86']['refs'][-1]['result_path']])}
    for expected in correlations['Q86']['details']:
        row=rows[expected['subcategory']]
        assert math.isclose(float(row[1]),expected['spearman'],abs_tol=1e-12)
        assert row[2]==expected['observations']
    assert len(rows)==len(correlations['Q86']['details'])==31
    before=csv_rows(records['refs/cube/Q84-1.csv']);after=csv_rows(records['refs/cube/Q84-2.csv'])
    assert {r[0]:r[1] for r in before}=={'A':1132,'B':666,'C':706}
    assert {r[0]:r[1] for r in after}=={'A':1131,'B':666,'C':707}
    assert all(row[3]<0 for row in csv_rows(records['refs/cube/Q95-1.csv']))
    old=json.loads((ROOT/'audit/reviews/2026-10-17-before-gap-ruling.json').read_text())
    old_records={r['result_path']:r for r in old['manifest']['records']}
    assert old_records['refs/new/Q119-2.csv']['sha256']==records['refs/new/Q119-1.csv']['sha256']
    assert all(not (ROOT/p).exists() for p in review['removed_references'])
    if args.sql_fixtures:
        import chdb
        from apply_semantic_gap_ruling import spearman_sql
        from audit_semantic_gaps import correlation, ranks
        samples=[[(0.,2.),(0.,2.),(1.,1.),(1.,3.),(1.,3.),(1.,3.)],
                 [(1.,3.),(2.,2.),(3.,1.)],[(0.,1.),(0.,2.),(0.,3.)]]
        for sample in samples:
            tuples=','.join(f'({x},{y})' for x,y in sample)
            domain=f'SELECT tupleElement(t,1) AS x,tupleElement(t,2) AS y FROM (SELECT arrayJoin([{tuples}]) AS t)'
            actual=json.loads(str(chdb.query(spearman_sql(domain,'correlation'),'JSONCompact')))['data'][0][0]
            expected=correlation(ranks([x for x,y in sample]),ranks([y for x,y in sample]))
            assert actual is None if expected is None else math.isclose(actual,expected,abs_tol=1e-12)
        print('PASS: SQL average-tie ranks with duplicate observations, reverse ranks and constant-domain NULL')
    print(f"PASS: 17 gap rulings, {len(records)} refs, {len(review['rewritten_question_checks'])+len(review.get('summary_rewrites',[]))} rewrite checks, weighted Spearman, ABC boundaries, {len(review['over_50_rows'])} long results and retired paths")


if __name__=='__main__':
    main()
