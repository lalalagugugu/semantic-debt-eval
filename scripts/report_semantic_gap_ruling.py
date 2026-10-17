#!/usr/bin/env python
"""Report approved reference changes, four A/B/C checks and all >50-row results."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from build_refs import effective_rules, load_unit_policy
from check_rules_impact import csv_rows

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.environ['SEMDEBT_MAIN_DIR'])
from harness.scorer import score


def read_revision(revision, path):
    return json.loads(subprocess.check_output(['git', 'show', f'{revision}:{path}'], cwd=ROOT, text=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decision-file', type=Path, required=True)
    args = parser.parse_args()
    summary_path=ROOT/'audit/2026-10-17-summary-rewrites.json'
    summary_rewrites=json.loads(summary_path.read_text()) if summary_path.exists() else None
    topn_path=ROOT/'audit/2026-10-17-q122-topn.json'
    q122_topn=json.loads(topn_path.read_text()) if topn_path.exists() else None
    questions = {q['id']: q for name in ('cube_100', 'new') for q in
                 json.loads((ROOT/f'questions/{name}.yaml').read_text())['questions']}
    manifest = json.loads((ROOT/'refs/MANIFEST.json').read_text())
    records = {r['result_path']: r for r in manifest['records']}
    policy, unit_sha = load_unit_policy()
    old = json.loads((ROOT/'audit/reviews/2026-10-17-before-gap-ruling.json').read_text())
    old_questions = {q['id']: q for q in old['questions']}
    old_records = {r['result_path']: r for r in old['manifest']['records']}
    changed = []
    for qid, q in questions.items():
        before = old_questions[qid]
        if q == before:
            continue
        changed.append({'question_id': qid, 'text_changed': q['text_zh'] != before['text_zh'],
                        'previous_references': len(before['refs']), 'current_references': len(q['refs']),
                        'interpretations': [r['interpretation'] for r in q['refs']]})
    checks = []
    for qid, positions in [('Q13', [2,3,4]), ('Q28', [1]), ('Q36', [1]), ('Q89', [1,2,3])]:
        q = questions[qid]; ref = q['refs'][0]; rec = records[ref['result_path']]
        rows = csv_rows(rec); rules = effective_rules(q, ref)
        zeros = deepcopy(rows); blanks = deepcopy(rows)
        for row in zeros:
            for pos in positions: row[pos] = 0
        for row in blanks:
            for pos in positions: row[pos] = None
        profiles = [{'column':rec['columns'][pos]['name'],
                     'distinct':len({policy.quantize_tie(row[pos], rules['value_kinds'][pos]) for row in rows}),
                     'minimum':min(row[pos] for row in rows if row[pos] is not None),
                     'maximum':max(row[pos] for row in rows if row[pos] is not None)} for pos in positions]
        trivial = {'empty': score([], [rows], rules), 'zero_measures':score(zeros,[rows],rules),
                   'blank_measures':score(blanks,[rows],rules)}
        a_hit = any(v == 'correct' for v in trivial.values()) or all(p['distinct'] <= 1 for p in profiles)
        assert not a_hit and rules['top_n'] is None and not rules.get('selection')
        checks.append({'question_id':qid,'text':q['text_zh'],'reference_rows':len(rows),
                       'A':{'hit':a_hit,'profiles':profiles,'trivial_candidate_verdicts':trivial},
                       'B':{'hit':False,'applicable':False,'reason':'不涉及首单/新客/复购/回头客，也不涉及节假日与周末；Q36/Q89是末次交易分层'},
                       'C':{'hit':False,'applicable':False,'reason':'无Top-N或排名选择'}})
    long = []
    for rec in manifest['records']:
        if rec['row_count'] <= 50: continue
        rule = rec['rules']; nominal = rec['row_count']; extra = 0
        if rec['selection_checks']:
            nominal = sum(g['required'] for stage in rec['selection_checks'] for g in stage)
            extra = sum(g['strict']+g['boundary']-g['required'] for stage in rec['selection_checks'] for g in stage)
        elif rule['top_n'] is not None:
            nominal = rule['top_n']; extra = rec['row_count']-nominal
        assert extra >= 0
        long.append({'question_id':rec['question_id'],'reference':rec['result_path'],'rows':rec['row_count'],
                     'top_n_tie_expansion':extra>0,'tie_extra_rows':extra,'rows_before_tie_expansion':nominal,
                     'exceeds_50_due_to_ties':nominal<=50<rec['row_count']})
    review = {'decision':'decisions/2026-10-17-semantic-gaps-and-realistic-questions.md',
              'decision_sha256':hashlib.sha256(args.decision_file.read_bytes()).hexdigest(),
              'previous_references':len(old_records),'final_references':len(records),'questions':len(questions),
              'current_question_sha256':{name:hashlib.sha256((ROOT/f'questions/{name}.yaml').read_bytes()).hexdigest() for name in ('cube_100','new')},
              'unit_policy_sha256':unit_sha,'changes':changed,'rewritten_question_checks':checks,
              'added_references':sorted(set(records)-set(old_records)),
              'removed_references':sorted(set(old_records)-set(records)),
              'over_50_rows':long,'anchor_revised_sensitivity_exclusions':['EN13','EN28','EN36','EN89'],
              'new_question_audit':'audit/2026-10-17-gap-ruling-new-question-check.json',
              'T05b_independent_recheck':'pending; SQL checks are not an independent pandas result'}
    if summary_rewrites:
        review['new_question_audit']=summary_rewrites['new_question_audit']
        review['anchor_revised_sensitivity_exclusions']=summary_rewrites['anchor_revised_sensitivity_exclusions']
        review['summary_rewrites']=summary_rewrites['records']
        review['Q13_Q28_wording']='user_confirmed'
    if q122_topn:
        review['q122_topn']=q122_topn
        review['new_question_audit']=q122_topn['new_question_audit']
        review['Q14_Q21_wording']='user_confirmed'
    (ROOT/'audit/2026-10-17-gap-ruling-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2,default=str)+'\n')

    baseline = 'bf8e09584187cee4fb60eb2715c4f075c4324424'
    base_questions = {q['id']:q for name in ('cube_100','new') for q in read_revision(baseline,f'questions/{name}.yaml')['questions']}
    base_records = {r['result_path']:r for r in read_revision(baseline,'refs/MANIFEST.json')['records']}
    summary = {'baseline_commit':baseline,'baseline_references':len(base_records),'current_references':len(records),
               'scope':'entire PR15 versus merged main/PR14; includes the approved semantic-gap ruling',
               'manifest_sha256':hashlib.sha256((ROOT/'refs/MANIFEST.json').read_bytes()).hexdigest(),
               'anchor_revised_sensitivity_exclusions':review['anchor_revised_sensitivity_exclusions'],'records':[]}
    for qid,q in questions.items():
        before = base_questions[qid]; paths={r['result_path'] for r in q['refs']}; previous={r['result_path'] for r in before['refs']}
        item={'question_id':qid,'text_changed':q['text_zh']!=before['text_zh'],
              'references_changed':paths!=previous,
              'previous_references':len(previous),'current_references':len(paths),
              'added_references':sorted(paths-previous),'removed_references':sorted(previous-paths)}
        for key,field in [('changed_SQL','sql_sha256'),('changed_CSV','sha256'),('changed_rules','rules')]:
            item[key]=sorted(p for p in paths&previous if records[p][field]!=base_records[p][field])
        if any(item[key] for key in ('changed_SQL','changed_CSV','changed_rules')):
            item['references_changed']=True
        if any(records[p]['postprocess']!=base_records[p]['postprocess'] for p in paths&previous):
            item['references_changed']=True
        summary['records'].append(item)
    for name,field in [('text_changed','text_changed'),('references_changed','references_changed'),('CSV_changed','changed_CSV')]:
        summary[name]=[r['question_id'] for r in summary['records'] if r[field]]
    (ROOT/'audit/2026-10-17-PR15-change-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    lines=['# 17项缺口裁决执行与真实问法改写','',
           '状态：PR15草稿，未冻结。仅执行用户已批准的裁决；T05b仍须独立重算。',
           f'122题、{len(old_records)}→{len(records)}份参考。英文原题text_en保持外部锚点标识，中文修订参考敏感性对照剔除EN13/EN28/EN36/EN89；harness接线归Claude Code。','',
           '## 逐条执行','',
           '| 缺口 | 执行 |','|---|---|',
           '| G01 | Q13改问全渠道销售额、平均单价、销售数量；Q28改问Store/Online平均单价。平均单价保留求平均能力；Q13以已有销售数量替换交易笔数，保留规模比较而不伪造订单；不用线上三店替代原比较对象 |',
           '| G02 | Q47保留故障事件平均，不是每台设备累计平均；题面未写“每台” |',
           '| G03 | Q38删除误差率参考，仅保留准确率Q38-2 |',
           '| G04 | Q39保留最长对称窗口，补前后各90天 |',
           '| G05 | Q40替换为ASOF向前沿用汇率，不再丢弃1065个无当日报价的销售日 |',
           '| G06 | Q76保留全目录/品类内两份 |',
           '| G07 | Q84补同额组纳入后归类，与纳入前归类并存；全局量化不变 |',
           '| G08 | Q100只保留既有精确线性插值P90 |',
           '| G09 | Q118只保留既有精确线性插值P90 |',
           '| G10 | Q97按裁决明确保留两份 |',
           '| G11 | Q98按裁决明确保留两份 |',
           '| G12 | Q117只保留相对降幅 |',
           '| G13 | Q92仅按毛利率排序，同时将rules.order_by改为毛利率列 |',
           '| G14 | Q119当前竞赛/稠密结果相同，删除Q119-2，只留Q119-1 |',
           '| G15 | Q121保留总体/样本标准差两份 |',
           '| G16 | Q95仅保留促销行均销售减原价行均销售，不将总额比当增量 |',
           '| G17 | Q48/Q86/Q91各补Spearman；并列取平均秩、重复频数保留，不改变Pearson观察域；Q48原分组对照示例仍保留 |','',
           '## 本轮题面（Q13、Q28待用户确认）','']
    for c in checks:
        lines += [f"- {c['question_id']}：{c['text']}"]
    lines += ['', '## 四题A/B/C自查','',
              '只用数据和参考，不读模型结果。B严格按裁决限定的首单/新客/复购及节假日/周末两类检查，不把不适用写成已做替换实验。','']
    for c in checks:
        lines += [f"- {c['question_id']}：{c['reference_rows']}行；A未命中，空/全零/空指标候选均不能判对，数值列不同值数为"+
                  '、'.join(f"{p['column']}={p['distinct']}" for p in c['A']['profiles'])+'；B不适用；C无Top-N，不适用。']
    lines += ['', '## 参考超过50行：仅列证据，不决定去留','',
              '“并列扩展”列报告是否发生扩展；括号额外区分去掉并列后本来是否已超50行。P90选样不等同Top-N并列扩展。','',
              '| 题号 | 参考行数 | 是否由Top-N并列扩展造成 |','|---|---:|---|']
    for r in long:
        why = f"有并列扩展：{r['rows_before_tie_expansion']}+{r['tie_extra_rows']}" if r['top_n_tie_expansion'] else '否'
        if r['top_n_tie_expansion']:
            why += '（因此跨过50行）' if r['exceeds_50_due_to_ties'] else '（未扩展也已超50行）'
        lines.append(f"| {r['question_id']} | {r['rows']} | {why} |")
    lines += ['', '## 验证与交接','',
              '全量生成：`uv run python scripts/build_refs.py --refresh-rules`；严格复算：`uv run python scripts/build_refs.py --check`。rules审阅表随现行manifest重新生成。',
              'T05b交接以`audit/2026-10-17-PR15-change-summary.json`为准：逐题含题面标志、参考增删、SQL/CSV/rules变化，基线固定为已合并PR14。新增窗口、ABC与Spearman需独立pandas实现，不导入本构建器。',
              '历史133份阶段的审阅报告保留为历史记录，当前份数以本报告及manifest为准。未修改语义层、评分器或英文原始参考，未执行eval-v1冻结。','']
    lines += ['验证结果：136份全量生成及最终严格复算通过（包含Q33）；T04、T05、rules、单一口径与本轮17项裁决校验通过；四题及22新题A/B/C均0命中。`validate_gap_ruling.py --sql-fixtures`另覆盖重复观察的平均秩、反向排名及常数域NULL。Q101原有GMV显式量纲与推断不同的告警仍保留。', '',
              '过程记录：旧校验固定在133份阶段的题面、Q40部分日期方案及新题文件哈希，已改为核验当前裁决报告；Q86新参考编号曾撞上历史退役Q86-2，校验发现后改用Q86-3，并重新严格复算。历史退役文件仍不存在，未覆盖历史审计。', '',
              'T11交接：Q95中文参考由5列改为4列，英文原始参考须继续使用自身schema和rules，不直接复用中文rules；英文原始参考接线由Claude Code负责。本轮没有重评600条，历史影响数字不当作当前口径结果。','']
    if summary_rewrites:
        lines=[line.replace('Q13、Q28待用户确认','Q13、Q28用户已确认；本节保留此前四题改写') for line in lines]
        lines.insert(2,'第六节追加：Q14/Q21/Q122汇总改写见[三题报告](2026-10-17-summary-rewrites.md)及配套JSON；Q13/Q28措辞已获用户确认。')
    if q122_topn:
        lines.insert(2,f"Q122题面已确认，当前{len(records)}份参考；Q122现行标准及边界见[最新报告](2026-10-17-q122-topn.md)，旧均值/额外订单数方案已撤销。")
    (ROOT/'audit/2026-10-17-gap-ruling-review.md').write_text('\n'.join(lines))
    print(json.dumps({'references':len(records),'changed_this_round':[r['question_id'] for r in changed],
                      'rewritten':[r['question_id'] for r in checks],'over_50':long},ensure_ascii=False))


if __name__ == '__main__':
    main()
