#!/usr/bin/env python
"""Check persisted reference rules and render the external-column review table."""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import yaml

from build_refs import effective_rules, load_selection_policy, load_unit_policy, validate_questions

REPO = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review', action='store_true')
    args = parser.parse_args()
    policy, policy_hash = load_unit_policy()
    load_selection_policy()
    spec = importlib.util.spec_from_file_location('rules_validation_adapter', Path(os.environ['SEMDEBT_MAIN_DIR']) / 'scripts/validate_scorer.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    groups = [yaml.safe_load((REPO / filename).read_text())['questions'] for filename in ('questions/cube_100.yaml', 'questions/new.yaml')]
    for source, questions in zip(('cube', 'new'), groups, strict=True):
        validate_questions(questions, source)
    manifest = json.loads((REPO / 'refs/MANIFEST.json').read_text())
    assert manifest['unit_policy_sha256'] == policy_hash
    records = {record['result_path']: record for record in manifest['records']}
    assert len(records) == len(manifest['records'])
    assert set(records) == {ref['result_path'] for questions in groups for q in questions for ref in q['refs']}
    lines = ['# 外部100题逐参考rules审阅表', '',
             '状态：自动推断结果供用户过目；不是人工批准或T05b独立重算结论。', '',
             '逐参考rules整份覆盖题级rules；没有ref.rules时沿用题级。下表每列依次为列名、查询返回类型、量纲；[整数守卫]仅标记count且返回整数类型的列。other不享受额外atol，不因数值外观猜单位。', '',
             f'量纲策略SHA256：`{policy_hash}`。并列使用Decimal ROUND_HALF_EVEN，amount两位、percentage先除100再六位、ratio/其他数值六位。', '',
             'Q101–Q122已按批准稿落实第二轮正式SQL，显式声明量纲并重新计算；这不是T05b独立pandas核验或eval-v1冻结结论。', '',
             '| 题号／参考 | ordered | 选择约束 | 列名／返回类型／推断量纲 |',
             '|---|---|---|---|']
    ordered = selected = count_guards = 0
    for questions in groups:
        for q in questions:
            for position, ref in enumerate(q['refs'], 1):
                rules = effective_rules(q, ref)
                record = records[ref['result_path']]
                assert record['rules'] == rules, (q['id'], position, 'rules')
                assert record['ordered'] == rules['ordered']
                if rules['ordered']:
                    assert rules['order_by'] and all(0<=key['column']<len(record['columns']) for key in rules['order_by'])
                assert record['value_kinds'] == rules['value_kinds']
                assert record['value_types'] == rules['value_types'] == [column['type'] for column in record['columns']]
                assert record['sql_sha256'] == hashlib.sha256(ref['sql'].encode()).hexdigest()
                path = REPO / ref['result_path']
                assert record['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
                with path.open(newline='') as stream:
                    reader = csv.reader(stream)
                    assert next(reader) == [column['name'] for column in record['columns']]
                    assert sum(1 for _ in reader) == record['row_count']
                if q['source'] == 'cube':
                    expected = int(q['id'][1:]) in adapter.ORDERED_QUESTION_IDS and adapter.final_order_clause(ref['sql']) is not None
                    assert rules['ordered'] == expected, (q['id'], position, 'ordered')
                    assert rules['value_kinds'] == adapter.reference_value_kinds(ref['sql'], record['columns'])
                    assert record['value_kind_source'] == 'inferred'
                    cells = []
                    for column, kind in zip(record['columns'], rules['value_kinds'], strict=True):
                        guarded = kind == 'count' and policy.is_integer_type(column['type'])
                        count_guards += guarded
                        name = column['name'].replace('|', '&#124;')
                        cells.append(f"`{name}` / `{column['type']}` / **{kind}**" + (' [整数守卫]' if guarded else ''))
                    selection = rules.get('selection')
                    constraint = f"{len(selection['stages'])}步骤分组选择" if selection else f"Top-{rules['top_n']}，键{rules['tie_columns']}" if rules['top_n'] is not None else '参考行集'
                    lines.append(f"| {q['id']}/{position} | {str(rules['ordered']).lower()} | {constraint} | {'<br>'.join(cells)} |")
                    ordered += rules['ordered']
                    selected += bool(selection)
                else:
                    assert record['value_kind_source'] == 'declared'
                if rules.get('selection'):
                    assert record['selection_checks'] is not None
    lines += ['', f'合计：100题、{len([r for r in records.values() if r["question_id"] in {q["id"] for q in groups[0]}])}份参考；ordered=true共{ordered}份；分组选择{selected}份参考；整数计数守卫{count_guards}列。', '',
             'Q33/Q45/Q97等judge题的示例截断不自动成为题干固定N；维持已批准的声明口径与非封闭示例，不将示例LIMIT伪装成新增的题意限制。', '',
              '类型来源：直接查询列取引擎返回元数据；Q74等后处理保留对应投影类型。Q84的abc_groups会生成新输出列，表中类型沿用T04已批准的正式后处理schema，不是原始聚合域的列类型；T05b须同时独立核对这一输出schema。', '',
              '冻结前仍需：用户审阅本表；T05b独立核对返回类型、量纲、排序、完整边界及已披露的参考修复。Q79以当前参考推导的边界成员集合及规则版本为准；2026-10-16 T05b差异裁决已确认独立成员集合一致并放行，旧306成员仅为历史工件，不是现行门禁。']
    review = '\n'.join(lines) + '\n'
    path = REPO / 'audit/rules-backfill-review.md'
    if args.write_review:
        path.write_text(review)
    else:
        assert path.read_text() == review, 'review table stale; regenerate with --write-review'
    print(f'PASS: 122 questions, {len(records)} reference rules/types/hashes, complete review table')


if __name__ == '__main__':
    main()
