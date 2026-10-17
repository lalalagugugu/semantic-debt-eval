#!/usr/bin/env python
"""Narrow, database-free checks of T05 questions and scoring metadata."""
from collections import Counter
from contextlib import redirect_stderr
from copy import deepcopy
import csv
import hashlib
import io
import json
from pathlib import Path
import math
import re

import yaml

from build_refs import effective_rules, has_final_order_by, load_unit_policy, postprocess_reference, reference_value_kinds, validate_questions

REPO = Path(__file__).resolve().parent.parent


def expect_error(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('expected explicit validation failure')


def main():
    old = yaml.safe_load((REPO / 'questions/cube_100.yaml').read_text())['questions']
    new = yaml.safe_load((REPO / 'questions/new.yaml').read_text())['questions']
    validate_questions(old)
    validate_questions(new, 'new')
    assert len(new) == 22
    assert not has_final_order_by('WITH x AS (SELECT 1 ORDER BY 1) SELECT * FROM x')
    assert not has_final_order_by("SELECT 'ORDER BY', 1 -- ORDER BY 1")
    assert has_final_order_by('WITH x AS (SELECT 1) SELECT * FROM x ORDER BY 1')
    assert not has_final_order_by('SELECT `ORDER BY`, 1')
    sample = deepcopy(new[0])
    sample['refs'][0].pop('rules',None)  # Exercise question-level inheritance, not an override.
    sample['rules']['ordered'] = True
    expect_error(lambda: validate_questions([sample], 'new'))
    sample = deepcopy(new[0])
    sample['refs'][0].pop('rules',None)  # Exercise question-level inheritance, not an override.
    del sample['rules']['value_kinds']
    expect_error(lambda: validate_questions([sample], 'new'))
    sample = deepcopy(new[0])
    sample['refs'][0].pop('rules',None)  # Exercise question-level inheritance, not an override.
    columns = [{'name': 'GMV', 'type': 'Float64'}]
    with redirect_stderr(io.StringIO()) as capture:
        kinds, warnings = reference_value_kinds(sample, sample['refs'][0], columns, ['other'])
    assert kinds == ['amount'] and warnings[0]['column_position'] == 1
    assert warnings[0]['declared'] == 'amount' and warnings[0]['inferred'] == 'other'
    assert 'Q101' in capture.getvalue() and 'VALUE_KIND_MISMATCH' in capture.getvalue()
    sample['rules']['value_types'] = ['UInt64']
    expect_error(lambda: reference_value_kinds(sample, sample['refs'][0], columns, ['other']))
    sample['rules']['value_types'] = ['Float64']
    sample['rules']['value_kinds'] = ['amount', 'count']
    expect_error(lambda: reference_value_kinds(sample, sample['refs'][0], columns, ['other']))

    counts = Counter(label for q in old + new for label in q['labels']['complexity_source']['items'])
    assert all(count >= 8 for count in counts.values()), counts
    manifest = json.loads((REPO / 'refs/MANIFEST.json').read_text())
    records = {r['result_path']: r for r in manifest['records']}
    assert set(records) == {r['result_path'] for q in old + new for r in q['refs']}
    assert set((REPO/'refs/new').glob('*.csv')) == {REPO/r['result_path'] for q in new for r in q['refs']}
    # The 600-case runner may omit sensitivity, never change verdicts/reasons.
    from check_rules_impact import verdict_only
    from harness.scorer import ExecError, score_detailed
    simple={'ordered':False,'top_n':None,'tie_columns':[],'value_kinds':['other','count'],'value_types':['String','UInt64']}
    matrices=[[],[['a',1]],[['a',2]],[['b',1]],[['a',1],['a',1]],[['a',None]],[['a',1],['b',2]]]
    for candidate in matrices:
        for reference in matrices:
            expected=score_detailed(candidate,[reference],simple)
            actual=verdict_only(candidate,[reference],simple)
            assert (actual.outcome,actual.reason,actual.matched_ref)==(expected.outcome,expected.reason,expected.matched_ref)
    for candidate in [ExecError('fixture'),'__REFUSED__']:
        if isinstance(candidate,str):
            from harness.scorer import REFUSAL
            candidate=REFUSAL
        assert verdict_only(candidate,[[['a',1]]],simple).outcome==score_detailed(candidate,[[['a',1]]],simple).outcome
    winning={'ordered':False,'top_n':None,'tie_columns':[],'value_kinds':['count'],'value_types':['UInt64']}
    refs=[[['a',1]],[[2]]]
    actual=verdict_only([[2]],refs,simple,reference_rules=[None,winning])
    assert actual==score_detailed([[2]],refs,simple,reference_rules=[None,winning])
    top={'ordered':True,'top_n':1,'tie_columns':[1],'value_kinds':['other','amount'],'value_types':['String','Float64']}
    for candidate in [[['a',10]],[['b',10]],[['a',10],['b',10]],[['c',9]],[]]:
        actual=verdict_only(candidate,[[['a',10],['b',10]]],top)
        expected=score_detailed(candidate,[[['a',10],['b',10]]],top)
        assert (actual.outcome,actual.reason)==(expected.outcome,expected.reason)
    policy, _ = load_unit_policy()
    from backfill_order_keys import reference_order
    assert reference_order('SELECT round(s.amount,2) AS total_amount FROM x ORDER BY s.amount DESC',[{'name':'total_amount','type':'Float64'}])[0]==[{'column':0,'descending':True}]
    expect_error(lambda:reference_order('SELECT a FROM x ORDER BY hidden',[{'name':'a','type':'Int32'}]))
    from snapshot_q79_boundary import boundary_members, compare_members
    stored={'unit_policy_sha256':'fixture','value_kinds':['other','amount'],'rules':{'tie_columns':[1]},'rows':[['a',1.004],['b',2.001]]}
    independent={'unit_policy_sha256':'fixture','value_kinds':['other','amount'],'rows':[['b',2.002],['a',1.003]]}
    compare_members(stored,independent,policy)
    dynamic={'top_n':2,'tie_columns':[1],'value_kinds':['other','amount']}
    members,counts=boundary_members([['a',20],['b',10],['c',10],['d',5]],dynamic,policy)
    assert len(members)==3 and counts['strict_prefix_count']==1 and counts['boundary_group_count']==2
    dynamic['top_n']=1
    assert len(boundary_members([['a',20],['b',10]],dynamic,policy)[0])==1
    invalid=deepcopy(independent)
    invalid['rows'][0][0]='another-member'
    expect_error(lambda:compare_members(stored,invalid,policy))
    invalid=deepcopy(independent)
    invalid['unit_policy_sha256']='different-policy'
    expect_error(lambda:compare_members(stored,invalid,policy))
    domain_meta = [{'name': n, 'type': t} for n,t in [('ProductKey','Int32'),('base_sales','Float64'),('sales_amount','Float64'),('total_sales','Float64'),('share_pct','Nullable(Float64)')]]
    domain = [[1,10.004,10,100,10],[2,10.005,20,100,20],[3,20,30,100,30],[4,20.004,40,100,40]]
    meta, selected, details = postprocess_reference('baseline_top_decile',domain_meta,domain,policy)
    assert selected == [[70,70.0]] and set(details['selected_product_keys']) == {3,4}
    assert [c['name'] for c in meta] == ['sales_amount','share_pct']
    rank_meta = [{'name': n, 'type': t} for n,t in [('StoreKey','Int32'),('StoreName','String'),('ProductKey','Int32'),('ProductName','String'),('product_sales','Float64'),('global_sales','Float64'),('global_rank','UInt64')]]
    rank_domain = [[1,'s1',1,'a',60,100.004,0],[1,'s1',2,'b',50,100.005,0],[2,'s2',1,'a',40,100.004,0],[2,'s2',3,'c',30,90,0]]
    for method, expected in [('competition',{1:1,2:1,3:3}),('dense',{1:1,2:1,3:2})]:
        _, ranked, _ = postprocess_reference('product_rank_'+method,rank_meta,rank_domain,policy)
        assert {r[2]:r[-1] for r in ranked} == expected
    expect_error(lambda: postprocess_reference('product_rank_dense',rank_meta,rank_domain+[[3,'s3',1,'a',1,100.02,0]],policy))
    draft = (REPO / 'audit/T05-rewrite-draft.md').read_text()
    approved = {f'Q{m[1]}':m[2] for m in re.finditer(r'\| D\d+→Q(\d+) \| ([^|]+?) \|',draft)}
    rewrite_path=REPO/'audit/T05-degeneracy-rewrites.json'
    rewrites=json.loads(rewrite_path.read_text()) if rewrite_path.exists() else None
    changed={r['question_id']:r for r in rewrites['records'] if r['changed']} if rewrites else {}
    corrections_path=REPO/'audit/T05b-reference-corrections.json'
    corrections=json.loads(corrections_path.read_text()) if corrections_path.exists() else None
    text_changes={r['question_id']:r for r in corrections['records'] if r['text_changed']} if corrections else {}
    policy_path=REPO/'audit/2026-10-17-single-policy-review.json'
    single_policy=json.loads(policy_path.read_text()) if policy_path.exists() else None
    gap_ruling_path=REPO/'audit/2026-10-17-gap-ruling-review.json'
    gap_ruling=json.loads(gap_ruling_path.read_text()) if gap_ruling_path.exists() else None
    policy_text={r['question_id']:r for r in single_policy['question_text_review']} if single_policy else {}
    assert len(approved)==22
    for q in new:
        expected=changed[q['id']]['new_question'] if q['id'] in changed else approved[q['id']]
        if q['id'] in text_changes:
            assert text_changes[q['id']]['old_text_zh']==expected
            expected=text_changes[q['id']]['new_text_zh']
        if q['id'] in policy_text:
            assert policy_text[q['id']]['old_text_zh']==expected
            expected=policy_text[q['id']]['new_text_zh']
        summary_rewrites={r['question_id']:r for r in gap_ruling.get('summary_rewrites',[])} if gap_ruling else {}
        if q['id'] in summary_rewrites:
            assert summary_rewrites[q['id']]['old_text_zh']==expected
            expected=summary_rewrites[q['id']]['new_text_zh']
        if q['id']=='Q122' and gap_ruling and gap_ruling.get('q122_topn'):
            assert gap_ruling['q122_topn']['old_text_zh']==expected
            expected=gap_ruling['q122_topn']['new_text_zh']
        if q['id'] in changed:
            assert changed[q['id']]['original_question']==approved[q['id']]
        assert q['text_zh']==expected
    assert {q['id'] for q in old+new if any(effective_rules(q,r).get('selection') for r in q['refs'])} == {'Q22','Q71','Q74','Q85','Q98','Q117','Q119'}
    purchase = json.loads((REPO/'audit/T05-purchase-events.json').read_text())
    assert purchase['scanned_questions']==122 and len(purchase['records'])==122
    assert purchase['compared_questions']==18 and purchase['different_questions']==9
    assert purchase['added_references']==9 and purchase['final_references']==148
    optional=json.loads((REPO/'audit/optional-product-group-refs.json').read_text())
    expected_total=sum(len(q['refs']) for q in old+new)
    assert len(records)==expected_total
    if rewrites:
        before=json.loads((REPO/'audit/T05-degeneracy-before.json').read_text())
        after=json.loads((REPO/'audit/T05-degeneracy-after.json').read_text())
        assert before['questions_scanned']==after['questions_scanned']==22 and not after['hits']
        assert set(before['hits'])==set(changed)==set(rewrites['rewritten_questions'])
        current_after=json.loads((REPO/gap_ruling['new_question_audit']).read_text()) if gap_ruling else json.loads((REPO/single_policy['new_question_audit']).read_text()) if single_policy else json.loads((REPO/corrections['new_question_audit']).read_text()) if corrections else after
        assert not current_after['hits'] and current_after['questions_scanned']==22
        assert current_after['question_sha256']==hashlib.sha256((REPO/'questions/new.yaml').read_bytes()).hexdigest()
        assert not rewrites['post_rewrite_audit_required'] and rewrites['after_hits']==[]
        assert rewrites['after_audit_sha256']==hashlib.sha256((REPO/'audit/T05-degeneracy-after.json').read_bytes()).hexdigest()
    else:
        assert expected_total==(optional['final_references'] if optional['applied'] else purchase['final_references'])
    if optional['applied'] and not single_policy:
        from audit_orphan_group_rows import GROUP_COLUMNS
        optional_paths={r['result_path'] for item in optional['records'] for r in item['additions']}
        optional_paths.update(path for item in optional['records'] for path in item.get('existing_optional_references',[]))
        checked=0
        for q in old+new:
            for ref in q['refs']:
                if ref['result_path'] not in optional_paths:
                    continue
                source=next(r for r in q['refs'] if r['result_path'] not in optional_paths and ref['sql'].startswith('SELECT * FROM (\n'+r['sql'].rstrip().rstrip(';')+'\n)'))
                assert effective_rules(q,ref)==effective_rules(q,source)
                assert records[ref['result_path']]['columns']==records[source['result_path']]['columns']
                with (REPO/source['result_path']).open(newline='') as stream:
                    original=list(csv.reader(stream))
                with (REPO/ref['result_path']).open(newline='') as stream:
                    named=list(csv.reader(stream))
                indices=[i for i,name in enumerate(original[0]) if name in GROUP_COLUMNS]
                assert indices and original[0]==named[0]
                expected=[row for row in original[1:] if all(row[i] not in ('\\N','') for i in indices)]
                assert Counter(map(tuple,expected))==Counter(map(tuple,named[1:])), ref['result_path']
                if effective_rules(q,ref)['ordered']:
                    assert expected==named[1:]
                checked+=1
        assert checked==optional['added_references']
    expected_different={'Q26','Q33','Q36','Q76','Q80','Q89','Q115','Q116','Q122'}
    assert {r['question_id'] for r in purchase['records'] if any(not x['quantized_equal'] for x in r['references'])}==expected_different
    for item in purchase['records']:
        for comparison in item['references']:
            if item['question_id'] not in changed and not single_policy:
                assert comparison['positive_maps_to'] in records
            if comparison['quantized_equal']:
                assert not comparison['new_reference']
    ordering=json.loads((REPO/'audit/ordered-rules-review.json').read_text())
    if single_policy:
        assert len(single_policy['extra_reference_inventory'])==43
        assert len(single_policy['question_text_review'])==122
        gap_ruling_path=REPO/'audit/2026-10-17-gap-ruling-review.json'
        gap_ruling=json.loads(gap_ruling_path.read_text()) if gap_ruling_path.exists() else None
        assert expected_total==(gap_ruling or single_policy)['final_references']
        retired={r['reference'] for r in single_policy['removed_references']}
        assert not retired.intersection(records)
        assert all(not (REPO/path).exists() for path in retired)
        assert all('购买事件=SalesQuantity>0' not in r['interpretation'] for q in old+new for r in q['refs'])
        by_id={q['id']:q for q in old+new}
        assert len(by_id['Q114']['refs'])==len(by_id['Q116']['refs'])==len(by_id['Q65']['refs'])==1
        assert '-89' in by_id['Q114']['refs'][0]['sql'] and '<=c.cutoff' in by_id['Q114']['refs'][0]['sql']
        assert by_id['Q65']['refs'][0]['result_path']=='refs/cube/Q65-2.csv'
    current_ordered={r['reference']:r for r in ordering['current_records']}
    expected_ordered={ref['result_path'] for q in old+new for ref in q['refs'] if effective_rules(q,ref)['ordered']}
    assert current_ordered.keys()==expected_ordered
    for path,item in current_ordered.items():
        assert item['order_by']==records[path]['rules']['order_by']
        assert item['columns']==records[path]['columns'] and item['sql_sha256']==records[path]['sql_sha256']
    from harness.scorer import _boundary_start, score
    from check_rules_impact import csv_rows
    def tied_prefix_swap(reference,rules):
        n=rules['top_n']
        end=n if len(reference)==n else _boundary_start(reference,n,tuple(rules['tie_columns']),tuple(rules['value_kinds']))
        key=lambda row:tuple(policy.quantize_tie(row[k['column']],rules['value_kinds'][k['column']]) for k in rules['order_by'])
        positions=[i for i in range(end-1) if key(reference[i])==key(reference[i+1]) and reference[i]!=reference[i+1]]
        if not positions:
            return False  # A corrected precise ranking may have no prefix tie.
        position=positions[0]
        candidate=deepcopy(reference[:n]);candidate[position],candidate[position+1]=candidate[position+1],candidate[position]
        assert score(candidate,[reference],rules)=='correct'
        return True
    for qid in ('Q27','Q87','Q88'):
        question=next(q for q in old if q['id']==qid);ref=question['refs'][0]
        swapped=tied_prefix_swap(csv_rows(records[ref['result_path']]),effective_rules(question,ref))
        assert swapped or (single_policy is not None and qid in single_policy['precision_questions']) or (qid=='Q27' and corrections is not None)
    from harness.questions import load_questions
    for anchor in load_questions(REPO,lang='en'):
        if anchor.qid in ('EN27','EN88'):
            tied_prefix_swap(anchor.refs[0],anchor.rules)
    warnings = []
    for q in new:
        assert q['split'] is None and q['scoring'] == 'deterministic'
        assert set(q['labels']) == set(old[0]['labels'])
        for ref in q['refs']:
            rules = effective_rules(q,ref)
            topn_q122=q['id']=='Q122' and gap_ruling and gap_ruling.get('q122_topn')
            assert rules['top_n'] == (10 if topn_q122 else None)
            assert rules['ordered'] == (q['id']=='Q117' or bool(topn_q122))
            assert has_final_order_by(ref['sql']) == rules['ordered']
            if topn_q122:
                assert re.search(r'\bLIMIT\s+10\s*$',ref['sql'],re.I)
            else:
                assert 'LIMIT' not in ref['sql'].upper()
            assert not ('FactOnlineSales' in ref['sql'] and 'FactSales ' in ref['sql'])
            if q['id'] == 'Q110':
                assert 'FactSales' in ref['sql'] and 'FactOnlineSales' not in ref['sql'] and 'DimChannel' in ref['sql']
            record = records[ref['result_path']]
            assert record['rules'] == rules
            assert record['value_kinds'] == rules['value_kinds']
            assert record['value_kind_source'] == 'declared'
            assert record['sql_sha256'] == hashlib.sha256(ref['sql'].encode()).hexdigest()
            path = REPO / ref['result_path']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
            with path.open(newline='') as stream:
                rows = list(csv.reader(stream))
            assert rows[0] == [c['name'] for c in record['columns']]
            assert len(rows)-1 == record['row_count'] >= 0
            assert [c['type'] for c in record['columns']] == rules['value_types']
            for row in rows[1:]:
                for v, typ in zip(row, rules['value_types'], strict=True):
                    if policy.is_numeric_type(typ) and v != '\\N':
                        assert math.isfinite(float(v)), (q['id'], v)
            warnings.extend(record['value_kind_warnings'])
    assert {(w['question_id'], w['column_position'], w['declared'], w['inferred']) for w in warnings} == {('Q101',1,'amount','other')}
    print(f'PASS: {len(old)+len(new)} questions, {len(records)} references; approved second round, declared kinds/types, selection domains, table policy, coverage and warning fixtures')


if __name__ == '__main__':
    main()
