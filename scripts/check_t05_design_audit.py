#!/usr/bin/env python
"""Validate design-audit bookkeeping, not SQL correctness or semantic novelty.

Reads only conventions.md in the main repo. No database or model calls.
An exit code of zero means consistent records, NOT acceptance of T05.
"""
from collections import Counter
from hashlib import sha256
from itertools import combinations
import json
import os
from pathlib import Path
import re


def require(condition, message):
    if not condition:
        raise SystemExit(f'INVALID AUDIT: {message}')


def signature(question):
    # IDs, question wording and literal parameters never identify a design.
    return question['structural_signature']


def main():
    root = Path(__file__).resolve().parent.parent
    main_dir = os.environ.get('SEMDEBT_MAIN_DIR')
    require(main_dir, 'SEMDEBT_MAIN_DIR must be set')
    audit = json.loads((root / 'audit/T05-self-check.json').read_text())
    source = audit['source']
    for path, expected in [
        (root / source['draft_path'], source['draft_sha256']),
        (root / source['cube_path'], source['cube_sha256']),
        (Path(main_dir) / 'semantic/conventions.md', source['conventions_sha256']),
    ]:
        require(sha256(path.read_bytes()).hexdigest() == expected,
                f'source changed; re-audit {path.name}')

    draft = (root / source['draft_path']).read_text()
    rows = re.findall(r'^\| (D\d{2})→(Q\d{3}) \| ([^|]+) \| ([^|]+) \|$',
                      draft, re.MULTILINE)
    require(len(rows) == 22, 'expected 22 second-round draft questions')
    expected_text = {qid: (did, text.strip()) for did, qid, text, _ in rows}
    questions = audit['questions']
    by_id = {q['id']: q for q in questions}
    require(len(questions) == len(by_id) == 22, 'duplicate or missing question')
    require(set(by_id) == {f'Q{n}' for n in range(101, 123)}, 'wrong IDs')
    cube = json.loads((root / source['cube_path']).read_text())
    existing_ids = {q['id'] for q in cube['questions']}
    fields = ('source_semantics', 'grain_flow', 'operators', 'measure_semantics',
              'scope_roles', 'temporal_flow')
    categories = ('required_unstated', 'explicit_in_prompt', 'partial', 'background_only')
    for q in questions:
        qid = q['id']
        require((q['design_id'], q['text_zh']) == expected_text[qid], f'{qid}: draft mismatch')
        require(q['analysis_stage'] == 'design_only_not_SQL_verified', f'{qid}: false SQL claim')
        require(q['coverage_delta'] and q['structural_rationale'], f'{qid}: missing rationale')
        require(set(q['nearest_existing_questions']) <= existing_ids, f'{qid}: unknown witness')
        require(tuple(signature(q)) == fields, f'{qid}: unexpected signature fields')
        for category in categories:
            items = q['conventions'][category]
            ids = [p['id'] for p in items] if category == 'partial' else items
            require(len(ids) == len(set(ids)) and set(ids) <= set(range(1, 16)),
                    f'{qid}: invalid convention IDs in {category}')
        structure = q['structure']
        require(type(structure['estimated_min_dimension_join_depth']) is int
                and structure['estimated_min_dimension_join_depth'] >= 0,
                f'{qid}: invalid estimated depth')
        require(structure['dedup_count'] in {'required', 'conditional', 'not_required'},
                f'{qid}: invalid dedup label')
        require(type(structure['staged_logic']) is bool and structure['time_window_types'],
                f'{qid}: missing structural label')
        require(q['summary_coverage'] == {
            'status': 'blocked_pre_G1', 'evidence': None, 'matched_interpretation': None,
        }, f'{qid}: unsupported summary coverage claim')
        require(q['metric_callability'] == {
            'status': 'blocked_pre_G1', 'metric_ids': [], 'interface_evidence': None,
        }, f'{qid}: unsupported metrics claim')

    # Regression fixture: changing question ID/text alone cannot avoid a collision.
    renamed = dict(questions[0], id='different_id', text_zh='different entity and year')
    require(signature(renamed) == signature(questions[0]), 'literal substitution bypass')
    conventions = audit['convention_coverage']
    require([c['id'] for c in conventions] == list(range(1, 16)), 'expected 15 conventions')
    backlinks = dict(zip(categories, ('new_required_unstated', 'new_prompt_disclosed',
                                      'new_partial', 'new_background_only')))
    for c in conventions:
        require(set(c['existing_witnesses'] + c['existing_partial_witnesses']) <= existing_ids,
                f'convention {c["id"]}: unknown existing witness')
        for category, backlink in backlinks.items():
            expected = []
            for q in questions:
                items = q['conventions'][category]
                ids = [p['id'] for p in items] if category == 'partial' else items
                if c['id'] in ids:
                    expected.append(q['id'])
            require(c[backlink] == expected, f'convention {c["id"]}: {backlink} mismatch')

    pairs = audit['pairwise_checks']
    expected_pairs = list(combinations(by_id, 2))
    require([(p['a'], p['b']) for p in pairs] == expected_pairs, 'incomplete/repeated pairs')
    collisions = 0
    needs_review = []
    for p in pairs:
        a, b = signature(by_id[p['a']]), signature(by_id[p['b']])
        differences = [key for key in fields if a[key] != b[key]]
        require(p['different_fields'] == differences, f'{p["a"]}/{p["b"]}: wrong differences')
        collisions += not differences
        expected = ('distinct_annotated_operator_signature' if differences
                    else 'same_signature_requires_review')
        if (p['a'], p['b']) == ('Q101', 'Q105'):
            expected = 'manual_review_required_simple_sum_family'
        require(p['design_check'] == expected and p['sql_verified'] is False,
                f'{p["a"]}/{p["b"]}: unsupported pass claim')
        if expected != 'distinct_annotated_operator_signature':
            needs_review.append(f'{p["a"]}/{p["b"]}')

    print('CONSISTENT design annotations: 22 questions, 15 conventions, 231 pairs.')
    print('Estimated dimension-join depths:', dict(sorted(Counter(
        q['structure']['estimated_min_dimension_join_depth'] for q in questions).items())))
    print('Dedup semantics:', dict(Counter(q['structure']['dedup_count'] for q in questions)))
    print('Staged logic:', sum(q['structure']['staged_logic'] for q in questions))
    print('Identical annotated signatures:', collisions)
    print('Manual review still required:', ', '.join(needs_review) or 'none')
    print('Summary coverage: 22 unverified; metric callability: 22 unverified.')
    print('Design only. SQL verification and T05 acceptance are NOT established.')


if __name__ == '__main__':
    main()
