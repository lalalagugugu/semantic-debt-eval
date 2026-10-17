#!/usr/bin/env python
"""Audit the approved three summary rewrites without using model outputs."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from build_refs import effective_rules, load_unit_policy
from check_rules_impact import csv_rows

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,os.environ['SEMDEBT_MAIN_DIR'])
from harness.scorer import score


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--customer-threshold',type=int,required=True,help='User-approved Q14 amount, never inferred from results')
    args=parser.parse_args()
    output=ROOT/'audit/2026-10-17-summary-rewrites.json'
    if output.exists():raise ValueError('Audit output already exists; archive it before a new run')
    revision='180e5116fe671fe6ae8aedfd76bb2e020ec527d0'
    def previous(path):return json.loads(subprocess.check_output(['git','show',f'{revision}:{path}'],cwd=ROOT,text=True))
    before={q['id']:q for name in ('cube_100','new') for q in previous(f'questions/{name}.yaml')['questions']}
    old_manifest=previous('refs/MANIFEST.json')['records']
    old_records={r['question_id']:r for r in old_manifest}
    old_paths={r['result_path']:r for r in old_manifest}
    current={q['id']:q for name in ('cube_100','new') for q in json.loads((ROOT/f'questions/{name}.yaml').read_text())['questions']}
    records={r['result_path']:r for r in json.loads((ROOT/'refs/MANIFEST.json').read_text())['records']}
    changed={qid for qid in current if current[qid]!=before[qid]}
    assert changed=={'Q14','Q21','Q122'},changed
    for qid,q in current.items():
        if qid not in changed:
            assert all(records[r['result_path']]==old_paths[r['result_path']] for r in q['refs']),qid
    policy,unit_sha=load_unit_policy();items=[]
    for qid,positions in [('Q14',[0]),('Q21',[2]),('Q122',[0,1,2,3,4])]:
        q=current[qid];ref=q['refs'][0];rec=records[ref['result_path']];rows=csv_rows(rec);rule=effective_rules(q,ref)
        zeros=deepcopy(rows);blanks=deepcopy(rows)
        for row in zeros:
            for i in positions:row[i]=0
        for row in blanks:
            for i in positions:row[i]=None
        profiles=[{'column':rec['columns'][i]['name'],'distinct':len({policy.quantize_tie(r[i],rule['value_kinds'][i]) for r in rows}),
                   'minimum':min(r[i] for r in rows),'maximum':max(r[i] for r in rows)} for i in positions]
        trivial={'empty':score([],[rows],rule),'zero':score(zeros,[rows],rule),'blank':score(blanks,[rows],rule)}
        a_hit=any(v=='correct' for v in trivial.values()) or (len(rows)>1 and all(p['distinct']==1 for p in profiles))
        assert not a_hit
        items.append({'question_id':qid,'old_text_zh':before[qid]['text_zh'],'new_text_zh':q['text_zh'],
                      'previous_reference_rows':old_records[qid]['row_count'],'reference_rows':len(rows),
                      'A':{'hit':a_hit,'profiles':profiles,'trivial_candidates':trivial},
                      'B':{'hit':False,'applicable':False,'reason':'不涉及首单/新客/复购或节假日/周末；另列原考点的错误算法敏感性'},
                      'C':{'hit':False,'applicable':False,'reason':'无Top-N/排序选择'}})
    from chdb import session
    s=session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR'])/'chdb-eval'))
    try:
        s.query('SET max_threads=1');s.query('SET max_execution_time=0')
        def query(sql):return json.loads(str(s.query(sql,'JSONCompact')))['data']
        q14=query(f'SELECT count(),min(spend),max(spend),countIf(spend>10000),countIf(spend>{args.customer_threshold}) FROM (SELECT CustomerKey,sum(SalesAmount) AS spend FROM retail.FactOnlineSales GROUP BY CustomerKey)')[0]
        row_filter=query(f'SELECT uniqExact(CustomerKey) FROM retail.FactOnlineSales WHERE SalesAmount>{args.customer_threshold}')[0][0]
        items[0]['capability']={'before':'客户粒度累计销售后的HAVING筛选','after':'相同客户粒度筛选后计数',
            'threshold':args.customer_threshold,'all_customers':q14[0],'minimum_spend':q14[1],
            'original_10000_members':q14[3],'selected_members':q14[4],'wrong_filter_fact_rows_count':row_filter,
            'ignoring_threshold_changes_result':q14[0]!=q14[4],
            'ignoring_threshold_verdict':score([[q14[0]]],[csv_rows(records['refs/cube/Q14-1.csv'])],effective_rules(current['Q14'],current['Q14']['refs'][0])),
            'retained':q14[0]!=q14[4] and row_filter!=q14[4]}
        assert q14[4]==385 and items[0]['capability']['retained']
        wrong=query('SELECT s.StoreKey,sum(i.OnHandQuantity) FROM retail.FactInventory i JOIN retail.DimStore s ON i.StoreKey=s.StoreKey WHERE i.DateKey=(SELECT max(DateKey) FROM retail.FactInventory) GROUP BY s.StoreKey')
        correct=csv_rows(records['refs/cube/Q21-1.csv']);left={r[0]:r[2] for r in correct};right={r[0]:r[1] for r in wrong}
        dates=query('SELECT count(),uniqExact(d),min(d),max(d) FROM (SELECT StoreKey,ProductKey,max(DateKey) AS d FROM retail.FactInventory GROUP BY StoreKey,ProductKey)')[0]
        items[1]['capability']={'before':'门店×产品各自最近快照的当前库存','after':'逐门店汇总同一批最近快照',
            'latest_store_products':dates[0],'distinct_latest_dates':dates[1],'latest_date_range':dates[2:],
            'correct_stores':len(left),'wrong_global_latest_stores':len(right),
            'wrong_global_latest_different_stores':sum(left.get(k)!=right.get(k) for k in left.keys()|right.keys()),'retained':True}
        sql=before['Q122']['refs'][0]['sql']
        nonzero=query('SELECT avg(support_ratio),avg(confidence_1_to_2_ratio),avg(confidence_2_to_1_ratio),avg(lift_ratio),count() FROM ('+sql+') WHERE support_ratio>0')[0]
        domain=query('SELECT count(),countIf(support_ratio>0) FROM ('+sql+')')[0]
        positive_sql=current['Q122']['refs'][0]['sql'].replace('WHERE toYear(f.DateKey)=2009 GROUP BY','WHERE toYear(f.DateKey)=2009 AND f.SalesQuantity>0 GROUP BY')
        assert positive_sql!=current['Q122']['refs'][0]['sql']
        positive=query(positive_sql)[0]
        summary_row=csv_rows(records['refs/new/Q122-1.csv'])[0]
        means=summary_row[1:]
        items[2]['capability']={'before':'全部产品对共购支持度、双向置信度、lift','after':'同一产品对域四项派生指标的等权均值',
            'pair_domain':domain[0],'nonzero_pairs':domain[1],'zero_pairs':domain[0]-domain[1],
            'all_orders':summary_row[0],'correct_means':means,'wrong_drop_zero_pairs_means':nonzero[:4],
            'wrong_positive_only_orders':positive[0],'wrong_positive_only_means':positive[1:],
            'drop_zero_pairs_changes_result':any(not policy.quantize_tie(a,'ratio')==policy.quantize_tie(b,'ratio') for a,b in zip(means,nonzero[:4],strict=True)),
            'retained':True}
        q122_rules=effective_rules(current['Q122'],current['Q122']['refs'][0])
        items[2]['capability']['wrong_drop_zero_pairs_verdict']=score([[summary_row[0],*nonzero[:4]]],[[summary_row]],q122_rules)
        items[2]['capability']['wrong_positive_only_verdict']=score([positive],[[summary_row]],q122_rules)
        ratio_rules={**q122_rules,'value_kinds':q122_rules['value_kinds'][1:],'value_types':q122_rules['value_types'][1:]}
        items[2]['capability']['means_only_positive_filter_verdict']=score([positive[1:]],[[list(means)]],ratio_rules)
        assert items[2]['capability']['wrong_drop_zero_pairs_verdict']=='wrong'
        assert items[2]['capability']['wrong_positive_only_verdict']=='wrong'
    finally:s.close()
    report={'baseline_commit':revision,'decision_sections':[6,7],'Q13_Q28_wording':'user_confirmed',
            'customer_threshold':args.customer_threshold,'records':items,'unit_policy_sha256':unit_sha,
            'unchanged_questions_verified':119,'new_question_audit':'audit/2026-10-17-summary-new-question-check.json',
            'anchor_revised_sensitivity_exclusions':['EN13','EN14','EN21','EN28','EN36','EN89']}
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n')
    lines=['# Q14、Q21、Q122汇总改写验收','',
           '依据：主仓库2026-10-17裁决第六、七节；Q13/Q28措辞已确认。本报告三题的新题面交用户确认，PR15保持草稿，未冻结。','',
           '| 题号 | 新题面 | 旧参考行数 | 新参考行数 | 保留的能力 |','|---|---|---:|---:|---|']
    abilities={'Q14':'按客户累计销售→聚合后门槛筛选→人数汇总',
               'Q21':'门店×产品各取最近快照→跨产品汇总当前库存，保留半可加粒度',
               'Q122':'订单篮子去重、全部产品对、支持度/双向置信度/lift→等权均值，保留全部订单分母'}
    for item in items:
        lines.append(f"| {item['question_id']} | {item['new_text_zh']} | {item['previous_reference_rows']:,} | {item['reference_rows']} | {abilities[item['question_id']]} |")
    c14,c21,c122=[r['capability'] for r in items]
    lines += ['', '## A/B/C与能力敏感性','',
              '- A：三题空结果、全零数值、空数值候选均判错；Q21库存有303个不同值。Q14/Q122单行汇总是计算结果，不因只有一行即称为数据退化常数。',
              '- B：三题均不涉及裁决限定的首单/新客/复购或节假日/周末，记不适用；以下额外比较原考点的常见错误算法，不冒充B条指定实验。',
              '- C：三题均无Top-N或排序选择，不适用。',
              f"- Q14：正确{c14['selected_members']}人；忽略门槛为{c14['all_customers']}人，先筛单条销售记录再去重为{c14['wrong_filter_fact_rows_count']}人。原1万美元门槛得到全部客户，命中原题退化；用户第七节批准改为10万美元。原门槛、新门槛及理由须在T19披露。",
              f"- Q21：600,241个门店×产品最近快照分布在{c21['distinct_latest_dates']}个日期。错误地只用全表最大日，{c21['wrong_global_latest_different_stores']}家门店的库存均不同；原快照粒度能力保留。",
              f"- Q122：在{c122['pair_domain']:,}个产品对上等权汇总，包含{c122['zero_pairs']:,}个零共购对。删零对后的均值作答判错；原共购及组合比率计算仍不可省略。",
              f"- Q122：正确总体{c122['all_orders']:,}个订单，仅正销量行错误算法为{c122['wrong_positive_only_orders']:,}个订单。只比较四个均值时错误算法会落入现有容差，故题面同时要求原总体订单数；最终计数整数守卫使该错误作答判错，不修改容差。", '',
              '## 范围、复算与交接','',
              '参考仍为122题136份。相对180e511只改Q14/Q21/Q122的题目记录和参考，其他119题逐题记录及参考元数据完全一致；Q34/Q75/Q74原样保留。',
              '本轮三题先用build_refs.py --question重算，最终用build_refs.py --check另起会话严格复算全部136份。当前22新题A/B/C见2026-10-17-summary-new-question-check.json；逐题JSON交接继续用2026-10-17-PR15-change-summary.json。',
              '最终验收：136份严格复算通过（包含Q33）；T04、T05、rules、单一口径和缺口裁决校验通过；当前22道新题A/B/C复查0命中。',
              '英文原题text_en标识及原始英文参考不改；Q122为新题，中英文随新问法同步。修订参考敏感性对照新增排除EN14/EN21，完整排除EN13/EN14/EN21/EN28/EN36/EN89；接线归T11。',
              '过程：初次审计向现有评分器传入的参考矩阵少一层，报TypeError；修正审计调用并重跑，不修改评分器。均值对正销量口径不敏感的问题通过增加原总体订单数解决，保留均值-only对照证据。',
              '无模型调用，无新依赖，不重新定业务口径；T05b仍须按新题意独立pandas重算。','']
    (ROOT/'audit/2026-10-17-summary-rewrites.md').write_text('\n'.join(lines))
    print(json.dumps(report,ensure_ascii=False,default=str))


if __name__=='__main__':main()
