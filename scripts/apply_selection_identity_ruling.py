"""Apply PR #106's approved metadata revision; never execute SQL or rewrite CSVs."""
from copy import deepcopy
import hashlib
import json
import subprocess
from pathlib import Path
from audit_selection_identities import bijection
from scorer_corpus import read_reference
from reference_presentation import ranking_domains

ROOT = Path(__file__).resolve().parents[1]
REPLACEMENTS = {'refs/cube/Q74-1.csv': {4: 1}, 'refs/new/Q117-1.csv': {0: 1},
                'refs/new/Q119-1.csv': {0: 1, 2: 3}}
REQUIRED = {'refs/cube/Q98-1.csv': 2, 'refs/cube/Q98-2.csv': 3}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def rule_summary(rule):
    return {'selection': rule['selection'], 'required_columns': rule['required_columns'],
            'rankings': [{**{k: v for k, v in rank.items() if k != 'blocks'},
                          'block_count': len(rank['blocks']), 'blocks_sha256': digest(rank['blocks'])}
                         for rank in rule.get('rankings', [])]}


def main():
    for name in ('questions/cube_100.yaml', 'questions/new.yaml', 'refs/MANIFEST.json', 'refs/PRESENTATION.json'):
        baseline = subprocess.check_output(['git', 'show', f'eval-v1.1:{name}'], cwd=ROOT)
        if (ROOT / name).read_bytes() != baseline:
            raise ValueError('Apply only to unchanged eval-v1.1 metadata: ' + name)
    manifest_path = ROOT / 'refs/MANIFEST.json'
    manifest = json.loads(manifest_path.read_text())
    records = {r['result_path']: r for r in manifest['records']}
    presentation_path = ROOT / 'refs/PRESENTATION.json'
    presentation = json.loads(presentation_path.read_text())
    changes = []
    for filename in ('cube_100.yaml', 'new.yaml'):
        path = ROOT / 'questions' / filename
        data = json.loads(path.read_text())
        for question in data['questions']:
            old_rules = question['rules']
            effective = []
            for ref in question['refs']:
                rule = deepcopy(ref.get('rules', old_rules))
                reference = ref['result_path']
                if reference in REPLACEMENTS or reference in REQUIRED:
                    record = records[reference]
                    before = deepcopy(rule)
                    rows = read_reference(ROOT / reference, rule['value_types'])
                    assert hashlib.sha256((ROOT / reference).read_bytes()).hexdigest() == record['sha256']
                    replacements = REPLACEMENTS.get(reference, {})
                    mappings = {}
                    for key, name in replacements.items():
                        check = bijection(rows, key, name)
                        assert name in rule['required_columns'] and check['bijective'] and not check['blank_name_rows']
                        mappings[key] = {row[key]: row[name] for row in rows}
                    def replace_columns(item):
                        old_groups = item['group_columns'][:]
                        item['group_columns'] = [replacements.get(c, c) for c in old_groups]
                        item['object_columns'] = [replacements.get(c, c) for c in item['object_columns']]
                        return old_groups
                    for i, stage in enumerate(rule['selection']['stages']):
                        groups = replace_columns(stage)
                        for check in record['selection_checks'][i]:
                            check['group'] = [mappings[c][v] if c in mappings else v for c, v in zip(groups, check['group'], strict=True)]
                    for rank in rule.get('rankings', []):
                        groups = replace_columns(rank)
                        for block in rank['blocks']:
                            block['group'] = [mappings[c][v] if c in mappings else v for c, v in zip(groups, block['group'], strict=True)]
                    display = presentation['references'][reference]
                    for rank in display.get('ranks', []) + display.get('existing_ranks', []):
                        replace_columns(rank)
                    if reference in REQUIRED:
                        rule['required_columns'] = sorted(set(rule['required_columns'] + [REQUIRED[reference]]))
                        presentation['overrides'][reference] = rule['required_columns'][:]
                    rule['rankings'] = ranking_domains(record['columns'], rows, display,
                        population_blocks=(record.get('postprocess_details') or {}).get('rank_blocks'))
                    record['rules'] = deepcopy(rule)
                    record['presentation_sha256'] = digest(display)
                    changes.append({'question_id': question['id'], 'reference': reference,
                                    'before': rule_summary(before), 'after': rule_summary(rule),
                                    'csv_sha256_unchanged': record['sha256'], 'sql_sha256_unchanged': record['sql_sha256']})
                effective.append(rule)
            question['rules'] = effective[0]
            for ref, rule in zip(question['refs'], effective, strict=True):
                if rule == question['rules']:
                    ref.pop('rules', None)
                else:
                    ref['rules'] = rule
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    presentation_path.write_text(json.dumps(presentation, ensure_ascii=False, indent=2) + '\n')
    manifest['presentation_sha256'] = hashlib.sha256(presentation_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'audit/2026-10-19-selection-identity-changes.json').write_text(json.dumps(
        {'ruling': 'semantic-debt PR #106; scorer spec v2 section IX', 'target': 'eval-v1.2',
         'reference_count': len(records), 'changes': changes}, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
