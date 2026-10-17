#!/usr/bin/env python
"""Quantify the 17-gap audit without changing questions or accepted references."""
import hashlib
import json
import os
import subprocess
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from build_refs import load_unit_policy
from check_rules_impact import csv_rows

ROOT = Path(__file__).resolve().parent.parent


def main():
    output = ROOT / 'audit/2026-10-17-gap-decision-deltas.json'
    if output.exists():
        raise ValueError('Audit output already exists; preserve the previous run')
    questions = {q['id']: q for name in ('cube_100', 'new')
                 for q in json.loads((ROOT / f'questions/{name}.yaml').read_text())['questions']}
    records = {r['result_path']: r for r in json.loads((ROOT / 'refs/MANIFEST.json').read_text())['records']}
    unit, unit_sha = load_unit_policy()
    evidence = {}
    original = {r['id']: r for r in json.loads((ROOT / 'audit/2026-10-17-semantic-gaps.json').read_text())['entries']}
    evidence['G01'] = {'stores': 306, 'fact_rows': 3406089, 'real_order_delta': None,
                       'reason': 'FactSales has no order identifier; real order interpretation cannot be reconstructed'}
    a, b = original['G05']['alternatives']
    evidence['G05'] = {'sales_EUR': [a['sales_eur'], b['sales_eur']],
                       'absolute_difference_EUR': str(Decimal(str(b['sales_eur'])) - Decimal(str(a['sales_eur']))),
                       'covered_days': [a['covered_days'], b['covered_days']]}
    for gid in ('G08', 'G09'):
        a, b = original[gid]['alternatives']
        assert a['membership_sha256'] == b['membership_sha256']
        evidence[gid] = {'members_each': a['members'], 'changed_members': 0,
                         'thresholds': [a['thresholds'], b['thresholds']]}
    a, b = original['G12']['alternatives']
    evidence['G12'] = {'members_each': len(a['store_keys']),
                       'common_members': len(set(a['store_keys']) & set(b['store_keys']))}
    a, b = original['G13']['alternatives']
    evidence['G13'] = {'brands': len(a['brands']),
                       'different_positions': sum(x != y for x, y in zip(a['brands'], b['brands'], strict=True))}

    def refs(qid):
        return [csv_rows(records[r['result_path']]) for r in questions[qid]['refs']]

    def pairs(a, b):
        left = {r[0]: r[1:] for r in a}
        right = {r[0]: r[1:] for r in b}
        assert len(left) == len(a) and len(right) == len(b) and left.keys() == right.keys()
        return [(left[k], right[k]) for k in left]

    def differences(a, b, positions, kind):
        aligned = pairs(a, b)
        deltas = [[abs(Decimal(str(x[i])) - Decimal(str(y[i]))) for i in positions]
                  for x, y in aligned]
        return {'groups': len(aligned), 'different_groups_at_global_precision': sum(
            any(unit.quantize_tie(x[i], kind) != unit.quantize_tie(y[i], kind) for i in positions)
            for x, y in aligned),
            'max_absolute_differences': [str(max(d[i] for d in deltas)) for i in range(len(positions))]}

    for qid, gid, pos, kind in [('Q38', 'G03', [2], 'percentage'), ('Q121', 'G15', [1], 'ratio')]:
        a, b = refs(qid)
        evidence[gid] = differences(a, b, pos, kind)
    a, b = refs('Q97')
    left = {r[4] for r in a}; right = {r[0] for r in b}
    evidence['G10'] = {'rows_each': len(a), 'common_products': len(left & right),
                       'replaced_products': len(left - right), 'symmetric_difference': len(left ^ right)}
    a, b = refs('Q98')
    evidence['G11'] = {'single_year_rows': len(a), 'all_year_rows': len(b),
                       'shared_2009': differences(a, [[r[0], *r[2:]] for r in b if r[1] == 2009], [0], 'percentage')}
    a, b = refs('Q119')
    evidence['G14'] = {'rows_each': len(a), 'exact_rows_equal': Counter(map(tuple, a)) == Counter(map(tuple, b))}
    correlations = json.loads((ROOT / 'audit/2026-10-17-correlation-gap-final.json').read_text())['records']
    evidence['G17'] = {}
    for r in correlations:
        if 'details' in r:
            evidence['G17'][r['question_id']] = {'groups': r['groups'], 'different_groups': r['different_groups'],
                'max_absolute_difference': max(abs(x['pearson'] - x['spearman']) for x in r['details']),
                'sample_cutoff_review': r['sample_cutoff_review']}
        else:
            evidence['G17'][r['question_id']] = {**r, 'absolute_difference': abs(r['pearson'] - r['spearman'])}

    from chdb import session
    sess = session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR']) / 'chdb-eval'))
    try:
        sess.query('SET max_threads=1')
        sess.query('SET max_execution_time=0')
        def query(sql):
            return json.loads(str(sess.query(sql, 'JSONCompact')))['data']

        a = query(questions['Q47']['refs'][0]['sql'])
        b = query('SELECT s.StoreName,avg(m.downtime) FROM (SELECT StoreKey,MachineKey,sum(DownTime) AS downtime FROM retail.FactITSLA WHERE DownTime IS NOT NULL GROUP BY StoreKey,MachineKey) m JOIN retail.DimStore s ON m.StoreKey=s.StoreKey GROUP BY s.StoreKey,s.StoreName')
        evidence['G02'] = differences(a, b, [0], 'other')
        sql = questions['Q39']['refs'][0]['sql']
        marker = "least(dateDiff('day',toDate('2007-01-01'),introduction_date),dateDiff('day',introduction_date,toDate('2010-01-01')))"
        assert sql.count(marker) == 1
        a = query(sql); b = query(sql.replace(marker, 'toInt64(90)'))
        evidence['G04'] = differences(a, b, [3, 4], 'amount')
        evidence['G04']['original_window_days'] = sorted({r[3] for r in a})
        # Compare unrounded percentages to avoid counting display rounding as a business difference.
        sql = questions['Q76']['refs'][0]['sql']
        before = 'round(sumIf(f.SalesAmount, co.n_orders >= 2) * 100.0 / nullif(sum(f.SalesAmount), 0), 2)'
        after = 'sumIf(f.SalesAmount, co.n_orders >= 2) * 100.0 / nullif(sum(f.SalesAmount), 0)'
        assert sql.count(before) == 1
        a = query(sql.replace(before, after)); b = query(questions['Q76']['refs'][1]['sql'])
        evidence['G06'] = differences(a, b, [0], 'percentage')
        evidence['G06']['left_range_pct'] = [min(r[1] for r in a), max(r[1] for r in a)]
        evidence['G06']['right_range_pct'] = [min(r[1] for r in b), max(r[1] for r in b)]
        # Q84 raw domain columns are taken from the returned schema, not assumed aliases.
        payload = json.loads(str(sess.query(questions['Q84']['refs'][0]['sql'], 'JSONCompact')))
        rows = payload['data']
        pos = {c['name']: i for i, c in enumerate(payload['meta'])}
        groups = defaultdict(list)
        for row in rows:
            groups[unit.quantize_tie(row[pos['revenue']], 'amount')].append(row)
        total = sum(v * len(rs) for v, rs in groups.items())
        cumulative = Decimal(0); transitions = Counter(); old_counts = Counter(); new_counts = Counter()
        for revenue, members in sorted(groups.items(), reverse=True):
            old = 'A' if cumulative < total * Decimal('.8') else 'B' if cumulative < total * Decimal('.95') else 'C'
            cumulative += revenue * len(members)
            new = 'A' if cumulative <= total * Decimal('.8') else 'B' if cumulative <= total * Decimal('.95') else 'C'
            old_counts[old] += len(members); new_counts[new] += len(members)
            if old != new:
                transitions[f'{old}->{new}'] += len(members)
        evidence['G07'] = {'before_counts': dict(old_counts), 'after_counts': dict(new_counts),
                           'changed_products': sum(transitions.values()), 'transitions': dict(transitions)}
        rows = query('SELECT pc.ProductCategoryName,sumIf(f.SalesAmount,f.PromotionKey!=1) AS promo,sumIf(f.SalesAmount,f.PromotionKey=1) AS full,countIf(f.PromotionKey!=1) AS n_promo,countIf(f.PromotionKey=1) AS n_full FROM retail.FactOnlineSales f LEFT JOIN retail.DimProduct p ON f.ProductKey=p.ProductKey LEFT JOIN retail.DimProductSubcategory ps ON p.ProductSubcategoryKey=ps.ProductSubcategoryKey LEFT JOIN retail.DimProductCategory pc ON ps.ProductCategoryKey=pc.ProductCategoryKey GROUP BY pc.ProductCategoryName')
        a = [r[1] - r[2] for r in rows]
        b = [r[1] / r[3] - r[2] / r[4] if r[3] and r[4] else None for r in rows]
        assert all(v is not None for v in b)
        evidence['G16'] = {'groups': len(rows), 'total_difference_USD_range': [min(a), max(a)],
                           'per_row_difference_USD_range': [min(b), max(b)],
                           'sign_changed_groups': sum((x > 0) != (y > 0) for x, y in zip(a, b, strict=True)),
                           'cross_method_subtraction': 'Not meaningful: USD versus USD per fact row'}
    finally:
        sess.close()
    source = Path(os.environ['SEMDEBT_MAIN_DIR'])
    source_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in
                     ('semantic/summary/summary.sql', 'render/measures.py', 'semantic/metrics.yaml')}
    frozen_revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'semantic-v1'], text=True).strip()
    for name in source_hashes:
        frozen = subprocess.check_output(['git', '-C', str(source), 'show', f'semantic-v1:{name}'])
        assert hashlib.sha256(frozen).hexdigest() == source_hashes[name], f'Not frozen source: {name}'
    output.write_text(json.dumps({'unit_policy_sha256': unit_sha, 'semantic_source_sha256': source_hashes,
                                  'semantic_v1_revision': frozen_revision,
                                  'accepted_reference_changes': False, 'entries': evidence}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
