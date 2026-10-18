"""Audit frozen selection identities without changing question rules."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import yaml
from scorer_corpus import read_reference

ROOT = Path(__file__).resolve().parents[1]


def norm(value):
    return value.strip() if isinstance(value, str) else value


def bijection(rows, key, name):
    forward, reverse = defaultdict(set), defaultdict(set)
    for row in rows:
        forward[norm(row[key])].add(norm(row[name]))
        reverse[norm(row[name])].add(norm(row[key]))
    return {'key_distinct': len(forward), 'name_distinct': len(reverse),
            'key_collisions': sum(len(x) > 1 for x in forward.values()),
            'name_collisions': sum(len(x) > 1 for x in reverse.values()),
            'blank_name_rows': sum(norm(row[name]) in (None, '') for row in rows),
            'bijective': all(len(x) == 1 for x in forward.values()) and all(len(x) == 1 for x in reverse.values())}


def scan():
    records = {r['result_path']: r for r in json.loads((ROOT / 'refs/MANIFEST.json').read_text())['records']}
    results, total, selected = [], 0, 0
    for filename in ('cube_100.yaml', 'new.yaml'):
        for q in yaml.safe_load((ROOT / 'questions' / filename).read_text())['questions']:
            for ref in q['refs']:
                total += 1
                rule = ref.get('rules', q['rules'])
                selection = rule.get('selection')
                if not selection:
                    continue
                selected += 1
                required = rule.get('required_columns', list(range(len(rule['value_types']))))
                meta = records[ref['result_path']]
                path = ROOT / ref['result_path']
                assert hashlib.sha256(path.read_bytes()).hexdigest() == meta['sha256']
                rows = read_reference(path, rule['value_types'])
                missing = []
                for i, stage in enumerate(selection['stages']):
                    for field in ('group_columns', 'object_columns'):
                        for col in stage.get(field, []):
                            if col not in required:
                                candidates = []
                                for name in required:
                                    if 'String' in rule['value_types'][name]:
                                        candidates.append({'column': name, 'name': meta['columns'][name]['name'], **bijection(rows, col, name)})
                                missing.append({'stage': i, 'field': field, 'column': col,
                                                'name': meta['columns'][col]['name'], 'required_name_checks': candidates})
                if missing:
                    results.append({'question_id': q['id'], 'reference': ref['result_path'], 'rows': len(rows),
                                    'required_columns': required, 'missing': missing})
    return {'baseline_commit': subprocess.check_output(['git', 'rev-parse', 'eval-v1.1^{}'], cwd=ROOT, text=True).strip(),
            'question_files_sha256': {name: hashlib.sha256((ROOT / 'questions' / name).read_bytes()).hexdigest() for name in ('cube_100.yaml', 'new.yaml')},
            'reference_count': total, 'selected_reference_count': selected,
            'noncompliant_question_count': len({r['question_id'] for r in results}),
            'noncompliant_reference_count': len(results), 'references': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(scan(), ensure_ascii=False, indent=2) + '\n')
