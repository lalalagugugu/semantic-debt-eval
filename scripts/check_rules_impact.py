#!/usr/bin/env python
"""Reexecute the 600 public candidates; separate contract and reference effects."""
from collections import Counter
import argparse
import ast
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

import yaml

from build_refs import effective_rules, load_selection_policy, load_unit_policy

REPO = Path(__file__).resolve().parent.parent


def csv_rows(record):
    rows = []
    with (REPO / record['result_path']).open(newline='') as stream:
        reader = csv.reader(stream)
        next(reader)
        for row in reader:
            values = []
            for value, column in zip(row, record['columns'], strict=True):
                typ = column['type']
                if value == '\\N':
                    value = None
                elif 'Int' in typ and not typ.startswith(('Array', 'Tuple', 'Map')):
                    value = int(value)
                elif any(name in typ for name in ('Float', 'Decimal')) and not typ.startswith(('Array', 'Tuple', 'Map')):
                    value = Decimal(value)
                elif typ.startswith(('Array', 'Tuple', 'Map')):
                    value = ast.literal_eval(value)
                values.append(value)
            rows.append(values)
    return rows


def contract_domain(qid, sql, question):
    rules = dict(question['rules'])
    if qid == 22:
        sql = re.sub(r'\s+WHERE rn <= 5\s*$', '', sql, flags=re.I)
    elif qid == 71:
        sql = sql.replace('FROM ranked WHERE rn = 1', 'FROM ranked')
    elif qid == 74:
        sql = re.sub(r'WHERE r\.rn <= 3', '', sql, flags=re.I)
        sql = re.sub(r'LIMIT 50\s*$', '', sql, flags=re.I)
        # Contract-only axis retains the original public channel and joins.
        rules['selection'] = {
            'version': 1,
            'stages': [{'parent': None, 'where': [], 'group_columns': [0], 'object_columns': [1], 'order_by': [{'column': 2, 'descending': True}], 'n': 3}],
            'output_order': [{'column': 0, 'descending': False}, {'column': 2, 'descending': True}],
        }
        rules['ordered'] = True
    elif qid == 85:
        sql = re.sub(r'\bLIMIT\s+5\b', '', sql, flags=re.I)
    elif qid == 98:
        end = sql.rfind(')\nSELECT')
        sql = sql[:end + 1] + ' SELECT ProductCategoryName,q_sales*100.0/sum(q_sales) OVER (PARTITION BY ProductCategoryName) AS peak_quarter_share_pct,q AS peak_quarter FROM cat_q ORDER BY peak_quarter_share_pct DESC'
    else:
        raise ValueError('unexpected grouped contract ID')
    return sql, rules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clean-baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=REPO / 'audit/rules-impact.json')
    parser.add_argument('--report', type=Path, default=REPO / 'audit/rules-impact.md')
    args = parser.parse_args()
    main_dir = Path(os.environ['SEMDEBT_MAIN_DIR'])
    data_dir = Path(os.environ['SEMDEBT_DATA_DIR'])
    selection, _ = load_selection_policy()
    _, policy_hash = load_unit_policy()
    spec = importlib.util.spec_from_file_location('impact_validation_adapter', main_dir / 'scripts/validate_scorer.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    from harness.scorer import ExecError, score_detailed
    from chdb import session

    questions = {int(q['id'][1:]): q for q in yaml.safe_load((REPO / 'questions/cube_100.yaml').read_text())['questions']}
    public = {int(q['id']): q for q in json.loads((REPO / 'vendor/cube/text_to_sql_benchmark.json').read_text())['questions']}
    manifest = json.loads((REPO / 'refs/MANIFEST.json').read_text())
    records_by_path = {r['result_path']: r for r in manifest['records']}
    clean = json.loads(args.clean_baseline.read_text())
    clean_outcomes = {(r['system'], r['question_id']): r.get('our_outcome', r.get('new')) for r in clean['records']}
    clean_records = {(r['system'], r['question_id']): r for r in clean['records']}
    assert len(clean_outcomes) == 600
    assert set(clean_outcomes.values()) <= {'correct', 'wrong', 'exec_error', 'refused', 'excluded'}
    run_root = REPO / 'vendor/cube/published-runs' / adapter.RUN_ID
    systems = sorted(p.name for p in run_root.iterdir() if p.is_dir() and p.name not in {'reference', 'scoring'})
    raw_dir = data_dir / 'rules-backfill' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    raw_dir.mkdir(parents=True, exist_ok=False)
    output = []
    references, changed_references, baseline_rules, contract_rules = {}, {}, {}, {}
    resets = 0
    sess = adapter.open_session(session, data_dir / 'chdb-eval')
    try:
        for qid, original in sorted(public.items()):
            if qid in adapter.EXCLUDED_QUESTION_IDS:
                continue
            rule = adapter.question_rules(qid, original['expected_sql'])
            reference, _, _ = adapter.stable_reference(sess, original['expected_sql'], qid, rule)
            baseline_rules[qid] = rule
            references[qid] = reference
            if qid in {22, 71, 74, 85, 98}:
                sql, new_rules = contract_domain(qid, original['expected_sql'], questions[qid])
                payload = json.loads(str(sess.query(sql, 'JSONCompact')))
                new_rules['value_kinds'] = adapter.reference_value_kinds(sql, payload['meta'])
                new_rules['value_types'] = [c['type'] for c in payload['meta']]
                rows = sorted(payload['data'], key=lambda row: json.dumps(row, ensure_ascii=False))
                changed_references[qid], _ = selection.complete_selection(rows, new_rules['selection'], new_rules['value_kinds'])
                contract_rules[qid] = new_rules
        with (raw_dir / 'candidates.jsonl').open('x') as raw:
            for system in systems:
                for qid in sorted(public):
                    candidate_sql = adapter.load_json(run_root / system / f'q{qid:02d}.json')['sql']
                    candidate = adapter.execute_rows(sess, candidate_sql)
                    if isinstance(candidate, ExecError):
                        sess = adapter.reset_session(sess, session, data_dir / 'chdb-eval')
                        resets += 1
                    raw.write(json.dumps({'system': system, 'question_id': qid, 'error': candidate.message if isinstance(candidate, ExecError) else None, 'rows': None if isinstance(candidate, ExecError) else candidate}, ensure_ascii=False) + '\n')
                    strict = adapter.load_json(run_root / 'scoring' / system / f'q{qid:02d}.json')
                    row = {'system': system, 'question_id': qid, 'historical_clean': clean_outcomes[system, qid], 'strict': strict['verdict'], 'analytical': strict['analytical_verdict']}
                    if qid in adapter.EXCLUDED_QUESTION_IDS:
                        row.update(baseline='excluded', contract='excluded', reference_only='excluded', combined='excluded')
                    else:
                        before = score_detailed(candidate, [references[qid]], baseline_rules[qid])
                        after = score_detailed(candidate, [changed_references.get(qid, references[qid])], contract_rules.get(qid, baseline_rules[qid]))
                        row.update(baseline=before.outcome, contract=after.outcome, contract_reason=after.reason)
                        if questions[qid]['scoring'] == 'deterministic':
                            current_refs = questions[qid]['refs']
                            current = [csv_rows(records_by_path[ref['result_path']]) for ref in current_refs]
                            overrides = [ref.get('rules') for ref in current_refs]
                            combined = score_detailed(candidate, current, questions[qid]['rules'], reference_rules=overrides)
                            flat_overrides = [{**effective_rules(questions[qid], ref), 'selection': None} for ref in current_refs]
                            reference_only = score_detailed(candidate, current, {**questions[qid]['rules'], 'selection': None}, reference_rules=flat_overrides)
                            row.update(reference_only=reference_only.outcome, combined=combined.outcome, combined_reason=combined.reason)
                        else:
                            row.update(reference_only=None, combined=None, combined_reason='judge_examples_are_not_closed_answer_sets')
                    row['contract_changed'] = row['baseline'] != row['contract']
                    row['reference_changed'] = row['reference_only'] is not None and row['baseline'] != row['reference_only']
                    row['combined_changed'] = row['combined'] is not None and row['baseline'] != row['combined']
                    row['baseline_reexecution_changed'] = row['baseline'] != row['historical_clean']
                    row['reference_scope'] = 'judge_example_only' if row['combined'] is None else 'current_bank_with_T04_revisions_orphan_repairs_and_purchase_variants'
                    prior = clean_records[system, qid]
                    intentional = prior.get('intentional_broader', (adapter.SYSTEM_LABELS[system], qid) in adapter.INTENTIONAL_BROADER or (prior.get('relative_only_outcome') == 'wrong' and row['historical_clean'] == 'correct'))
                    row['intentional_broader'] = row['contract'] == 'correct' and row['strict'] != 'pass' and (intentional or (row['contract_changed'] and qid in contract_rules))
                    output.append(row)
                    if len(output) % 10 == 0:
                        print(f'impact executed {len(output)}/600', flush=True)
    finally:
        sess.close()
    comparable = [r for r in output if r['contract'] != 'excluded']
    agreements = sum((r['contract'] == 'correct') == (r['strict'] == 'pass') for r in comparable)
    analytical = sum((r['contract'] == 'correct') == (r['analytical'] == 'pass') for r in comparable)
    wider = sum(r['intentional_broader'] for r in comparable)
    result = {'executed_candidates': len(output), 'runtime': {'max_threads': 1, 'max_execution_time': 30, 'session_resets': resets}, 'unit_policy_sha256': policy_hash,
              'selection_sha256': hashlib.sha256((main_dir / 'harness/selection.py').read_bytes()).hexdigest(), 'question_sha256': hashlib.sha256((REPO / 'questions/cube_100.yaml').read_bytes()).hexdigest(),
              'raw_candidates_sha256': hashlib.sha256((raw_dir / 'candidates.jsonl').read_bytes()).hexdigest(), 'raw_candidates_path': str(raw_dir / 'candidates.jsonl'),
              'contract_counts': dict(Counter(r['contract'] for r in output)), 'reference_counts': dict(Counter(r['reference_only'] for r in output if r['reference_only'] is not None)), 'combined_counts': dict(Counter(r['combined'] for r in output if r['combined'] is not None)),
              'reference_manifest_sha256': hashlib.sha256((REPO / 'refs/MANIFEST.json').read_bytes()).hexdigest(), 'baseline_input_sha256': hashlib.sha256(args.clean_baseline.read_bytes()).hexdigest(), 'strict_agreements': agreements, 'strict_comparable': len(comparable), 'analytical_agreements': analytical,
              'wider_excluded_agreements': agreements, 'wider_excluded_comparable': len(comparable) - wider, 'records': output}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    lines = ['# 评分规则补齐：600条影响复验', '', '本报告仅题号及汇总，不含题干、SQL或结果行。会话污染复验另存；本次固定全局量化与容差。', '',
             f'执行600条；Q33的6条历史excluded保留（当前题库Q33已完整复算；该题仍为judge，不能凭示例替代开放评分），可比较分母{len(comparable)}。执行失败即关闭并重建会话，共{resets}次。', '',
             f'原公开参考＋新分组契约：strict一致{agreements}/{len(comparable)}；analytical一致{analytical}/{len(comparable)}；排除有意更宽后的描述性分母为{agreements}/{len(comparable)-wider}。', '',
             '历史strict一致521/594（87.7%）、排除11条有意更宽后521/583（89.4%）保留，不覆盖。', '',
             'reference_only固定旧扁平比较，combined为当前题库参考＋新契约；二者只在确定性题记录。judge参考仅是示例，不能用“与例子不同”代替judge结论。参考修复轴同时包含T04既有修订及本次孤儿修复，不将其全部归为Q74或模型改善。', '',
             '每条四轴判定保存在配套JSON。下表逐条列出任何判定变化；historical_clean差异是复执行稳定性轴，不能直接归为新契约。', '',
             '| 系统 | 题号 | 干净历史 | 本轮旧契约 | 仅契约 | 仅参考 | 联合 |', '|---|---|---|---|---|---|---|']
    for r in output:
        if any(r[k] for k in ('contract_changed', 'reference_changed', 'combined_changed', 'baseline_reexecution_changed')):
            lines.append(f"| {adapter.SYSTEM_LABELS[r['system']]} | Q{r['question_id']:02d} | {r['historical_clean']} | {r['baseline']} | {r['contract']} | {r['reference_only'] or 'judge'} | {r['combined'] or 'judge'} |")
    lines += ['', '汇总：' + '；'.join(f"{key}={sum(r[key] for r in output)}" for key in ('contract_changed', 'reference_changed', 'combined_changed', 'baseline_reexecution_changed')), '',
              'G0已通过的历史事实保留；新的契约／参考影响交用户评估，不能自动撤销或重批G0。第二轮22题已正式落地、全部148份参考已重算。T05b跨引擎核对及Q79独立成员复现仍为冻结前置。']
    args.report.write_text('\n'.join(lines) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k.endswith('agreements') or k.endswith('comparable') or k == 'contract_counts'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
