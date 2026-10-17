#!/usr/bin/env python
"""Prepare T06 data-only evidence and reproducible split/pilot artifacts."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
from importlib.metadata import version as package_version

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ['SEMDEBT_MAIN_DIR'])
sys.path.insert(0, str(MAIN))
from build_refs import effective_rules, load_unit_policy, postprocess_reference
from check_rules_impact import csv_rows, verdict_only
from harness import selection
from harness.questions import parse_value

BASE = 'e3aaed630aed48ff0069c5ec24d8d7d2a0765f9d'
SEED = 20261017
POLICY, POLICY_HASH = load_unit_policy()


def dump(path, value):
    (ROOT / path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


def questions():
    return [q for name in ('cube_100', 'new') for q in json.loads((ROOT / f'questions/{name}.yaml').read_text())['questions']]


def refs_manifest():
    return {r['result_path']: r for r in json.loads((ROOT / 'refs/MANIFEST.json').read_text())['records']}


def members(rows, kinds):
    return Counter(tuple(POLICY.quantize_tie(v, k) for v, k in zip(row, kinds, strict=True)) for row in rows)


class Database:
    def __enter__(self):
        from chdb import session
        self.session = session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR']) / 'chdb-eval'))
        self.session.query('SET max_threads=1')
        self.session.query('SET max_execution_time=0')
        self.runtime = {'chdb_version': package_version('chdb'), 'clickhouse_version': self.query('SELECT version()')['data'][0][0], 'python_version': sys.version.split()[0], 'max_threads': 1, 'max_execution_time': 0, 'database_copy': 'chdb-eval'}
        return self

    def __exit__(self, *args):
        self.session.close()

    def query(self, sql):
        # Abort on any execution error; never reuse a potentially poisoned session.
        return json.loads(str(self.session.query(sql, 'JSONCompact')))


def b_counterpart(qid, ref, rows):
    sql = ref['sql']
    if qid in {'Q17', 'Q99'}:
        assert 'retail.DimDate d' in sql
        return '用节假日替换周末，保留 WeekEnd/WorkDay 输出标签', sql.replace('retail.DimDate d', "(SELECT * EXCEPT(IsWorkDay),if(IsHoliday='Yes','WeekEnd','WorkDay') AS IsWorkDay FROM retail.DimDate) d")
    if qid in {'Q29', 'Q68', 'Q59'}:
        return '用周末替换节假日，保留 Yes/No 输出标签', sql.replace('retail.DimDate', "(SELECT * EXCEPT(IsHoliday),if(IsWorkDay='WeekEnd','Yes','No') AS IsHoliday FROM retail.DimDate)")
    if qid == 'Q26':
        return '新客=当季度有购买的客户', "SELECT toQuarter(DateKey),uniqExact(CustomerKey) FROM retail.FactOnlineSales WHERE toYear(DateKey)=2007 GROUP BY toQuarter(DateKey) ORDER BY toQuarter(DateKey)"
    if qid == 'Q76':
        assert '>= 2' in sql or '>=2' in sql
        return '回头客=有购买，不检查至少两笔订单', sql.replace('>= 2', '>= 1').replace('>=2', '>=1')
    if qid == 'Q80':
        return '忽略首单：用最近一次购买日同时作起点和终点', sql.replace('MIN(DateKey) AS first_d', 'MAX(DateKey) AS first_d')
    if qid == 'Q81':
        return '首购年份分群=该年有购买，客户可以进入多个年份', sql.replace('toYear(MIN(DateKey)) AS cohort_year', 'toYear(DateKey) AS cohort_year').replace('GROUP BY CustomerKey\n)', 'GROUP BY CustomerKey,cohort_year\n)', 1)
    if qid == 'Q83':
        return '2007首购客=2007活跃客，后续留存条件不变', sql.replace('toYear(min(DateKey)) AS first_year', 'if(countIf(toYear(DateKey)=2007)>0,2007,0) AS first_year')
    if qid == 'Q96':
        return '首购年份分群=该年有购买，客户可以进入多个年份', sql.replace('toYear(min(DateKey)) AS first_year', 'toYear(DateKey) AS first_year').replace('GROUP BY CustomerKey\n)', 'GROUP BY CustomerKey,first_year\n)', 1)
    from audit_new_question_degeneracy import counterpart
    return counterpart(qid, ref, rows)


def selection_evidence(domain, spec, kinds):
    _, checks = selection.complete_selection(domain, spec, kinds)
    result = []
    # Each stage is scoped to its declared group and filters. Parent selections
    # are evaluated by the production selection policy, not a new tie algorithm.
    selected = []
    for index, stage in enumerate(spec['stages']):
        eligible = selection._eligible(domain, stage, spec['stages'], selected)
        groups = selection._domain(eligible, stage, kinds)
        chosen = set()
        stage_rows = []
        for group, objects in groups.items():
            strict, tied, required = selection._boundary(objects, stage)
            boundary = objects[next(iter(tied))]
            chosen.update(group + obj for obj in strict | tied)
            stage_rows.append({'group': list(group), 'n': stage['n'], 'required': required,
                               'domain_objects': len(objects), 'distinct_sort_keys': len(set(objects.values())),
                               'boundary_members': len(tied), 'nth_key': list(map(str, boundary)),
                               'hit': len(tied) >= 3 * stage['n']})
        selected.append(chosen)
        result.append({'stage': index, 'groups': stage_rows, 'production_checks': checks[index]})
    return result


def audit_low():
    records = refs_manifest()
    output = []
    with Database() as db:
        order_week_check = db.query("SELECT count(),countIf(weeks>1),max(weeks) FROM (SELECT SalesOrderNumber,uniqExact(tuple(toMonday(DateKey),toYear(DateKey))) AS weeks FROM retail.FactOnlineSales WHERE toYear(DateKey)=2009 GROUP BY SalesOrderNumber)")['data']
        for q in questions():
            item = {'question_id': q['id'], 'hits': [], 'A': [], 'B': [], 'C': []}
            flags = set()
            for ref in q['refs']:
                rec = records[ref['result_path']]
                assert hashlib.sha256((ROOT / ref['result_path']).read_bytes()).hexdigest() == rec['sha256']
                rows = csv_rows(rec)
                rule = effective_rules(q, ref)
                numeric = [i for i, k in enumerate(rule['value_kinds']) if k != 'other']
                profile = [{'column': rec['columns'][i]['name'], 'kind': rule['value_kinds'][i],
                            'distinct': len({POLICY.quantize_tie(r[i], rule['value_kinds'][i]) for r in rows}),
                            'minimum': min((r[i] for r in rows if r[i] is not None), default=None),
                            'maximum': max((r[i] for r in rows if r[i] is not None), default=None)} for i in numeric]
                candidates = {'empty': []}
                if numeric:
                    for name, value in [('all_zero_measures', 0), ('all_null_measures', None)]:
                        candidate = deepcopy(rows)
                        for row in candidate:
                            for i in numeric:
                                row[i] = value
                        candidates[name] = candidate
                    if all(rule['value_kinds'][i] in {'ratio', 'percentage'} for i in numeric):
                        candidate = deepcopy(rows)
                        for row in candidate:
                            for i in numeric:
                                row[i] = 100 if rule['value_kinds'][i] == 'percentage' else 1
                        candidates['all_full_ratios'] = candidate
                verdicts = {name: verdict_only(value, [rows], rule).outcome for name, value in candidates.items()}
                hits = [name for name, verdict in verdicts.items() if verdict == 'correct']
                # Follow the approved T05 audit convention: one computed scalar
                # is not a data-induced constant just because it has one cell.
                if len(rows) > 1 and profile and all(p['distinct'] <= 1 for p in profile):
                    hits.append('constant_measure_vector')
                if hits:
                    flags.add('A')
                item['A'].append({'reference': ref['result_path'], 'row_count': len(rows), 'measure_profile': profile,
                                  'trivial_verdicts': verdicts, 'hits': hits})
                alternate = b_counterpart(q['id'], ref, rows)
                if alternate:
                    reason, sql = alternate
                    other = db.query(sql)['data']
                    same = members(rows, rule['value_kinds']) == members(other, rule['value_kinds'])
                    if same:
                        flags.add('B')
                    item['B'].append({'reference': ref['result_path'], 'replacement': reason, 'replacement_sql': sql,
                                      'equal': same, 'original_rows': rows, 'replacement_rows': other})
                if rule.get('selection'):
                    domain = db.query(ref['sql'])['data']
                    meta = db.query('SELECT * FROM (' + ref['sql'] + ') LIMIT 0')['meta']
                    if ref.get('postprocess') == 'store_top3':
                        keep = [i for i, c in enumerate(meta) if c['name'] != 'StoreKey']
                        domain = [[r[i] for i in keep] for r in domain]
                    else:
                        meta, domain, _ = postprocess_reference(ref.get('postprocess'), meta, domain, POLICY)
                    stages = selection_evidence(domain, rule['selection'], rule['value_kinds'])
                    if any(g['hit'] for s in stages for g in s['groups']):
                        flags.add('C')
                    item['C'].append({'reference': ref['result_path'], 'stages': stages})
                elif rule['top_n'] is not None:
                    n = rule['top_n']
                    sql, changed = re.subn(rf'\bLIMIT\s+{n}\s*;?\s*$', '', ref['sql'], flags=re.I)
                    assert changed == 1, q['id']
                    domain = db.query(sql)['data']
                    keys = [tuple(POLICY.quantize_tie(r[i], rule['value_kinds'][i]) for i in rule['tie_columns']) for r in domain]
                    descending = rule['order_by'][0]['descending']
                    keys.sort(reverse=descending)
                    nth = keys[min(n, len(keys)) - 1]
                    count = keys.count(nth)
                    hit = count >= 3 * n
                    if hit:
                        flags.add('C')
                    item['C'].append({'reference': ref['result_path'], 'n': n, 'domain_rows': len(domain),
                                      'distinct_sort_keys': len(set(keys)), 'nth_key': list(map(str, nth)),
                                      'boundary_members': count, 'hit': hit})
            item['hits'] = sorted(flags)
            item['B_scope'] = 'first-purchase/repeat/cohort and holiday/weekend only'
            if not item['B']:
                item['B_not_applicable'] = '不涉及首单、复购、首购分群或节假日/周末'
            if not item['C']:
                item['C_not_applicable'] = '非Top-N选择；P90选择的证据另见新题复查'
            output.append(item)
            print(q['id'], item['hits'], flush=True)
            flagged = [r for r in output if r['hits']]
            if len(flagged) > 15 or q['source'] == 'new' and flags:
                dump('audit/T06-low-discrimination.json', {'stopped': True, 'records': output})
                raise SystemExit('User stop condition reached; no split/coverage preparation is allowed')
    dump('audit/T06-low-discrimination.json', {'stopped': False, 'base_revision': BASE,
         'unit_policy_sha256': POLICY_HASH, 'tie_quantization': 'Decimal ROUND_HALF_EVEN; amount=2, percentage/100 and ratio/other=6',
         'scope': 'data and references only; no model outputs or published system answers', 'runtime': db.runtime,
         'A_constant_policy': 'same policy as audit/T05-degeneracy-review.md; computed single scalar is not itself a constant',
         'Q53_order_week_disjointness': {'sql': "SELECT count(),countIf(weeks>1),max(weeks) FROM (SELECT SalesOrderNumber,uniqExact(tuple(toMonday(DateKey),toYear(DateKey))) AS weeks FROM retail.FactOnlineSales WHERE toYear(DateKey)=2009 GROUP BY SalesOrderNumber)", 'rows': order_week_check},
         'flagged': {r['question_id']: r['hits'] for r in output if r['hits']}, 'records': output})


def build_summary():
    path = MAIN / 'render/build_summary.py'
    spec = importlib.util.spec_from_file_location('t06_summary_builder', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.chdb_dir = lambda: Path(os.environ['SEMDEBT_DATA_DIR']) / 'chdb-eval'
    module.REPORT = ROOT / 'audit/T06-summary-build.md'
    sys.argv = [str(path)]
    module.main()
    text = module.REPORT.read_text().replace('uv run python render/build_summary.py', 'uv run python scripts/prepare_t06.py build-summary')
    module.REPORT.write_text(text.rstrip() + '\n')


def select_candidate(rows, rule):
    if rule.get('selection'):
        spec = rule['selection']
        selected, stage_rows = [], []
        for stage in spec['stages']:
            eligible = list(selection._eligible(rows, stage, spec['stages'], selected))
            groups = selection._domain(eligible, stage, rule['value_kinds'])
            chosen = set()
            for group, objects in groups.items():
                strict, tied, count = selection._boundary(objects, stage)
                # A candidate returns exactly N objects, while stored references
                # deliberately include the whole boundary for acceptable ties.
                take = strict | set(sorted(tied, key=repr)[:count-len(strict)])
                chosen.update(group + obj for obj in take)
            selected.append(chosen)
            stage_rows.append([r for r in eligible if selection.identity(r, stage['group_columns'] + stage['object_columns']) in chosen])
        parents = {stage['parent'] for stage in spec['stages']}
        wanted = {tuple(r) for i, part in enumerate(stage_rows) if i not in parents for r in part}
        result = [r for r in rows if tuple(r) in wanted]
        if spec['output_order']:
            from functools import cmp_to_key
            result.sort(key=cmp_to_key(lambda a, b: selection.compare_keys(selection.order_key(a, spec['output_order'], rule['value_kinds']), selection.order_key(b, spec['output_order'], rule['value_kinds']), spec['output_order'])))
        return result
    return rows[:rule['top_n']] if rule['top_n'] is not None else rows


def coverage():
    low = json.loads((ROOT / 'audit/T06-low-discrimination.json').read_text())
    assert low['Q53_order_week_disjointness']['rows'][0][1:] == [0, 1]
    plan = json.loads((ROOT / 'audit/T06-query-plan.json').read_text())['questions']
    manifest = refs_manifest()
    output = []
    with Database() as db:
        schema = db.query("SELECT name,engine,create_table_query FROM system.tables WHERE database='ads' ORDER BY name")['data']
        for q in questions():
            entry = plan[q['id']]
            attempts = []
            covered = False
            for query in entry['queries']:
                sql = query['sql']
                # Input is reviewed SQL; enforce the only permitted physical
                # namespace before execution. CTE aliases remain unqualified.
                if re.search(r'\b(?:retail|system|file|url|remote)\s*[.(]', sql, re.I) or not re.match(r'\s*(SELECT|WITH)\b', sql, re.I):
                    raise ValueError('non-ads coverage query: ' + q['id'])
                ref = q['refs'][query['reference_index']]
                rule = effective_rules(q, ref)
                payload = db.query(sql)
                # chDB serializes Decimal values as JSON strings; recover their
                # numeric type using returned metadata before the real scorer.
                rows = [[parse_value(str(v), c['type']) if v is not None else None for v, c in zip(r, payload['meta'], strict=True)] for r in payload['data']]
                meta, rows, details = postprocess_reference(ref.get('postprocess'), payload['meta'], rows, POLICY)
                rows = select_candidate(rows, rule)
                matches = []
                for accepted in q['refs']:
                    record = manifest[accepted['result_path']]
                    accepted_rule = effective_rules(q, accepted)
                    result = verdict_only(rows, [csv_rows(record)], accepted_rule)
                    matches.append({'reference': accepted['result_path'], 'outcome': result.outcome, 'reason': result.reason})
                scorer_matched = any(m['outcome'] == 'correct' for m in matches)
                valid = query.get('semantically_valid', True)
                matched = scorer_matched and valid
                covered |= matched
                attempts.append({'sql': sql, 'candidate_rows': rows, 'meta': meta, 'reference_matches': matches, 'matched': matched, 'scorer_matched': scorer_matched, 'semantically_valid': valid})
            item = {'question_id': q['id'], 'summary_coverage': 'covered' if covered else 'not_covered',
                    'reason': '仅使用ads汇总表/维度的查询已复现至少一份有效参考。' if covered else entry['reason'],
                    'attempts': attempts}
            output.append(item)
            print(q['id'], item['summary_coverage'], [m['outcome'] for a in attempts for m in a['reference_matches']], flush=True)
    dump('audit/T06-summary-coverage.json', {'base_revision': BASE, 'unit_policy_sha256': POLICY_HASH,
         'summary_sql_sha256': hashlib.sha256((MAIN / 'semantic/summary/summary.sql').read_bytes()).hexdigest(),
         'summary_yaml_sha256': hashlib.sha256((MAIN / 'semantic/summary/summary.yaml').read_bytes()).hexdigest(),
         'query_plan_sha256': hashlib.sha256((ROOT / 'audit/T06-query-plan.json').read_bytes()).hexdigest(),
         'ads_schema': schema, 'runtime': db.runtime, 'counts': dict(Counter(r['summary_coverage'] for r in output)), 'records': output})


REWRITE_NOTES = {
    'Q13': '按真实问法改写为门店销售额、平均单价和销量；订单指标改为已有平均单价。',
    'Q14': '按真实问法改为客户人数；累计消费门槛由10000美元改为100000美元，避免全体客户通过筛选。',
    'Q21': '按真实问法改为逐门店汇总当前在手库存，保留门店×产品各自最近快照口径。',
    'Q28': '按真实问法改为比较门店与线上渠道的平均单价；移除实体渠道不存在的订单概念。',
    'Q36': '按真实问法改为三个现有客户分层各有多少人。',
    'Q89': '按真实问法直接使用客户分层业务词，询问各层平均消费及平均产品种类数。',
}
DECISION = 'decisions/2026-10-17-semantic-gaps-and-realistic-questions.md'


def split_and_pilot(qs):
    rng = random.Random(SEED)
    strata = defaultdict(list)
    for q in qs:
        strata[(q['labels']['q_level'], q['labels']['persona'], q['type'])].append(q['id'])
    result, totals, report = {}, Counter(), []
    for key in sorted(strata):
        ids = sorted(strata[key])
        rng.shuffle(ids)
        half = len(ids) // 2
        counts = {'tuning': half, 'heldout': half}
        if len(ids) % 2:
            smaller = min(totals.values(), default=0)
            choices = [side for side in ('tuning', 'heldout') if totals[side] == smaller]
            if not choices:
                choices = [min(('tuning', 'heldout'), key=lambda side: totals[side])]
            counts[rng.choice(choices)] += 1
        for side, subset in [('tuning', ids[:counts['tuning']]), ('heldout', ids[counts['tuning']:])]:
            for qid in subset:
                result[qid] = side
            totals[side] += len(subset)
        report.append({'q_level': key[0], 'persona': key[1], 'type': key[2], **counts})
    eligible = [q for q in qs if result[q['id']] == 'tuning' and q['type'] in {'指标分析', '维度查找'}]
    chosen, traces = [], []
    for level in ('Q1', 'Q2', 'Q3'):
        pool = sorted([q for q in eligible if q['labels']['q_level'] == level], key=lambda q: q['id'])
        if len(pool) < 8:
            raise ValueError(f'{level}: only {len(pool)} tuning questions eligible for pilot; ask user')
        rng.shuffle(pool)
        tie_rank = {q['id']: i for i, q in enumerate(pool)}
        covered, primary, persona, types = set(), Counter(), Counter(), Counter()
        for _ in range(8):
            def priority(q):
                labels = q['labels']
                complexity = labels['complexity_source']
                return (len(set(complexity['items']) - covered), -primary[complexity['primary']],
                        -persona[labels['persona']], -types[q['type']], -tie_rank[q['id']])
            best = max(pool, key=priority)
            traces.append({'q_level': level, 'question_id': best['id'], 'priority': list(priority(best))})
            chosen.append(best['id'])
            covered.update(best['labels']['complexity_source']['items'])
            primary[best['labels']['complexity_source']['primary']] += 1
            persona[best['labels']['persona']] += 1
            types[best['type']] += 1
            pool.remove(best)
    return result, chosen, report, traces


def baseline_questions():
    return [q for name in ('cube_100', 'new') for q in json.loads(subprocess.check_output(['git', 'show', f'{BASE}:questions/{name}.yaml'], cwd=ROOT, text=True))['questions']]


def annotated_questions():
    low = json.loads((ROOT / 'audit/T06-low-discrimination.json').read_text())
    new = json.loads((ROOT / 'audit/T06-new-degeneracy.json').read_text())
    cover = json.loads((ROOT / 'audit/T06-summary-coverage.json').read_text())
    assert not low['stopped'] and len(low['flagged']) <= 15
    assert new['questions_scanned'] == 22 and not new['hits']
    qs = baseline_questions()
    split, pilot, strata, traces = split_and_pilot(qs)
    coverage_by_id = {r['question_id']: (i, r) for i, r in enumerate(cover['records'])}
    low_by_id = {r['question_id']: (i, r) for i, r in enumerate(low['records'])}
    assert set(coverage_by_id) == set(low_by_id) == {q['id'] for q in qs}
    for q in qs:
        i, cov = coverage_by_id[q['id']]
        j, discrimination = low_by_id[q['id']]
        q['split'] = split[q['id']]
        q['summary_coverage'] = cov['summary_coverage']
        q['summary_coverage_reason'] = cov['reason']
        q['labels']['summary_coverage_evidence'] = f'audit/T06-summary-coverage.json#/records/{i}'
        q['labels']['low_discrimination'] = {'criteria': discrimination['hits'], 'evidence': f'audit/T06-low-discrimination.json#/records/{j}'}
        if q['id'] in REWRITE_NOTES:
            q['labels']['external_rewrite'] = {'rewritten': True, 'reason': REWRITE_NOTES[q['id']],
                                               'decision_repository': 'main', 'decision': DECISION,
                                               'anchor_revised_sensitivity': 'excluded'}
            if q['id'] == 'Q14':
                q['labels']['external_rewrite']['threshold_change'] = {'original_usd': 10000, 'current_usd': 100000}
    return qs, pilot, strata, traces


def manifest_text(qs, pilot, strata):
    lines = ['# T06 题集清单（G2待审，未冻结）', '',
             f'基点 `{BASE}`；122题（外部100题、新题22题），136份参考。',
             '进入T06依据：T05b最终报告提交 `c8afbc1`，针对同一基点；无参考修正待办。',
             f'固定随机种子 `{SEED}`。低区分度与覆盖标注只依赖数据、参考和冻结汇总层，未读取模型结果。', '',
             '## 划分与抽样规则', '',
             '题号先排序，再按 `q_level × persona × type` 的排序分层；每层用同一个Python Random实例洗牌并对半划分。奇数层的多出一题给累计题数较少的一侧，累计相同时用同一随机流选择。',
             'pilot仅取tuning中的指标分析/维度查找题，每个Q级8题。按同一随机流给候选排序，逐次优先新增complexity_source.items覆盖，其次依次平衡primary、persona、type；最终按固定随机次序破同分。不按模型表现、低区分度或覆盖标签挑样本。', '',
             '| q_level | persona | type | tuning | heldout |', '|---|---|---|---:|---:|']
    lines += [f"| {s['q_level']} | {s['persona']} | {s['type']} | {s['tuning']} | {s['heldout']} |" for s in strata]
    lines += ['', '## 数量统计', '']
    for field in ['split', 'type', 'q_level', 'persona', 'complexity_source', 'semantic_dependency', 'summary_coverage']:
        counts = Counter()
        for q in qs:
            value = q.get(field, q['labels'].get(field))
            if isinstance(value, dict):
                counts.update(value['items'])
            else:
                counts[value] += 1
        lines += [f'### {field}', '', '| 值 | 题数 |', '|---|---:|']
        lines += [f'| {key} | {count} |' for key, count in sorted(counts.items())]
        if field in {'complexity_source', 'semantic_dependency'}:
            lines += ['', '按items多选计数，一题可计入多项。']
        lines += ['']
    main = [q for q in qs if q['type'] in {'指标分析', '维度查找'}]
    clean = [q for q in main if not q['labels']['low_discrimination']['criteria']]
    lines += [f'主结论题（指标分析+维度查找）：{len(main)}；其中排除低区分度后的主准确率分母：{len(clean)}。',
              '低区分度仍保留；T19须同时报告剔除后的主准确率与全题准确率。', '',
              '## 低区分度题', '', '| 题号 | 条款 |', '|---|---|']
    lines += [f"| {q['id']} | {'/'.join(q['labels']['low_discrimination']['criteria'])} |" for q in qs if q['labels']['low_discrimination']['criteria']]
    lines += ['', '逐题A/B/C证据见 `audit/T06-low-discrimination.json`，新题复查见 `audit/T06-new-degeneracy.json`。', '',
              '## 试跑样本', '', ', '.join(pilot), '',
              '完整抽样参数与选择轨迹见 `questions/pilot.yaml`。Q1/Q2/Q3是难度等级，每级8题，共24题。',
              '按主仓库Q79门禁裁决，24题不重抽；T12分别报告含/不含低区分度题的准确率，选模型阈值按不含的一列判定。', '',
              '## 改写与多份参考', '',
              '外部改写题：Q13、Q14、Q21、Q28、Q36、Q89；题级labels.external_rewrite记录主仓库裁决来源。Q14门槛由1万美元改为10万美元。英文锚点的修订参考敏感性列剔除这六题。',
              '参考与题意均保持基点不变；乙组保留Q39、Q76、Q84、Q48、Q86、Q91、Q121的现有多份参考。Q119两种排名当前等价，按裁决仅存一份；Q97/Q98等已有问法歧义照基点保留。', '',
              '## 汇总层覆盖', '',
              'covered要求查询的实际数据源只用ads，并在语义上有效、通过现有逐参考评分规则；任一可接受解读即可。not_covered逐题列出缺失粒度/指标/维度或需要的明细。',
              'Q19/Q108的错误订单数求和虽落入评分容差，仍标not_covered；Q53全站周表求和须有本数据订单不跨周的探查证据，不将去重指标视为一般可加。',
              '覆盖查询及结果、参考匹配、失败尝试和ads对象DDL见 `audit/T06-summary-coverage.json`；可执行查询计划见 `audit/T06-query-plan.json`。', '',
              '## 复现', '', '```sh',
              'uv run python scripts/prepare_t06.py all',
              'uv run python scripts/prepare_t06.py check', '```', '',
              '须先设置SEMDEBT_MAIN_DIR、SEMDEBT_EVAL_DIR（本worktree）、SEMDEBT_DATA_DIR；使用本仓库既有uv依赖。all通过主仓库build_summary.py包装入口只在chdb-eval重建ads，报告也写入本题库；不修改主仓库文件。',
              '未创建eval-v1 tag；G2由用户审定后另行冻结。', '']
    return '\n'.join(lines)


def prepare():
    qs, pilot, strata, traces = annotated_questions()
    for source, name in [('cube', 'cube_100'), ('new', 'new')]:
        dump(f'questions/{name}.yaml', {'questions': [q for q in qs if q['source'] == source]})
    dump('questions/pilot.yaml', {'seed': SEED, 'stratification': ['q_level', 'persona', 'type'],
         'split_algorithm': 'sorted strata; Random(seed) shuffle; half per stratum; odd member to cumulative smaller side, random tie',
         'sampling_algorithm': '8 per Q level; tuning metric/dimension only; maximize new complexity items, then balance primary/persona/type, seeded tie order',
         'questions': pilot, 'selection_trace': traces})
    (ROOT / 'questions/MANIFEST.md').write_text(manifest_text(qs, pilot, strata))
    schema = json.loads((ROOT / 'questions/schema.json').read_text())
    item = schema['properties']['questions']['items']
    for name, spec in [('summary_coverage', {'enum': ['covered', 'not_covered']}),
                       ('summary_coverage_reason', {'type': 'string', 'minLength': 1})]:
        if name not in item['required']:
            item['required'].append(name)
        item['properties'][name] = spec
    item['properties']['labels']['properties'] = {
        'summary_coverage_evidence': {'type': 'string', 'pattern': '^audit/T06-summary-coverage\\.json#/records/[0-9]+$'},
        'low_discrimination': {'type': 'object', 'required': ['criteria', 'evidence'], 'additionalProperties': False,
            'properties': {'criteria': {'type': 'array', 'uniqueItems': True, 'items': {'enum': ['A', 'B', 'C']}}, 'evidence': {'type': 'string'}}},
        'external_rewrite': {'type': 'object', 'required': ['rewritten', 'reason', 'decision_repository', 'decision', 'anchor_revised_sensitivity'],
            'properties': {'rewritten': {'const': True}, 'reason': {'type': 'string'}, 'decision_repository': {'const': 'main'}, 'decision': {'type': 'string'}, 'anchor_revised_sensitivity': {'const': 'excluded'}, 'threshold_change': {'type': 'object'}}},
    }
    item['properties']['labels']['required'] = ['summary_coverage_evidence', 'low_discrimination']
    dump('questions/schema.json', schema)
    write_report(qs, pilot, strata)
    check()


def check():
    from build_refs import validate_questions
    expected, pilot, strata, traces = annotated_questions()
    actual = questions()
    assert actual == expected, 'question metadata does not reproduce'
    assert len(actual) == 122
    assert Counter(q['source'] for q in actual) == {'cube': 100, 'new': 22}
    for s in strata:
        assert abs(s['tuning'] - s['heldout']) <= 1
    assert Counter(q['split'] for q in actual) == {'tuning': 61, 'heldout': 61}
    selected = json.loads((ROOT / 'questions/pilot.yaml').read_text())
    assert selected['questions'] == pilot and selected['selection_trace'] == traces
    assert len(set(pilot)) == 24
    pq = [q for q in actual if q['id'] in pilot]
    assert Counter(q['labels']['q_level'] for q in pq) == {'Q1': 8, 'Q2': 8, 'Q3': 8}
    assert all(q['split'] == 'tuning' and q['type'] in {'指标分析', '维度查找'} for q in pq)
    assert (ROOT / 'questions/MANIFEST.md').read_text() == manifest_text(actual, pilot, strata)
    for source in ('cube', 'new'):
        validate_questions([q for q in actual if q['source'] == source], source)
    baseline = baseline_questions()
    for old, new in zip(baseline, actual, strict=True):
        stripped = deepcopy(new)
        stripped.pop('summary_coverage')
        stripped.pop('summary_coverage_reason')
        for key in ('summary_coverage_evidence', 'low_discrimination', 'external_rewrite'):
            stripped['labels'].pop(key, None)
        stripped['split'] = old['split']
        assert stripped == old, old['id'] + ': non-T06 content changed'
    assert {q['id'] for q in actual if 'external_rewrite' in q['labels']} == set(REWRITE_NOTES)
    for path in ['refs/MANIFEST.json'] + [r['result_path'] for q in baseline for r in q['refs']]:
        assert (ROOT / path).read_bytes() == subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT), path
    new_audit = json.loads((ROOT / 'audit/T06-new-degeneracy.json').read_text())
    assert new_audit['revision'] == 'e3aaed6' and not new_audit['hits']
    low = json.loads((ROOT / 'audit/T06-low-discrimination.json').read_text())
    cover = json.loads((ROOT / 'audit/T06-summary-coverage.json').read_text())
    assert low['unit_policy_sha256'] == cover['unit_policy_sha256'] == POLICY_HASH
    assert cover['query_plan_sha256'] == hashlib.sha256((ROOT / 'audit/T06-query-plan.json').read_bytes()).hexdigest()
    for name in ('summary.sql', 'summary.yaml'):
        assert cover[f'summary_{"sql" if name.endswith("sql") else "yaml"}_sha256'] == hashlib.sha256((MAIN / 'semantic/summary' / name).read_bytes()).hexdigest()
    assert all(not q['labels']['low_discrimination']['criteria'] for q in actual if q['source'] == 'new')
    assert set(low['flagged']) <= {q['id'] for q in actual if q['source'] == 'cube'}
    for r in cover['records']:
        assert (r['summary_coverage'] == 'covered') == any(a['matched'] and a['semantically_valid'] for a in r['attempts'])
        assert r['reason']
    from snapshot_q79_boundary import compare_members
    from validate_t05 import expect_error
    fixture = {'unit_policy_sha256': 'fixture', 'value_kinds': ['other', 'amount', 'ratio'],
               'rules': {'tie_columns': [2]}, 'rows': [['a', 100.005000001, 0.1], ['b', 200, 0.2]]}
    reordered = deepcopy(fixture)
    reordered['rows'] = [['b', 200.01, 0.2], ['a', 100.005, 0.1]]
    assert POLICY.quantize_tie(fixture['rows'][0][1], 'amount') != POLICY.quantize_tie(reordered['rows'][1][1], 'amount')
    compare_members(fixture, reordered, POLICY)
    for column, value in [(0, 'different-member'), (1, 220), (2, 0.200002)]:
        invalid = deepcopy(reordered)
        invalid['rows'][0][column] = value
        expect_error(lambda: compare_members(fixture, invalid, POLICY))
    invalid = deepcopy(reordered)
    invalid['rows'][0] = list(invalid['rows'][1])
    expect_error(lambda: compare_members(fixture, invalid, POLICY))
    invalid = deepcopy(reordered)
    invalid['unit_policy_sha256'] = 'different-policy'
    expect_error(lambda: compare_members(fixture, invalid, POLICY))
    invalid = deepcopy(reordered)
    invalid['value_kinds'][1] = 'other'
    expect_error(lambda: compare_members(fixture, invalid, POLICY))
    independent = json.loads((ROOT / 'audit/T06-Q79-independent.json').read_text())
    current = json.loads((ROOT / 'audit/Q79-boundary-members.json').read_text())
    try:
        compare_members(current, independent, POLICY)
        q79_gate = {'passed': True, 'comparison': 'exact member identity and quantized ranking; other amounts use unchanged scorer tolerance', 'decision': 'decisions/2026-10-17-q79-freeze-gate-scope.md'}
    except ValueError as error:
        q79_gate = {'passed': False, 'reason': str(error), 'question': 'T06-1'}
    report = {'Q79_freeze_gate': q79_gate, 'freeze_ready': q79_gate['passed'], 'base_revision': BASE, 'questions': len(actual), 'references': sum(len(q['refs']) for q in actual),
              'split': dict(Counter(q['split'] for q in actual)), 'low_discrimination': low['flagged'],
              'pilot': pilot, 'coverage': dict(Counter(q['summary_coverage'] for q in actual)),
              'strata_max_difference': max(abs(s['tuning']-s['heldout']) for s in strata),
              'checks': 'all 122 annotations, split and pilot reproducible; metadata only; references byte-identical to base; hashes consistent'}
    dump('audit/T06-validation.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


def all_steps():
    import tempfile
    with tempfile.TemporaryDirectory(prefix='semdebt-t06-new-') as temporary:
        path = Path(temporary) / 'new.json'
        subprocess.run([sys.executable, str(ROOT / 'scripts/audit_new_question_degeneracy.py'), '--revision', 'e3aaed6', '--output', str(path)], check=True)
        result = json.loads(path.read_text())
        dump('audit/T06-new-degeneracy.json', result)
        if result['hits']:
            raise SystemExit('New question hit A/B/C; stop and ask user; do not rewrite')
    audit_low()
    build_summary()
    coverage()
    prepare()


def write_report(qs, pilot, strata):
    low = json.loads((ROOT / 'audit/T06-low-discrimination.json').read_text())
    cover = json.loads((ROOT / 'audit/T06-summary-coverage.json').read_text())
    lines = ['# T06 交付报告（待G2审定）', '',
             '基于main `e3aaed6`，分支 `T06-split-freeze`。进入依据为T05b最终报告 `c8afbc1`，主仓库BOARD已由PR #68同步。未读取模型作答或外部基准公布的系统结果。', '',
             '## 划分', '', '| 部分 | 总数 | Q1 | Q2 | Q3 | 主结论题 |', '|---|---:|---:|---:|---:|---:|']
    for side in ['tuning', 'heldout']:
        subset = [q for q in qs if q['split'] == side]
        counts = Counter(q['labels']['q_level'] for q in subset)
        lines.append(f"| {side} | {len(subset)} | {counts['Q1']} | {counts['Q2']} | {counts['Q3']} | {sum(q['type'] in {'指标分析', '维度查找'} for q in subset)} |")
    lines += ['', f'种子 `{SEED}`。13个q_level×persona×type分层，各层两侧题数差≤1；算法和分层计数见questions/MANIFEST.md。', '',
              '## 低区分度', '', '| 题 | 条款 | 证据摘要 |', '|---|---|---|']
    notes = {
        'Q07': '参考扩展14款产品，价格均为3199.99；A的恒定度量向量。完整价格排序域有376个键，C不命中。',
        'Q17': '用节假日替换周末并保留输出标签，销售金额及占比结果不变。',
        'Q29': '用周末替换节假日，日均销售差异百分比不变。',
        'Q59': '日历节假日数与周末日数均731。',
        'Q68': '用周末替换节假日，2009年两类订单数及营收结果不变。',
        'Q76': '全目录口径各品类回头客销售占比均为100%；全100答案通过。将至少2笔订单替换为至少1笔，全目录参考结果不变；乙组品类内口径仍原样保留。',
        'Q79': 'N=10，第N名量化键1.220389；边界42家≥30，完整排序域306家仅3个达成率键。',
        'Q83': '2007首购客替换为2007活跃客，三项计数均为18868、18723、17671。',
        'Q85': '最高/最低各N=5；边界分别42/55家，均≥15；每侧完整306店排序域仅3个键。',
        'Q99': '周末/工作日与节假日/非节假日互换并保留输出标签，各品类日均金额及提升百分比结果不变。',
    }
    lines += [f"| {qid} | {'/'.join(criteria)} | {notes[qid]} |" for qid, criteria in low['flagged'].items()]
    lines += ['', '共10题，不超过15题停止线。外部题保留，T19主准确率剔除、另报全量准确率。逐题A/B/C证据与B条替换前后完整结果见audit/T06-low-discrimination.json。',
              'C条另核对完整排序域的键数：Q25仅4个季节、Q46每个解读仅5类客户属性，属于问题本身有限候选域；Q22少数国家仅1位客户，不代表整道题排序退化；Q74使用完整产品排序域而非只看前3结果。除Q79/Q85外未发现完整大候选域折叠为极少值。',
              '新客窗口实测：Q26两个季度分别18015/853；Q114六个月末分别13140/15910/18015/5894/2868/732，与窗口活跃客户的对照不同，均未命中。Q81/Q96与忽略首单的分群结果不同。',
              'Q101–Q122按基点全部复查，0题命中；没有自行改题。新题逐参考度量分布、口径替换及Top-N边界见audit/T06-new-degeneracy.json。', '',
              '## 试跑24题', '', '| Q级 | 题号 |', '|---|---|']
    by_id = {q['id']: q for q in qs}
    for level in ['Q1', 'Q2', 'Q3']:
        ids = [qid for qid in pilot if by_id[qid]['labels']['q_level'] == level]
        lines.append(f"| {level} | {', '.join(ids)} |")
    lines += ['', '24题不重抽；T12报告含/不含低区分度两列，选模型阈值使用不含的一列。全部来自tuning，且仅为指标分析/维度查找。固定种子分层后，用新增复杂度覆盖、primary/persona/type平衡与固定随机破同分规则抽样；轨迹在questions/pilot.yaml。', '',
              '## L1.5S覆盖', '', '| 范围 | covered | not_covered |', '|---|---:|---:|']
    for name, subset in [('全部', qs), ('tuning', [q for q in qs if q['split']=='tuning']), ('heldout', [q for q in qs if q['split']=='heldout'])] + [(level, [q for q in qs if q['labels']['q_level']==level]) for level in ['Q1','Q2','Q3']]:
        counts = Counter(q['summary_coverage'] for q in subset)
        lines.append(f"| {name} | {counts['covered']} | {counts['not_covered']} |")
    lines += ['', '只以ads汇总表和维度表作答。覆盖查询通过现有评分器及逐参考rules；多份可接受解读命中任一即可。缺字段/粒度的题给出结构证据，有可疑替代源时保存执行失败匹配证据。',
              'Q19/Q108：跨画像/季度累加订单数会重复，虽然评分容差内判对，仍不算覆盖。Q53：数据探查确认2009年378070个订单没有跨周×年份分区重复，全站周订单数可在本冻结数据上复现；不推广为去重指标的一般可加性。',
              'Q113：先用ads.dim_date补齐12个月，并将无销售月补0，再识别连续未达均摊目标时段，33段全部复现参考。',
              '主仓库build_summary.py默认指向chdb；本卡通过导入包装仅覆盖chdb_dir()和报告路径，在chdb-eval内重建ads并执行全部既有汇总对账，未改冻结脚本/SQL/YAML。', '',
              '## 改写与多解', '',
              '题集labels.external_rewrite记录Q13、Q14、Q21、Q28、Q36、Q89；Q14同时记录10000→100000美元门槛变化。来源为主仓库2026-10-17-semantic-gaps-and-realistic-questions.md第三、五、六、七节。六题从英文锚点修订参考敏感性对照列剔除，英文原始锚点不受影响。',
              '乙组与其他已批准多解均保持基点内容，不撤回参考、不新增口径。所有136份CSV和refs/MANIFEST.json逐字节校验与基点一致；问句、SQL、rules逐题结构校验一致。', '',
              '## 验证与复现', '', '```sh', 'uv run python scripts/prepare_t06.py all', 'uv run python scripts/prepare_t06.py check', 'uv run python scripts/validate_rules.py', '```', '',
              '须设置SEMDEBT_MAIN_DIR、SEMDEBT_EVAL_DIR（本worktree）、SEMDEBT_DATA_DIR。all会重建可再生的chdb-eval/ads并更新T06工件；不要同时运行另一个打开chdb-eval的进程。check只检查已交付工件、基点、参考哈希、划分和统计，不重新执行SQL。',
              '运行条件与量纲策略哈希随JSON保存；每份参考的完整value_kinds/value_types沿用未改变的refs/MANIFEST.json。没有安装新依赖或读取模型输出。门禁回归检查覆盖半分币差异与乱序通过，以及换成员、改量化排名键、金额超容差、重复成员和策略版本/量纲不符拒绝。', '',
              '## Q79门禁裁决已落实（T06-1）', '',
              '已提交pandas结果c8afbc1的42家店名集合和第N名量化键完全一致；原门禁额外要求完整行所有量化值相等。Damascus No.1 Store的目标金额：参考10304326.61、pandas10304326.60；Osaka No.1 Store的实际金额：参考13592892.53、pandas13592892.52。均位于半分币舍入边界。按主仓库decisions/2026-10-17-q79-freeze-gate-scope.md，仅严格核对成员与量化排名键，其余金额调用既有评分器容差；冻结检查现已通过，评分器未改。',
              '独立结果来源、提交号、CSV哈希和42行值保存在audit/T06-Q79-independent.json；原问题与最终裁决记入decisions/open-questions.md。复现当前门禁：uv run python scripts/snapshot_q79_boundary.py --freeze-check --independent-snapshot audit/T06-Q79-independent.json。', '',
              '## G2待用户审定', '', '- [x] T06-1：已按主仓库裁决修正比较范围，Q79冻结检查通过。', '- [ ] 同意61/61划分与24题试跑样本。', '- [ ] 同意10道低区分度标注及49/73覆盖标注。',
              '- [ ] B条首单组独立抽查由Claude Code执行；按用户2026-10-18指令，本PR不等待该抽查。', '- [ ] 用户G2审定后另行决定eval-v1 tag；本PR不打tag。', '']
    (ROOT / 'audit/T06-report.md').write_text('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['audit', 'build-summary', 'coverage', 'prepare', 'check', 'all'])
    args = parser.parse_args()
    {'audit': audit_low, 'build-summary': build_summary, 'coverage': coverage, 'prepare': prepare, 'check': check, 'all': all_steps}[args.action]()


if __name__ == '__main__':
    main()
