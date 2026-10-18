"""Check approved metadata, selection membership and ranking blocks; no SQL."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ['SEMDEBT_MAIN_DIR'])
from harness.selection import complete_selection
from reference_presentation import ranking_domains
from scorer_corpus import read_reference


def main():
    baseline = json.loads(subprocess.check_output(
        ['git', 'show', 'eval-v1.1:refs/MANIFEST.json'], cwd=ROOT))
    old = {r['result_path']: r for r in baseline['records']}
    manifest = json.loads((ROOT / 'refs/MANIFEST.json').read_text())
    presentation = json.loads((ROOT / 'refs/PRESENTATION.json').read_text())
    changed = {'refs/cube/Q74-1.csv', 'refs/cube/Q98-1.csv', 'refs/cube/Q98-2.csv',
               'refs/new/Q117-1.csv', 'refs/new/Q119-1.csv'}
    assert len(manifest['records']) == len(old) == 137
    for record in manifest['records']:
        previous = old[record['result_path']]
        path = ROOT / record['result_path']
        assert record['sha256'] == previous['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert record['sql_sha256'] == previous['sql_sha256']
        if record['result_path'] not in changed:
            assert record == previous
            continue
        rules = record['rules']
        rows = read_reference(path, rules['value_types'])
        selected, _ = complete_selection(rows, rules['selection'], rules['value_kinds'])
        assert selected == rows, record['question_id']
        population = (record.get('postprocess_details') or {}).get('rank_blocks')
        rankings = ranking_domains(record['columns'], rows,
            presentation['references'][record['result_path']], population_blocks=population)
        assert rankings == rules['rankings'], record['question_id']
        for current, prior in zip(record['selection_checks'], previous['selection_checks'], strict=True):
            assert [{k: v for k, v in c.items() if k != 'group'} for c in current] == [
                {k: v for k, v in c.items() if k != 'group'} for c in prior]
    scan = json.loads((ROOT / 'audit/2026-10-19-selection-identities-after.json').read_text())
    assert scan['noncompliant_reference_count'] == 0
    print('PASS: 137 CSV/SQL hashes unchanged; only approved 5 metadata records changed; '
          'selection membership and ranking blocks preserved')


if __name__ == '__main__':
    main()
