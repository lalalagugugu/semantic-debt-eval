#!/usr/bin/env python
"""Validate the approved post-freeze reference patch; --write also probes Q69."""
import argparse
from collections import Counter
import csv
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
BASE = '07dca9af414295205b0ae5f4a220bda44682af71'
REPORT = ROOT / 'audit/2026-10-18-reference-fixes.json'
CHANGED = {'Q34', 'Q50', 'Q71', 'Q99'}


def old(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def rows(contents):
    return list(csv.DictReader(io.StringIO(contents.decode())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    groups = ['questions/cube_100.yaml', 'questions/new.yaml']
    questions = {q['id']: q for name in groups for q in json.loads((ROOT/name).read_text())['questions']}
    previous = {q['id']: q for name in groups for q in json.loads(old(name))['questions']}
    manifest = json.loads((ROOT/'refs/MANIFEST.json').read_text())
    records = {r['question_id']: r for r in manifest['records'] if r['question_id'] in CHANGED}
    old_manifest = json.loads(old('refs/MANIFEST.json'))
    assert len(manifest['records']) == len(old_manifest['records']) == 136
    assert len(questions) == 122
    for qid, q in questions.items():
        baseline = previous[qid]
        assert q['text_zh'] == baseline['text_zh'] and q['text_en'] == baseline['text_en']
        assert 'required_columns' not in q['rules']
        assert all('required_columns' not in r.get('rules', {}) for r in q['refs'])
        assert q['split'] == baseline['split']
        if qid not in CHANGED | {'Q69'}:
            assert q == baseline, qid
        else:
            permitted = {'refs', 'rules', 'scoring_notes'} if qid in CHANGED else {'labels'}
            assert {k:v for k,v in q.items() if k not in permitted} == {k:v for k,v in baseline.items() if k not in permitted}
            if qid == 'Q69':
                assert {k:v for k,v in q['labels'].items() if k != 'low_discrimination'} == {k:v for k,v in baseline['labels'].items() if k != 'low_discrimination'}
    assert {k:v for k,v in manifest.items() if k!='records'} == {k:v for k,v in old_manifest.items() if k!='records'}
    for r, before in zip(manifest['records'], old_manifest['records'], strict=True):
        assert r['result_path'] == before['result_path']
        assert hashlib.sha256((ROOT/r['result_path']).read_bytes()).hexdigest() == r['sha256']
        if r['question_id'] not in CHANGED:
            assert r == before, r['result_path']
    details = {}
    for qid in sorted(CHANGED):
        r = records[qid]; path = r['result_path']
        before = rows(old(path)); after = rows((ROOT/path).read_bytes())
        if qid == 'Q34':
            by_key = {r['ProductKey']:r for r in after}
            assert all(by_key[r['ProductKey']] == r for r in before)
            added = [r for r in after if r['ProductKey'] not in {x['ProductKey'] for x in before}]
            assert len(after) == 2508 and len(added) == 4
            assert all(Decimal(r['total_cogs']) == Decimal(r['turnover_ratio']) == 0 and Decimal(r['avg_inventory']) > 0 for r in added)
            details[qid] = {'before_rows':len(before), 'after_rows':len(after), 'added_rows':added}
        elif qid == 'Q71':
            removed = [r for r in before if r['subcategory'] == '\\N']
            assert len(removed) == 1 and len(after) == 8
            assert Counter(tuple(r.items()) for r in after) == Counter(tuple(r.items()) for r in before if r['subcategory'] != '\\N')
            details[qid] = {'before_rows':len(before), 'after_rows':len(after), 'removed_rows':removed}
        else:
            alias = 'growth_amount' if qid == 'Q50' else 'weekend_difference_amount'
            assert [{k:v for k,v in r.items() if k!=alias} for r in after] == before
            for r in after:
                a,b = ('sales_2009','sales_2008') if qid=='Q50' else ('avg_weekend_day_sales','avg_weekday_sales')
                assert abs(Decimal(r[alias]) - (Decimal(r[a])-Decimal(r[b]))) < Decimal('0.000001')
            details[qid] = {'rows':len(after), 'new_column':alias, 'values':[r[alias] for r in after]}
        details[qid].update(reference=path, sql_sha256=records[qid]['sql_sha256'], reference_sha256=records[qid]['sha256'])
    q69 = questions['Q69']; ref = q69['refs'][0]
    assert q69['refs'] == previous['Q69']['refs'] and q69['rules'] == previous['Q69']['rules']
    assert q69['labels']['low_discrimination']['criteria'] == ['A']
    if args.write:
        from chdb import session
        sql = ref['sql'].replace('SELECT pr.PromotionCategory,', 'SELECT any(pr.PromotionCategory) AS PromotionCategory,').replace(' GROUP BY pr.PromotionCategory', '')
        probe = 'SELECT uniqExact(pr.PromotionCategory), uniqExact(pr.PromotionName) FROM retail.FactOnlineSales f JOIN retail.DimPromotion pr ON f.PromotionKey=pr.PromotionKey WHERE f.PromotionKey<>1'
        sess = session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR'])/'chdb-eval'))
        try:
            sess.query('SET max_threads=1, max_execution_time=0')
            ungrouped = json.loads(str(sess.query(sql, 'JSONCompact')))['data']
            cardinality = json.loads(str(sess.query(probe, 'JSONCompact')))['data']
        finally:
            sess.close()
        expected = rows((ROOT/ref['result_path']).read_bytes())
        assert cardinality[0][0] == 1 and len(ungrouped) == len(expected) == 1
        assert ungrouped[0][0] == expected[0]['PromotionCategory']
        from build_refs import load_selection_policy
        load_selection_policy()
        from harness.scorer import score
        reference_values = [[expected[0]['PromotionCategory'], *[float(v) for v in list(expected[0].values())[1:]]]]
        assert score(ungrouped, [reference_values], q69['rules']) == 'correct'
        evidence = {'conclusion':'中英文均明确促销类别，不含促销名解读；保留原参考，按最新裁决标A', 'criterion':'A：类别维度只有一个有效值，类别间营收排名退化；不将单行计算指标本身视为常数', 'category_count':cardinality[0][0], 'promotion_name_count':cardinality[0][1], 'ungrouped_sql':sql, 'ungrouped_rows':ungrouped, 'reference_rows':expected, 'comparison':'correct under frozen scorer tolerance; raw floating sums differ by aggregation order', 'cardinality_sql':probe, 'reference_unchanged':True, 'evidence_scope':'data and reference only; no candidate/model outputs'}
        REPORT.write_text(json.dumps({'baseline_commit':BASE, 'references':136, 'details':details, 'Q69':evidence, 'question_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in groups}, 'manifest_sha256':hashlib.sha256((ROOT/'refs/MANIFEST.json').read_bytes()).hexdigest()},ensure_ascii=False,indent=2)+'\n')
    report = json.loads(REPORT.read_text())
    assert report['details'] == details
    for name,digest in report['question_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest
    assert report['manifest_sha256'] == hashlib.sha256((ROOT/'refs/MANIFEST.json').read_bytes()).hexdigest()
    assert report['Q69']['category_count'] == 1
    print('PASS: 122 unchanged prompts/splits, 136 references, four approved fixes, Q69 rationale and A evidence; no required_columns')


if __name__ == '__main__':
    main()
