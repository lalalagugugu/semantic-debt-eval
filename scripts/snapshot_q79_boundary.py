#!/usr/bin/env python
"""Save the published Q79 boundary; gate freezing on T05b member equality."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path

from build_refs import load_unit_policy
from check_q79_membership import member_counts

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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--freeze-check', action='store_true')
    parser.add_argument('--independent-snapshot', type=Path)
    args = parser.parse_args()
    policy, policy_hash = load_unit_policy()
    if args.freeze_check:
        stored = json.loads(SNAPSHOT.read_text())
        if stored['unit_policy_sha256'] != policy_hash:
            raise ValueError('stored boundary uses another unit policy')
        if args.independent_snapshot is None:
            raise SystemExit('BLOCKED: T05b independent pandas boundary snapshot required')
        independent = json.loads(args.independent_snapshot.read_text())
        if independent['question_id'] != 79 or len(independent['rows']) != 306:
            raise ValueError('expected independent Q79 boundary with 306 members')
        compare_members(stored, independent, policy)
        print('PASS: T05b Q79 member multiset reproduced; raw hashes are not compared')
        return

    main_dir = Path(os.environ['SEMDEBT_MAIN_DIR'])
    spec = importlib.util.spec_from_file_location('q79_current_adapter', main_dir / 'scripts/validate_scorer.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    benchmark = ROOT / 'vendor/cube/text_to_sql_benchmark.json'
    question = next(q for q in json.loads(benchmark.read_text())['questions'] if int(q['id']) == 79)
    from chdb import session
    sess = adapter.open_session(session, Path(os.environ['SEMDEBT_DATA_DIR']) / 'chdb-eval')
    try:
        rules = adapter.question_rules(79, question['expected_sql'])
        rows, check, _ = adapter.stable_reference(sess, question['expected_sql'], 79, rules)
    finally:
        sess.close()
    if len(rows) != 306 or len(Counter(row[0] for row in rows)) != 306:
        raise ValueError('expected 306 distinct Q79 boundary members')
    snapshot = {
        'question_id': 79,
        'scope': 'published_reference_boundary',
        'unit_policy_sha256': policy_hash,
        'boundary_policy_sha256': hashlib.sha256((main_dir / 'scripts/validate_scorer.py').read_bytes()).hexdigest(),
        'sql_sha256': hashlib.sha256(question['expected_sql'].encode()).hexdigest(),
        'serialization_version': 'json-compact-utf8-v1',
        'columns': rules['reference_columns'],
        'value_kinds': rules['value_kinds'],
        'row_count': len(rows),
        'sha256': check['sha256'],
        'rows': rows,
    }
    if args.check:
        stored = json.loads(SNAPSHOT.read_text())
        compare_members(stored, snapshot, policy)
        print('PASS: current Q79 snapshot, 306 members; T05b freeze gate still pending')
    else:
        SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
        print(f'Saved 306 Q79 members; unit policy {policy_hash}; T05b freeze gate pending')


if __name__ == '__main__':
    main()
