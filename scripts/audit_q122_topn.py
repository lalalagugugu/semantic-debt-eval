#!/usr/bin/env python
"""Audit Q122 Top-10 membership and explicitly declared lift populations."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from build_refs import effective_rules, load_unit_policy
from check_rules_impact import csv_rows

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,os.environ['SEMDEBT_MAIN_DIR'])
from harness.scorer import score


def main():
    out=ROOT/'audit/2026-10-17-q122-topn.json'
    if out.exists():raise ValueError('Audit already exists; archive before another run')
    revision='573d51849249f9d25a7d7db9ad1de9789803383b'
    def previous(path):return json.loads(subprocess.check_output(['git','show',f'{revision}:{path}'],cwd=ROOT,text=True))
    before={q['id']:q for name in ('cube_100','new') for q in previous(f'questions/{name}.yaml')['questions']}
    questions={q['id']:q for name in ('cube_100','new') for q in json.loads((ROOT/f'questions/{name}.yaml').read_text())['questions']}
    manifest=json.loads((ROOT/'refs/MANIFEST.json').read_text());records={r['result_path']:r for r in manifest['records']}
    old_records={r['result_path']:r for r in previous('refs/MANIFEST.json')['records']}
    assert {qid for qid in questions if questions[qid]!=before[qid]}=={'Q122'}
    for qid,q in questions.items():
        if qid!='Q122':assert all(records[r['result_path']]==old_records[r['result_path']] for r in q['refs']),qid
    q=questions['Q122'];assert len(q['refs'])==1
    assert all(word not in q['text_zh'] for word in ('总体','至少售出','平均','订单总数','分母'))
    unit,unit_sha=load_unit_policy()
    from chdb import session
    s=session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR'])/'chdb-eval'))
    entries=[]
    try:
        s.query('SET max_threads=1');s.query('SET max_execution_time=0')
        def query(sql):return json.loads(str(s.query(sql,'JSONCompact')))['data']
        cte=q['refs'][0]['sql'].split('\nSELECT x.product1_key')[0]
        populations=query(cte+' SELECT count() FROM baskets')[0]
        for ref,population in zip(q['refs'],populations,strict=True):
            rec=records[ref['result_path']];rules=effective_rules(q,ref);rows=csv_rows(rec)
            sql,n=re.subn(r'\bLIMIT\s+10\s*$','',ref['sql'],flags=re.I);assert n==1
            domain=query(sql);keys=[unit.quantize_tie(r[4],'count') for r in domain]
            boundary=keys[9];strict=sum(k>boundary for k in keys);ties=keys.count(boundary)
            assert boundary==13 and strict==7 and ties==10 and len(rows)==17
            assert len({(r[0],r[2]) for r in rows})==17
            prefix=deepcopy(rows[:7]+rows[-3:])
            missing_strict=deepcopy(rows[:6]+rows[7:11])
            crossed=deepcopy(rows[:10]);crossed[0],crossed[1]=crossed[1],crossed[0]
            tied=deepcopy(rows[:10]);tied[1],tied[2]=tied[2],tied[1]
            zero=deepcopy(prefix)
            for r in zero:r[4]=0;r[5]=0
            verdicts={'empty':score([],[rows],rules),'all_zero_measures':score(zero,[rows],rules),
                      'alternate_boundary_subset':score(prefix,[rows],rules),
                      'missing_strict_member':score(missing_strict,[rows],rules),
                      'cross_rank_block_swap':score(crossed,[rows],rules),
                      'within_rank_block_swap':score(tied,[rows],rules)}
            assert verdicts=={'empty':'wrong','all_zero_measures':'wrong','alternate_boundary_subset':'correct',
                              'missing_strict_member':'wrong','cross_rank_block_swap':'wrong','within_rank_block_swap':'correct'}
            entries.append({'reference':ref['result_path'],'interpretation':ref['interpretation'],'population_orders':population,
                            'reference_rows':len(rows),'domain_pairs':len(domain),'distinct_sort_keys':len(set(keys)),
                            'n':10,'nth_common_orders':int(boundary),'strict_prefix_members':strict,'boundary_members':ties,
                            'boundary_slots_needed':10-strict,'three_n_threshold':30,'C_hit':ties>=30,
                            'A_hit':False,'B_applicable':False,'verdicts':verdicts,
                            'minimum_lift':min(r[5] for r in rows),'maximum_lift':max(r[5] for r in rows)})
        prior=json.loads(subprocess.check_output(['git','show','6ab9687:refs/MANIFEST.json'],cwd=ROOT,text=True))
        prior_standard=next(r for r in prior['records'] if r['result_path']=='refs/new/Q122-1.csv')
        assert records['refs/new/Q122-1.csv']==prior_standard
    finally:s.close()
    result={'baseline_commit':revision,'old_text_zh':before['Q122']['text_zh'],'new_text_zh':q['text_zh'],
            'authorization':'用户确认题面，裁定Q122新题只保留标准全体线上订单总体；乙组仅适用于外部原题问法歧义',
            'policy':'standard_all_online_orders','wording':'user_confirmed',
            'unit_policy_sha256':unit_sha,'references':entries,'final_references':len(records),
            'unchanged_questions_verified':121,'Q14_Q21_wording':'user_confirmed','same_pair_members':True,
            'new_question_audit':'audit/2026-10-17-q122-standard-new-question-check.json',
            'removed_outputs':['总体订单数','平均支持度','平均双向置信度','平均提升度'],
            'question_sha256':hashlib.sha256((ROOT/'questions/new.yaml').read_bytes()).hexdigest()}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
    lines=['# Q122 Top-N重写与边界验收','',
           '状态：Q14/Q21/Q122措辞均获用户确认。Q122仅保留标准全体线上订单参考；全部校验通过后将PR15标Ready for review，不执行合并或冻结。','',
           '新题面：'+q['text_zh'],'',
           '输出列：两个产品的键与名称、共同订单数、提升度。只显示用户要求的产品对与两个指标；不附总体定义、不输出为整数守卫增设的总体订单数。','',
           '## 唯一标准参考','',
           f'- 全体2009线上订单总体：{populations[0]:,}单；lift = P(A且B)/(P(A)P(B))。',
           '用户裁决：Q122是新题，标准答案由出题方确定；乙组多份参考只适用于外部原题问法里的歧义。已删除含Contoso订单的条件总体参考，不改变主参考、题面或Top-N边界规则。','',
           '## A/B/C及排序契约','',
           '- A：空结果和全零指标均判错；共同订单数和提升度均非平凡常数。',
           '- B：不涉及首单/新客/复购或节假日/周末，按标准不适用。',
           '- C：正共购域32,304对、17个共同订单数取值；第10名为13单，严格前缀7对、边界并列10对，边界小于3N=30，未命中。参考17行，允许保留7个严格成员并任选3个边界成员。',
           '- 实测：替换边界内任意3成员判对；漏严格成员判错；同计数块内换序判对；跨计数块换序判错。按未取整整数共同订单数排名。','',
           '## 交接','',
           f'当前122题{len(records)}份参考（Q122一份、17行）。其余121题不变；Q122主参考与6ab9687逐字节一致，已撤销条件总体参考。',
           'T05b按最新2026-10-17-PR15-change-summary.json独立重算全体线上订单总体的提升度及第10名边界。22新题A/B/C见q122-standard-new-question-check.json；两总体旧审计归档于audit/reviews/。',
           '验证：全部136份另起会话严格复算（包含Q33）；T04/T05/rules/单一口径/缺口校验及22新题A/B/C按现行版本检查。当前23份有序参考均有显式排序键。未修改评分器、容差或冻结语义层。','']
    (ROOT/'audit/2026-10-17-q122-topn.md').write_text('\n'.join(lines))
    print(json.dumps(result,ensure_ascii=False,default=str))


if __name__=='__main__':main()
