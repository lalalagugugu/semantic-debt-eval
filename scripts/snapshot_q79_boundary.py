#!/usr/bin/env python
"""Snapshot the current Q79 boundary and require independent member equality."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

from build_refs import effective_rules, load_unit_policy
from check_q79_membership import member_counts
from check_rules_impact import csv_rows

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / 'audit/Q79-boundary-members.json'


def compare_members(stored, independent, policy):
    if stored['unit_policy_sha256'] != independent['unit_policy_sha256']:
        raise ValueError('unit policy versions differ')
    if stored['value_kinds'] != independent['value_kinds']:
        raise ValueError('boundary column kinds differ')
    expected = member_counts(stored['rows'], stored['value_kinds'], policy)
    actual = member_counts(independent['rows'], independent['value_kinds'], policy)
    if expected != actual:
        raise ValueError(f'boundary members differ: removed={sum((expected-actual).values())}, added={sum((actual-expected).values())}')


def current_reference():
    question = next(q for q in json.loads((ROOT/'questions/cube_100.yaml').read_text())['questions'] if q['id']=='Q79')
    if len(question['refs']) != 1:
        raise ValueError('Q79 snapshot needs one unambiguous current reference')
    ref = question['refs'][0]
    record = next(r for r in json.loads((ROOT/'refs/MANIFEST.json').read_text())['records'] if r['result_path']==ref['result_path'])
    rules = effective_rules(question,ref)
    if record['sql_sha256']!=hashlib.sha256(ref['sql'].encode()).hexdigest() or record['sha256']!=hashlib.sha256((ROOT/ref['result_path']).read_bytes()).hexdigest() or record['rules']!=rules:
        raise ValueError('current Q79 reference/manifest is stale; rebuild first')
    return ref,record,rules


def boundary_members(rows, rules, policy, descending=True):
    n=rules['top_n']
    if not n or not rules['tie_columns'] or len(rows)<n:
        raise ValueError('current Q79 reference must contain its declared Top-N')
    key=lambda row:tuple(policy.quantize_tie(row[i],rules['value_kinds'][i]) for i in rules['tie_columns'])
    ordered=sorted(rows,key=lambda row:json.dumps(row,ensure_ascii=False,default=str))
    ordered.sort(key=key,reverse=descending)
    nth=key(ordered[n-1])
    prefix=[row for row in ordered if key(row)>nth] if descending else [row for row in ordered if key(row)<nth]
    ties=[row for row in ordered if key(row)==nth]
    return prefix+ties,{'strict_prefix_count':len(prefix),'boundary_group_count':len(ties),'nth_quantized_key':[str(v) for v in nth]}


def make_snapshot(ref, record, rules, rows, policy, policy_hash):
    descending=not bool(re.search(r'\bASC\s*(?:LIMIT\s+\d+)?\s*;?\s*$',ref['sql'],re.I))
    rows,details=boundary_members(rows,rules,policy,descending)
    if len(Counter(row[0] for row in rows))!=len(rows):
        raise ValueError('current Q79 boundary contains duplicate store identities')
    return {'question_id':79,'scope':'current_reference_boundary','unit_policy_sha256':policy_hash,
            'sql_sha256':record['sql_sha256'],'reference_sha256':record['sha256'],
            'serialization_version':'json-compact-utf8-v1','columns':record['columns'],
            'rules':rules,'rules_sha256':hashlib.sha256(json.dumps(rules,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'value_kinds':rules['value_kinds'],'row_count':len(rows),**details,'rows':rows}


def check_current(stored, current, policy):
    for field in ['question_id','scope','unit_policy_sha256','sql_sha256','reference_sha256','rules','rules_sha256','columns','row_count','strict_prefix_count','boundary_group_count','nth_quantized_key']:
        if stored[field]!=current[field]:
            raise ValueError('snapshot is not the current Q79 reference: '+field)
    if stored['row_count']!=len(stored['rows']):
        raise ValueError('snapshot row count is stale')
    compare_members(current,stored,policy)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--freeze-check',action='store_true')
    parser.add_argument('--independent-snapshot',type=Path)
    args=parser.parse_args()
    policy,policy_hash=load_unit_policy()
    ref,record,rules=current_reference()
    from_csv=make_snapshot(ref,record,rules,csv_rows(record),policy,policy_hash)
    if args.freeze_check:
        stored=json.loads(SNAPSHOT.read_text())
        check_current(stored,from_csv,policy)
        if args.independent_snapshot is None:
            raise SystemExit('BLOCKED: T05b independent pandas boundary snapshot required')
        independent=json.loads(args.independent_snapshot.read_text())
        if independent['question_id']!=stored['question_id']:
            raise ValueError('independent snapshot is not Q79')
        compare_members(stored,independent,policy)
        print(f"PASS: T05b Q79 current boundary reproduced: {from_csv['row_count']} members; raw hashes are not compared")
        return
    main_dir=Path(os.environ['SEMDEBT_MAIN_DIR'])
    spec=importlib.util.spec_from_file_location('q79_current_adapter',main_dir/'scripts/validate_scorer.py')
    adapter=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    from chdb import session
    sess=adapter.open_session(session,Path(os.environ['SEMDEBT_DATA_DIR'])/'chdb-eval')
    try:
        sql,count=re.subn(rf"\bLIMIT\s+{rules['top_n']}\s*;?\s*$",'',ref['sql'],flags=re.I)
        if count!=1:
            raise ValueError('cannot expand current Q79 ranking domain')
        payload=json.loads(str(sess.query(sql,'JSONCompact')))
    finally:
        sess.close()
    if payload['meta']!=record['columns']:
        raise ValueError('current Q79 query metadata changed')
    current=make_snapshot(ref,record,rules,payload['data'],policy,policy_hash)
    compare_members(from_csv,current,policy)
    if args.check:
        check_current(json.loads(SNAPSHOT.read_text()),current,policy)
        print(f"PASS: current Q79 snapshot, {current['row_count']} members; independent freeze gate pending")
    else:
        SNAPSHOT.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
        print(f"Saved current Q79: {current['strict_prefix_count']} strict prefix + {current['boundary_group_count']} tied = {current['row_count']} members; rule version {policy_hash}")


if __name__=='__main__':
    main()
