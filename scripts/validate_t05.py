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

import yaml

from build_refs import has_final_order_by, load_unit_policy, reference_value_kinds, validate_questions

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
    sample['rules']['ordered'] = True
    expect_error(lambda: validate_questions([sample], 'new'))
    sample = deepcopy(new[0])
    del sample['rules']['value_kinds']
    expect_error(lambda: validate_questions([sample], 'new'))
    sample = deepcopy(new[0])
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
    policy, _ = load_unit_policy()
    warnings = []
    for q in new:
        assert q['split'] is None and q['scoring'] == 'deterministic'
        assert set(q['labels']) == set(old[0]['labels'])
        for ref in q['refs']:
            assert not q['rules']['ordered'] and q['rules']['top_n'] is None
            assert not has_final_order_by(ref['sql'])
            assert 'LIMIT' not in ref['sql'].upper()
            assert not ('FactOnlineSales' in ref['sql'] and 'FactSales ' in ref['sql'])
            assert 'DimChannel' not in ref['sql']
            record = records[ref['result_path']]
            assert record['rules'] == q['rules']
            assert record['value_kinds'] == q['rules']['value_kinds']
            assert record['value_kind_source'] == 'declared'
            assert record['sql_sha256'] == hashlib.sha256(ref['sql'].encode()).hexdigest()
            path = REPO / ref['result_path']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
            with path.open(newline='') as stream:
                rows = list(csv.reader(stream))
            assert rows[0] == [c['name'] for c in record['columns']]
            assert len(rows)-1 == record['row_count'] > 0
            assert [c['type'] for c in record['columns']] == q['rules']['value_types']
            for row in rows[1:]:
                for v, typ in zip(row, q['rules']['value_types'], strict=True):
                    if policy.is_numeric_type(typ) and v != '\\N':
                        assert math.isfinite(float(v)), (q['id'], v)
            warnings.extend(record['value_kind_warnings'])
    assert {(w['question_id'], w['column_position'], w['declared'], w['inferred']) for w in warnings} == {('Q101',1,'amount','other'),('Q102',2,'amount','other')}
    print(f'PASS: {len(old)+len(new)} questions, {len(records)} references; declared kinds/types, unordered rows, table policy, coverage and warning fixtures')


if __name__ == '__main__':
    main()
