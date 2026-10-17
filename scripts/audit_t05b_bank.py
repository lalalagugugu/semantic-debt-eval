#!/usr/bin/env python
"""Review all 122 questions for premature rounding, event scope and labels."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re

from build_refs import effective_rules, load_selection_policy, load_unit_policy, postprocess_reference
from check_purchase_event_impact import EVENTS, positive_sql

ROOT = Path(__file__).resolve().parent.parent
# These are reviewed audit classifications, never scorer exceptions.
EARLY_ROUNDING = {
    'Q27': '利润率取整后成为Top-N排序键',
    'Q34': '周转率取整别名用于最终排序',
    'Q45': '平效取整别名用于最终排序',
    'Q71': '取整销售额作为分组选择及最终排序输入',
    'Q75': '增长率取整别名用于最终排序',
    'Q76': '回头客占比取整别名用于最终排序',
    'Q77': '输出sales别名与输入同名，窗口／环比不能依赖别名解析取整',
    'Q79': '达成率取整后成为Top-N排序键',
    'Q80': '平均活跃天数取整别名用于最终排序',
    'Q85': 'perf先取整达成率，再进入两路分组Top-N',
    'Q87': '可售天数取整后成为Top-N排序键',
    'Q88': 'SQL按实际消费排序，但构建器从取整投影提取Top-N键；金额全局两位量化不变',
}
LABELS = {
    'Q36': ['Active', 'At Risk', 'Churned'],
    'Q48': ['High Downtime', 'Low Downtime'],
    'Q84': ['A', 'B', 'C'],
    'Q85': ['TOP', 'BOTTOM'],
    'Q89': ['Active', 'At Risk', 'Churned'],
    'Q115': ['活跃', '有流失风险', '已流失'],
    'Q120': ['全体', '职业内'],
}
FIXED_ORDER_METRICS = {'Q13','Q19','Q28','Q53','Q63','Q66','Q68','Q100','Q103','Q108'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(sess, question, ref, sql, unit, selection):
    rules = effective_rules(question, ref)
    n = rules['top_n']
    if n:
        sql, count = re.subn(rf'\bLIMIT\s+{n}\s*;?\s*$', '', sql, flags=re.I)
        if count != 1:
            raise ValueError('Top-N domain must end in its declared LIMIT')
    data = json.loads(str(sess.query(sql, 'JSONCompact')))
    meta, rows, details = postprocess_reference(ref.get('postprocess'), data['meta'], data['data'], unit)
    kinds = rules['value_kinds']
    if rules.get('selection'):
        rows, details = selection.complete_selection(rows, rules['selection'], kinds)
    elif n:
        key = lambda row: tuple(unit.quantize_tie(row[i], kinds[i]) for i in rules['tie_columns'])
        descending = not bool(re.search(r'\bASC\s*LIMIT', ref['sql'], re.I))
        rows.sort(key=key, reverse=descending)
        cut = n
        while cut < len(rows) and key(rows[cut]) == key(rows[n-1]):
            cut += 1
        rows = rows[:cut]
    normalized = Counter(json.dumps([unit.quantize_tie(v,k) for v,k in zip(row,kinds,strict=True)], ensure_ascii=False, default=str) for row in rows)
    return rows, normalized


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute-events', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('choose a new append-only audit output')
    before = json.loads((ROOT/'audit/reviews/2026-10-16-before-t05b-corrections.json').read_text())['questions']
    current = sum([json.loads((ROOT/f'questions/{f}.yaml').read_text())['questions'] for f in ('cube_100','new')], [])
    originals = {q['id']:q for q in before}
    events = {**EVENTS, 'Q100': '客户级购买频次及客单价P90交集；订单指标既是度量也是客户集合筛选键'}
    unit, policy_sha = load_unit_policy()
    selection, _ = load_selection_policy()
    sess = None
    comparisons = 0
    records = []
    try:
        if args.execute_events:
            from chdb import session
            sess = session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR'])/'chdb-eval'))
            sess.query('SET max_threads=1'); sess.query('SET max_execution_time=0')
        for question in current:
            qid = question['id']
            old = originals[qid]
            calls = [{'reference': r['result_path'], 'sql_sha256': hashlib.sha256(r['sql'].encode()).hexdigest(),
                      'round_calls': len(re.findall(r'\b(?:round\w*|floor|ceil\w*|trunc\w*)\s*\(',r['sql'],re.I))} for r in old['refs']]
            role = ('purchase_event' if qid in events else 'fixed_order_metric' if qid in FIXED_ORDER_METRICS else 'financial_measure' if any('FactOnlineSales' in r['sql'] or 'FactSales ' in r['sql'] for r in old['refs']) else 'not_purchase_event')
            reason = (events[qid] if qid in events else '题面统计全部订单／交易指标；按冻结定义保留所有去重订单号，不自行改分母' if role=='fixed_order_metric' else '题面问财务金额、销量或其比较；不因退货行过滤财务事实；金额门槛／金额排名不是购买事件' if role=='financial_measure' else '维度、库存、计划或设备等口径，不以线上购买事件构造客户集合')
            item = {'question_id': qid, 'rounding': {'references': calls, 'premature': qid in EARLY_ROUNDING,
                    'reason': EARLY_ROUNDING.get(qid, '仅最终展示取整，未取整值进入窗口／比较／聚合／排序' if any(r['round_calls'] for r in calls) else '无数值取整函数'),
                    'current_reference_sha256': {r['result_path']:hashlib.sha256(r['sql'].encode()).hexdigest() for r in question['refs']}},
                    'purchase_event': {'role':role,'reason':reason,'prior_scan_missed':qid=='Q100','comparisons':[]},
                    'constant_output_labels': LABELS.get(qid, []),
                    'label_action': '题面明确标签' if qid in {'Q115','Q120'} else '外部题只列出，题面不改' if qid in LABELS else '无额外语义常量标签；数据值、筛选常量、日期单位和类型字面量不属于输出标签'}
            if qid in events and sess is not None:
                for ref in question['refs']:
                    if 'SalesQuantity>0' in ref['sql'] or 'SalesQuantity > 0' in ref['sql']:
                        continue
                    alternate = positive_sql(qid,ref) if qid!='Q100' else ref['sql'].replace('FROM retail.FactOnlineSales','FROM (SELECT * FROM retail.FactOnlineSales WHERE SalesQuantity>0)',1)
                    left, a = execute(sess, question, ref, ref['sql'], unit, selection)
                    right, b = execute(sess, question, ref, alternate, unit, selection)
                    signature = lambda rows: hashlib.sha256(json.dumps(sorted(rows.items()),ensure_ascii=False).encode()).hexdigest()
                    item['purchase_event']['comparisons'].append({'reference':ref['result_path'],'all_rows':len(left),'positive_rows':len(right),'quantized_equal':a==b,'all_signature':signature(a),'positive_signature':signature(b),
                       'only_all_multiplicity':sum((a-b).values()),'only_positive_multiplicity':sum((b-a).values())})
                    comparisons += 1
            records.append(item)
            print(f'audited {qid}',flush=True)
    finally:
        if sess is not None:
            sess.close()
    result = {'questions_scanned':len(records),'unit_policy_sha256':policy_sha,'events_executed':args.execute_events,'event_questions':len(events),'event_comparisons':comparisons,
              'prior_Q100_miss_reason':'旧脚本ALL_ORDER_METRICS把Q100与纯订单总数一起排除，白名单EVENTS只关注首末购／复购／共购，未检查订单计数作为客户分位筛选与客单价分母的复合角色。新扫描逐题审阅题意、聚合输入、客户集合与后处理，Q100归入购买事件而非纯订单度量。',
              'question_sha256':{f:digest(ROOT/f'questions/{f}.yaml') for f in ('cube_100','new')},'records':records}
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')


if __name__ == '__main__':
    main()
