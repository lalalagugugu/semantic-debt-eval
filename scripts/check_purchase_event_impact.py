#!/usr/bin/env python
"""Audit both approved purchase-event definitions across all 122 questions.

Run without --apply to execute and report first. After reviewing that report,
--apply adds only distinct positive-quantity outcomes; build_refs.py must then
recompute every active reference. Frozen monetary and order metrics are kept.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

import yaml
from chdb import session
from build_refs import effective_rules, load_unit_policy, postprocess_reference

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT/'audit/reviews/2026-10-16-pre-purchase-questions.yaml'
REPORT = ROOT/'audit/T05-purchase-events.json'
EVENTS = {
 'Q03':'购买过的客户集合', 'Q26':'首次购买／新客（约定14）',
 'Q32':'连续三个年份购买', 'Q33':'同订单共购',
 'Q36':'最近购买／客户分层（约定13）', 'Q76':'回头客订单事件',
 'Q80':'首购至末购时长', 'Q81':'首购年份与终身消费',
 'Q83':'首购与后续年份留存', 'Q88':'四季度均购买',
 'Q89':'最近购买分层及购买产品种类', 'Q91':'线上消费者集合与收入相关',
 'Q96':'首次购买年份与后续购买', 'Q114':'近90天首次购买／新客（约定14）',
 'Q115':'固定已购群体的最近购买分层（约定13）',
 'Q116':'首购与90日复购', 'Q120':'当年购买客户集合与收入相关',
 'Q122':'已售产品及共购，全部订单分母固定',
}
ALL_ORDER_METRICS = {'Q19','Q53','Q63','Q66','Q68','Q100','Q103','Q108'}


def replace_once(sql, old, new):
    if sql.count(old) != 1:
        raise ValueError(f'expected one occurrence: {old}')
    return sql.replace(old,new)


def positive_sql(qid, ref):
    sql=ref['sql']
    if qid=='Q122':
        return replace_once(sql,"p.BrandName='Contoso'","p.BrandName='Contoso' AND f.SalesQuantity>0")
    if qid=='Q32':
        return replace_once(sql,'count(DISTINCT toYear(DateKey))','countDistinctIf(toYear(DateKey),SalesQuantity>0)')
    if qid=='Q76':
        if 'AS n_orders' in sql:
            return replace_once(sql,'countDistinct(SalesOrderNumber) AS n_orders','countDistinctIf(SalesOrderNumber,SalesQuantity>0) AS n_orders')
        sql=replace_once(sql,'f.SalesAmount AS SalesAmount,','f.SalesAmount AS SalesAmount,f.SalesQuantity AS SalesQuantity,')
        return replace_once(sql,'countDistinct(SalesOrderNumber) AS orders','countDistinctIf(SalesOrderNumber,SalesQuantity>0) AS orders')
    if qid in {'Q91','Q120'}:
        return sql.replace('GROUP BY CustomerKey','GROUP BY CustomerKey HAVING countIf(SalesQuantity>0)>0',1)
    if qid=='Q88':
        return sql.replace('FROM retail.FactOnlineSales','FROM (SELECT * FROM retail.FactOnlineSales WHERE SalesQuantity>0)',1)
    if qid=='Q81':
        return sql.replace('FROM retail.FactOnlineSales','FROM (SELECT * FROM retail.FactOnlineSales WHERE SalesQuantity>0)',1)
    if qid=='Q89':
        sql=replace_once(sql,'MAX(DateKey) AS last_purchase','maxIf(DateKey,SalesQuantity>0) AS last_purchase')
        sql=replace_once(sql,'countDistinct(ProductKey) AS distinct_products','countDistinctIf(ProductKey,SalesQuantity>0) AS distinct_products')
        return sql.replace('GROUP BY CustomerKey','GROUP BY CustomerKey HAVING countIf(SalesQuantity>0)>0',1)
    # Only event/date domains use this substitution, never financial/order totals.
    sql,n=re.subn(r'\b(FROM|JOIN) retail\.FactOnlineSales\b',r'\1 (SELECT * FROM retail.FactOnlineSales WHERE SalesQuantity>0)',sql)
    if n==0:
        raise ValueError(f'{qid}: no purchase source found')
    return sql


def execute(s, q, ref, sql, policy):
    rules=effective_rules(q,ref)
    n=rules['top_n']
    if n is not None:
        sql,replacements=re.subn(rf'\bLIMIT\s+{n}\s*;?\s*$','',sql,flags=re.I)
        if replacements!=1:
            raise ValueError('missing final Top-N limit')
    payload=json.loads(str(s.query(sql,'JSONCompact')))
    meta,rows,_=postprocess_reference(ref.get('postprocess'),payload['meta'],payload['data'],policy)
    kinds=rules['value_kinds']
    if [c['type'] for c in meta]!=rules['value_types']:
        raise ValueError(f'{q["id"]}: variant changed declared types')
    if rules.get('selection'):
        raise ValueError('purchase-event cohort unexpectedly overlaps grouped selection; review explicitly')
    if n is not None:
        key=lambda row: tuple(policy.quantize_tie(row[i],kinds[i]) for i in rules['tie_columns'])
        descending=not bool(re.search(r'\bASC\s*(?:LIMIT\s+\d+)?\s*;?\s*$',ref['sql'],re.I))
        rows.sort(key=lambda row:json.dumps(row,ensure_ascii=False))
        rows.sort(key=key,reverse=descending)
        if len(rows)<n:
            raise ValueError('insufficient Top-N rows')
        cut=n
        while cut<len(rows) and key(rows[cut])==key(rows[n-1]):
            cut+=1
        rows=rows[:cut]
    quantized=[json.dumps([policy.quantize_tie(v,k) for v,k in zip(row,kinds,strict=True)],ensure_ascii=False,default=str) for row in rows]
    return {'sql':sql,'meta':meta,'rows':rows},Counter(quantized)


def signature(counter):
    return hashlib.sha256(json.dumps(sorted(counter.items()),ensure_ascii=False).encode()).hexdigest()


def apply(report):
    if report['baseline_sha256']!=hashlib.sha256(BASELINE.read_bytes()).hexdigest():
        raise ValueError('audit baseline changed')
    baseline=yaml.safe_load(BASELINE.read_text())['questions']
    current=sum([yaml.safe_load((ROOT/f'questions/{name}.yaml').read_text())['questions'] for name in ['cube_100','new']],[])
    if current!=baseline:
        raise ValueError('active questions changed since audit; do not overwrite concurrent edits')
    by_id={q['id']:q for q in baseline}
    for record in report['records']:
        q=by_id[record['question_id']]
        if record['question_id'] not in EVENTS:
            continue
        q['scoring_notes']+='\n购买事件双解：全部行与SalesQuantity>0均可；实际结果相同的购买定义共用参考。逐参考比较及去重映射见audit/T05-purchase-events.json。'
        for ref in q['refs']:
            comparison=next(x for x in record['references'] if x['result_path']==ref['result_path'])
            ref['interpretation']+='；购买事件=全部行／正销量（结果相同）' if comparison['quantized_equal'] else '；购买事件=全部行'
        for addition in record['additions']:
            q['refs'].append(addition)
    for source,filename in [('cube','cube_100'),('new','new')]:
        path=ROOT/f'questions/{filename}.yaml'
        path.write_text(json.dumps({'questions':[q for q in baseline if q['source']==source]},ensure_ascii=False,indent=2)+'\n')
    print(f"Applied {report['added_references']} additional references; recompute all references next.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if args.apply:
        apply(json.loads(REPORT.read_text()))
        return
    policy,policy_hash=load_unit_policy()
    questions=yaml.safe_load(BASELINE.read_text())['questions']
    if len(questions)!=122 or set(EVENTS)-{q['id'] for q in questions}:
        raise ValueError('incomplete 122-question scan')
    raw=Path(os.environ['SEMDEBT_DATA_DIR'])/'t05-finalize'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-purchase-events-full')
    raw.mkdir(parents=True,exist_ok=False)
    records=[]
    s=session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR'])/'chdb-eval'))
    try:
        s.query('SET max_threads=1')
        s.query('SET max_execution_time=0')
        s.query('SET output_format_json_quote_denormals=1')
        for q in questions:
            qid=q['id']
            record={'question_id':qid,'scope':EVENTS.get(qid,'非购买事件题；维度、财务金额、库存、目标或统计观察单位不改'), 'compared':qid in EVENTS,'references':[],'additions':[]}
            if qid in ALL_ORDER_METRICS:
                record['scope']='订单数／客单价采用冻结的全部去重订单号；不改为购买事件数'
            if qid in EVENTS:
                known={}
                comparisons=[]
                for ref in q['refs']:
                    data,all_rows=execute(s,q,ref,ref['sql'],policy)
                    file=raw/(Path(ref['result_path']).stem+'-all_rows.json')
                    file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
                    known[signature(all_rows)]=ref['result_path']
                    comparisons.append((ref,all_rows))
                next_index=len(q['refs'])+1
                for ref,all_rows in comparisons:
                    sql=positive_sql(qid,ref)
                    data,positive=execute(s,q,ref,sql,policy)
                    file=raw/(Path(ref['result_path']).stem+'-positive_sales.json')
                    file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
                    sig=signature(positive)
                    mapped=known.get(sig)
                    addition=None
                    if mapped is None:
                        addition=deepcopy(ref)
                        addition.update(sql=sql,interpretation=ref['interpretation']+'；购买事件=SalesQuantity>0',result_path=f"refs/{'cube' if q['source']=='cube' else 'new'}/{qid}-{next_index}.csv")
                        addition['rules']=deepcopy(effective_rules(q,ref))
                        addition['rules']['value_types']=[column['type'] for column in data['meta']]
                        mapped=addition['result_path']
                        known[sig]=mapped
                        record['additions'].append(addition)
                        next_index+=1
                    item={'result_path':ref['result_path'],'quantized_equal':all_rows==positive,'all_rows_count':sum(all_rows.values()),'positive_sales_count':sum(positive.values()),'removed_rows':sum((all_rows-positive).values()),'added_rows':sum((positive-all_rows).values()),'all_rows_signature':signature(all_rows),'positive_sales_signature':sig,'positive_sql_sha256':hashlib.sha256(sql.encode()).hexdigest(),'positive_maps_to':mapped,'new_reference':addition is not None}
                    record['references'].append(item)
                    if addition is None and not item['quantized_equal']:
                        for prior in record['additions']:
                            if prior['result_path']==mapped:
                                prior['interpretation']+='；亦覆盖：'+ref['interpretation']+'（正销量结果相同）'
                    print(qid,ref['result_path'],'same' if item['quantized_equal'] else 'DIFFERENT',mapped,flush=True)
            records.append(record)
    finally:
        s.close()
    report={'status':'executed_both_algorithms_before_full_rebuild','baseline_sha256':hashlib.sha256(BASELINE.read_bytes()).hexdigest(),'unit_policy_sha256':policy_hash,'raw_directory':str(raw),'scanned_questions':122,'compared_questions':sum(r['compared'] for r in records),'different_questions':sum(any(not x['quantized_equal'] for x in r['references']) for r in records),'added_references':sum(len(r['additions']) for r in records),'baseline_references':sum(len(q['refs']) for q in questions),'records':records}
    report['final_references']=report['baseline_references']+report['added_references']
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# 购买事件双解：用户裁决与122题全量扫描','',
    '用户批准同时接受购买=全部行、购买=SalesQuantity>0；不修改冻结汇总层或Cube模型。相同结果不增加重复购买解读参考，既有其他多解（窗口、排名等）保留。Q122全部订单分母固定为全部去重订单号。',
    '', '实测：2009年32,050条零销量纯退货记录，SalesAmount均为0；81位客户首购日、112位末购日受影响；378,070个订单号中2,044个只含零销量行。',
    '',f"扫描{report['scanned_questions']}题，实际执行双算法{report['compared_questions']}题；{report['different_questions']}题输出不同，新增{report['added_references']}份参考：{report['baseline_references']}→{report['final_references']}。以下结果先于全量重算报告。",'',
    '金额累计保持全部财务行；Q32、Q76、Q81、Q88、Q89、Q91、Q120只改购买资格／日期／种类，保留消费金额和订单总体。Q122仅对产品篮成员施加正销量条件，空篮订单保留在分母。比较在固定量纲精度下按成员多重集进行，Top-N包含完整边界组；不将结果微小浮点差当作口径差异。',
    '', '| 题号 | 路径／范围 | 双算法结果 | 新增参考 |','|---|---|---|---:|']
    for r in records:
        detail='；'.join(Path(x['result_path']).stem+('相同' if x['quantized_equal'] else '不同') for x in r['references']) or '不适用（定义不变）'
        lines.append(f"| {r['question_id']} | {r['scope']} | {detail} | {len(r['additions'])} |")
    lines+=['','复现：`uv run python scripts/check_purchase_event_impact.py`；核对报告后 `uv run python scripts/check_purchase_event_impact.py --apply`，再 `uv run python scripts/build_refs.py --refresh-rules`。详细SQL在预购买解读快照和脚本中，原始结果保存在JSON记载的SEMDEBT_DATA_DIR目录。本文不是T05b独立证据。','']
    (ROOT/'audit/T05-purchase-events.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in report.items() if k!='records'},ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
