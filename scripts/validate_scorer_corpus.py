"""Synthetic codec checks and optional exported-corpus readback; no SQL execution."""
import argparse
import datetime as dt
from decimal import Decimal
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path
import tempfile
from scorer_corpus import encode, read_corpus


def fixtures():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'cases.jsonl'
        values = [[dt.date(2008, 1, 1), dt.datetime(2008, 1, 1),
                   dt.datetime.fromisoformat('2008-01-01T12:30:00+08:00'), Decimal('1.230000000000000000001'),
                   float('nan'), float('inf'), -float('inf'), None, '', 'NaN', '2008-01-01']]
        cases = [{'candidate': values, 'refs': [values, []], 'rules': [{}, {}], 'value_types': [[], []]},
                 {'candidate': 'CANNOT_ANSWER'}, {'candidate': {'exec_error': '原始报错\nline 2'}}, {'candidate': []}]
        path.write_text(''.join(json.dumps(encode(c), allow_nan=False, ensure_ascii=False) + '\n' for c in cases))
        restored = list(read_corpus(path))
        row = restored[0]['candidate'][0]
        assert row[:4] == values[0][:4]
        assert type(row[0]) is dt.date and type(row[1]) is dt.datetime
        assert math.isnan(row[4]) and row[5:7] == values[0][5:7]
        assert row[7:] == values[0][7:]
        assert restored[1:] == cases[1:]
        assert restored[0]['refs'][1] == []
        path.write_text('{"candidate":NaN}\n')
        try:
            list(read_corpus(path))
        except ValueError:
            pass
        else:
            raise AssertionError('Bare NaN accepted')


def check(path):
    seen, errors = set(), 0
    for case in read_corpus(path):
        assert set(case) == {'case_id', 'source', 'question_id', 'system', 'candidate', 'refs', 'rules', 'value_types', 'external_verdict', 'judge', 'bank'}
        assert case['source'] == 'ext600' and case['case_id'] not in seen
        seen.add(case['case_id'])
        assert len(case['refs']) == len(case['rules']) == len(case['value_types'])
        for rows, rule, types in zip(case['refs'], case['rules'], case['value_types'], strict=True):
            assert types == rule['value_types']
            assert all(len(row) == len(types) for row in rows)
        candidate = case['candidate']
        if isinstance(candidate, dict):
            assert set(candidate) == {'exec_error'} and isinstance(candidate['exec_error'], str)
            errors += 1
        else:
            assert isinstance(candidate, list) or candidate == 'CANNOT_ANSWER'
        assert case['external_verdict'] in ('pass', 'fail', 'excluded')
    assert len(seen) == 600
    return {'cases': len(seen), 'exec_errors': errors}


def check_main_loader(path, cache):
    sys.path.insert(0, os.environ['SEMDEBT_MAIN_DIR'])
    from harness.scorer_corpus import load_corpus, encode_value
    from harness.scorer import ExecError
    cases = load_corpus(path)
    assert len(cases) == 600 and len({c['case_id'] for c in cases}) == 600
    assert sum(c['judge'] for c in cases) == 78
    assert len({c['system'] for c in cases}) == 6
    assert all(n == 100 for n in Counter(c['system'] for c in cases).values())
    with cache.open() as stream:
        for case, line in zip(cases, stream, strict=True):
            original = json.loads(line)
            assert case['system'] == original['system']
            assert int(case['question_id'][1:]) == original['question_id']
            if original['error'] is not None:
                assert isinstance(case['candidate'], ExecError)
                assert case['candidate'].message == original['error']
            else:
                assert encode_value(case['candidate']) == encode_value(original['rows'])
    return {'load_corpus': 'passed', 'cached_candidates_identical': len(cases),
            'judge': sum(c['judge'] for c in cases)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path)
    parser.add_argument('--cache', type=Path, help='Also verify with PR #105 load_corpus and compare original cached candidates')
    args = parser.parse_args()
    if args.cache and not args.corpus:
        parser.error('--cache requires --corpus')
    fixtures()
    print({'fixtures': 'passed', **(check(args.corpus) if args.corpus else {}),
           **(check_main_loader(args.corpus, args.cache) if args.cache else {})})
