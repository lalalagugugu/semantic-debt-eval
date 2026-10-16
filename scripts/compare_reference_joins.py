#!/usr/bin/env python
"""Measure all 24 remaining INNER-dimension paths without rewriting answers."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

import yaml
from chdb import session

from audit_reference_data_quality import inspect_reference
from build_refs import effective_rules, load_selection_policy, load_unit_policy, postprocess_reference

ROOT = Path(__file__).resolve().parent.parent
JOIN = re.compile(r'\b(?:(INNER|LEFT|RIGHT|FULL)\s+)?JOIN\s+(?:retail\.)?Dim(?:Product(?:Subcategory|Category)?|Employee)\b', re.I)


def left_variant(sql):
    return JOIN.sub(lambda m: m.group() if m.group(1) and m.group(1).upper() != 'INNER' else re.sub(r'^(?:INNER\s+)?JOIN', 'LEFT JOIN', m.group(), flags=re.I), sql)


def normalized(rows, kinds, policy):
    return Counter(json.dumps([policy.quantize_tie(cell, kind) for cell, kind in zip(row, kinds, strict=True)], ensure_ascii=False, default=str) for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'audit/T05-inner-left.json')
    parser.add_argument('--report', type=Path, default=ROOT / 'audit/T05-inner-left.md')
    parser.add_argument('--questions', type=Path, default=ROOT / 'audit/reviews/2026-10-16-pre-join-questions.yaml')
    args = parser.parse_args()
    policy, policy_hash = load_unit_policy()
    selection, _ = load_selection_policy()
    questions = yaml.safe_load(args.questions.read_text())['questions']
    targets = [(q, r) for q in questions for r in q['refs'] if inspect_reference(q, r, 'active_original')['fact_product_inner_exposure']]
    if len(targets) != 24 or len({q['id'] for q, _ in targets}) != 20:
        raise ValueError('expected the original 20-question / 24-reference audit cohort')
    raw_dir = Path(os.environ['SEMDEBT_DATA_DIR']) / 't05-finalize' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-joins')
    raw_dir.mkdir(parents=True, exist_ok=False)
    records = []
    result = {'unit_policy_sha256': policy_hash, 'questions_path': str(args.questions), 'questions_sha256': hashlib.sha256(args.questions.read_bytes()).hexdigest(), 'max_execution_time': 0, 'max_threads': 1, 'completed': False, 'raw_directory': str(raw_dir), 'records': records}

    def save():
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')

    sess = session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR']) / 'chdb-eval'))
    try:
        sess.query('SET max_threads=1')
        sess.query('SET max_execution_time=0')
        sess.query('SET output_format_json_quote_denormals=1')
        for index, (q, ref) in enumerate(targets, 1):
            rules = effective_rules(q, ref)
            variants = {}
            for label, sql in (('inner', ref['sql']), ('left', left_variant(ref['sql']))):
                if rules['top_n'] is not None:
                    sql, n = re.subn(rf"\bLIMIT\s+{rules['top_n']}\s*;?\s*$", '', sql, flags=re.I)
                    if n != 1:
                        raise ValueError('cannot extend ranked audit domain')
                print(f'{index}/24 {ref["result_path"]} {label}', flush=True)
                try:
                    payload = json.loads(str(sess.query(sql, 'JSONCompact')))
                    meta, rows, _ = postprocess_reference(ref.get('postprocess'), payload['meta'], payload['data'], policy)
                    if rules.get('selection'):
                        rows, _ = selection.complete_selection(rows, rules['selection'], rules['value_kinds'])
                    elif rules['top_n'] is not None:
                        key = lambda row: tuple(policy.quantize_tie(row[i], rules['value_kinds'][i]) for i in rules['tie_columns'])
                        ascending = bool(re.search(r'\bASC\s*(?:LIMIT\s+\d+)?\s*;?\s*$', ref['sql'], re.I))
                        rows.sort(key=key, reverse=not ascending)
                        boundary = key(rows[min(rules['top_n'], len(rows))-1])
                        rows = [row for row in rows if key(row) <= boundary] if ascending else [row for row in rows if key(row) >= boundary]
                    raw = json.dumps({'meta': meta, 'rows': rows}, ensure_ascii=False, indent=2) + '\n'
                    path = raw_dir / (Path(ref['result_path']).stem + '-' + label + '.json')
                    path.write_text(raw)
                    variants[label] = {'sql_sha256': hashlib.sha256(sql.encode()).hexdigest(), 'row_count': len(rows), 'sha256': hashlib.sha256(raw.encode()).hexdigest(), 'rows': rows}
                except Exception as error:
                    records.append({'question_id': q['id'], 'result_path': ref['result_path'], 'status': 'exec_error', 'variant': label, 'error': str(error)})
                    save()
                    raise
            before = normalized(variants['inner'].pop('rows'), rules['value_kinds'], policy)
            after = normalized(variants['left'].pop('rows'), rules['value_kinds'], policy)
            record={'question_id': q['id'], 'result_path': ref['result_path'], **variants, 'quantized_members_equal': before == after, 'removed_rows': sum((before-after).values()), 'added_rows': sum((after-before).values()), 'status': 'path_present_no_result_impact' if before == after else 'repair_required'}
            if q['id']=='Q73':
                # Preserve product identity; grouping missing names would invent one object.
                sql=left_variant(ref['sql']).replace('GROUP BY p.ProductName','GROUP BY i.ProductKey,p.ProductName')
                sql,count=re.subn(r'\bLIMIT\s+10\s*;?\s*$','',sql,flags=re.I)
                if count!=1:
                    raise ValueError('expected Q73 complete ranking domain')
                payload=json.loads(str(sess.query(sql,'JSONCompact')))
                key=lambda row:tuple(policy.quantize_tie(row[i],rules['value_kinds'][i]) for i in rules['tie_columns'])
                rows=sorted(payload['data'],key=key,reverse=True)
                boundary=key(rows[9])
                rows=[row for row in rows if key(row)>=boundary]
                content=json.dumps({'meta':payload['meta'],'rows':rows},ensure_ascii=False,indent=2)+'\n'
                (raw_dir/'Q73-per-product-left.json').write_text(content)
                record['per_product_identity_comparison_equal']=before==normalized(rows,rules['value_kinds'],policy)
                record['identity_check_sql_sha256']=hashlib.sha256(sql.encode()).hexdigest()
            records.append(record)
            save()
    finally:
        sess.close()
    result['completed'] = True
    save()
    lines = ['# 20题／24份参考：内连接与左连接实测', '', f'量纲策略SHA256：{policy_hash}。单线程，离线参考计算不限时；比较完整量化结果多重集合。结果行保存在外部数据目录。', '', '| 题号／参考 | 内连接行数 | 左连接行数 | 移除／增加 | 结论 |', '|---|---:|---:|---:|---|']
    for row in records:
        lines.append(f"| {row['result_path']} | {row['inner']['row_count']} | {row['left']['row_count']} | {row['removed_rows']}／{row['added_rows']} | {'路径存在、结果无影响' if row['quantized_members_equal'] else '结果不同，须修复'} |")
    lines+=['','Q73另按事实ProductKey保留对象粒度复算，结果相同性见JSON的per_product_identity_comparison_equal；不得把缺名产品合并后当作真实Top-N。修复采用记录及后续双解见T05-finalization.md。']
    args.report.write_text('\n'.join(lines) + '\n')
    print(json.dumps(dict(Counter(r['status'] for r in records)), ensure_ascii=False))


if __name__ == '__main__':
    main()
