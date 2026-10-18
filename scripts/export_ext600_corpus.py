"""Export cached executions only; no SQL execution or scoring."""
import argparse
import csv
import io
import os
import sys
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import yaml
from scorer_corpus import encode

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '938957f4281ddc63ba699bf15d91dcde6b71ddf0'


def frozen(path):
    return subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'], cwd=ROOT)


def reference(path, columns, parse_value):
    reader = csv.reader(io.StringIO(frozen(path).decode()))
    assert next(reader) == [c['name'] for c in columns]
    return [[parse_value(v, c['type']) for v, c in zip(row, columns, strict=True)] for row in reader]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def export(cache, output):
    sys.path.insert(0, os.environ['SEMDEBT_MAIN_DIR'])
    from harness.questions import parse_value
    if sha(cache) != 'f629285de6f00f423443e45985f9eb171ee72cbbe634c8f987e27e54428f2213':
        raise ValueError('Expected the first finalized ext600 execution cache')
    questions = yaml.safe_load(frozen('questions/cube_100.yaml'))['questions']
    records = {r['result_path']: r for r in json.loads(frozen('refs/MANIFEST.json'))['records']}
    refs = {}
    judges = []
    for q in questions:
        number = int(q['id'][1:])
        if q['scoring'] == 'judge':
            judges.append(q['id'])
        rules = [ref.get('rules', q['rules']) for ref in q['refs']]
        types = [rule['value_types'] for rule in rules]
        rows = []
        for ref, rule in zip(q['refs'], rules, strict=True):
            meta = records[ref['result_path']]
            assert meta['rules'] == rule
            assert hashlib.sha256(frozen(ref['result_path'])).hexdigest() == meta['sha256']
            rows.append(reference(ref['result_path'], meta['columns'], parse_value))
        refs[number] = (rows, rules, types)
    seen, systems, counts = set(), Counter(), Counter()
    temporary = output.with_suffix('.jsonl.tmp')
    if output.exists() or temporary.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    verdict_hash = hashlib.sha256()
    try:
        with cache.open() as source, temporary.open('x', encoding='utf-8') as dest:
            for line in source:
                record = json.loads(line)
                system, qid = record['system'], record['question_id']
                identity = (system, qid)
                if identity in seen:
                    raise ValueError(f'Duplicate case: {identity}')
                seen.add(identity)
                systems[system] += 1
                if record['error'] is not None:
                    candidate = {'exec_error': record['error']}
                    counts['exec_error'] += 1
                else:
                    candidate = record['rows']
                    if not isinstance(candidate, list) and candidate != 'CANNOT_ANSWER':
                        raise ValueError(f'Invalid cached candidate: {identity}')
                    counts['cannot_answer' if candidate == 'CANNOT_ANSWER' else 'rows'] += 1
                verdict_path = ROOT / 'vendor/cube/published-runs/paper-2026-04-22/scoring' / system / f'q{qid:02d}.json'
                raw = frozen(str(verdict_path.relative_to(ROOT)))
                verdict_hash.update(str(verdict_path.relative_to(ROOT)).encode() + b'\0' + raw)
                verdict = json.loads(raw)['verdict']
                rows, rules, types = refs[qid]
                case = {'case_id': f'ext600:{system}:Q{qid:02d}', 'source': 'ext600',
                        'question_id': f'Q{qid:02d}', 'system': system, 'candidate': candidate,
                        'judge': f'Q{qid:02d}' in judges, 'bank': 'eval-v1.1@938957f',
                        'refs': rows, 'rules': rules, 'value_types': types, 'external_verdict': verdict}
                dest.write(json.dumps(encode(case), ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n')
        if len(seen) != 600 or len(systems) != 6 or any(n != 100 for n in systems.values()):
            raise ValueError(f'Incomplete corpus: {len(seen)}, {systems}')
        for system in systems:
            assert {qid for s, qid in seen if s == system} == set(range(1, 101))
        temporary.rename(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    summary = {'cases': len(seen), 'source': 'ext600', 'baseline': 'eval-v1.1',
                'baseline_commit': BASELINE,
                'execution_cache': str(cache), 'execution_cache_sha256': sha(cache),
                'corpus_sha256': sha(output), 'verdict_files_sha256': verdict_hash.hexdigest(),
                'candidate_counts': dict(counts), 'systems': dict(systems),
                'value_types_layout': 'per reference, aligned with refs and rules',
                'judge_example_questions': judges, 'judge_example_cases': len(judges) * 6,
                'judge_warning': 'Judge references are examples, not closed-set gold answers.',
                'cached_cell_policy': 'Preserve cached JSON primitives; do not infer dates from candidate strings.'}
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.cache, args.output), ensure_ascii=False, indent=2))
