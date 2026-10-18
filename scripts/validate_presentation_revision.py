#!/usr/bin/env python
"""Check and report the approved eval-v1.1 presentation patch, without a DB."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess

from build_refs import effective_rules, load_selection_policy, load_unit_policy, validate_questions
from check_rules_impact import csv_rows
from reference_presentation import apply_presentation

ROOT=Path(__file__).resolve().parent.parent
BASE='455e96f'
REPORT=ROOT/'audit/2026-10-18-presentation-review.json'
REWRITES={'Q67','Q69','Q92','Q98','Q45','Q97'}


def old(path):return subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=ROOT)
def digest(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def table(data):return list(csv.DictReader(io.StringIO(data.decode())))


def fixtures(policy):
    meta=[{'name':'entity','type':'String'},{'name':'sales_amount','type':'Float64'}]
    spec={'ranks':[{'name':'rank','group_columns':[],'object_columns':[0],'order_by':[{'column':1,'descending':True}],'where':[]}]}
    _,result=apply_presentation(meta,[['A',10.004],['B',10.005],['C',9.994]],policy,spec)
    assert [r[-1] for r in result]==[1,1,3]
    _,result=apply_presentation(meta,[['A',10],['A',10],['B',9]],policy,spec)
    assert [r[-1] for r in result]==[1,1,2]
    spec={'periods':[{'column':0,'kind':'calendar_month','year_name':'year'}]}
    _,result=apply_presentation([{'name':'month','type':'Date'}],[['2007-01-01'],['2008-01-01']],policy,spec)
    assert result==[[1,2007],[1,2008]]
    _,result=apply_presentation([{'name':'quarter','type':'UInt8'}],[[1],[4]],policy,{'periods':[{'column':0,'kind':'quarter_label'}]})
    assert result==[['Q1'],['Q4']]


def sample_selection(rows,rule):
    # Sanity witness, not independent verification of the selection contract.
    from harness.selection import _eligible, _domain, _boundary, identity
    spec=rule['selection']; stages=spec['stages']; chosen={}
    for i,stage in enumerate(stages):
        eligible=list(_eligible(rows,stage,stages,chosen))
        domain=_domain(eligible,stage,rule['value_kinds'])
        members=set()
        for group,objects in domain.items():
            order=stage['order_by']
            def key(obj):
                return tuple((-x if k['descending'] else x) for x,k in zip(objects[obj],order,strict=True))
            for obj in sorted(objects,key=key)[:stage['n']]:members.add(group+obj)
        chosen[i]=members
    parents={s['parent'] for s in stages}
    leaves=[i for i in range(len(stages)) if i not in parents]
    return [row for row in rows if any(identity(row,stages[i]['group_columns']+stages[i]['object_columns']) in chosen[i] and all(row[c['column']]==c['equals'] for c in stages[i]['where']) for i in leaves)]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');parser.add_argument('--fixtures-only',action='store_true');args=parser.parse_args()
    policy,_=load_unit_policy();fixtures(policy)
    if args.fixtures_only:print('PASS: competition ranks, duplicate objects, quarter labels, cross-year months');return
    load_selection_policy()
    from harness.scorer import score,_cells_equal
    qfiles=['questions/cube_100.yaml','questions/new.yaml']
    groups=[json.loads((ROOT/p).read_text())['questions'] for p in qfiles]
    validate_questions(groups[0]);validate_questions(groups[1],'new')
    qs={q['id']:q for group in groups for q in group}
    before={q['id']:q for p in qfiles for q in json.loads(old(p))['questions']}
    manifest=json.loads((ROOT/'refs/MANIFEST.json').read_text());records={r['result_path']:r for r in manifest['records']}
    prior={r['result_path']:r for r in json.loads(old('refs/MANIFEST.json'))['records']}
    cfg=json.loads((ROOT/'refs/PRESENTATION.json').read_text())
    assert len(qs)==122 and len(records)==137
    assert set(records)-set(prior)=={'refs/cube/Q38-3.csv'} and not set(prior)-set(records)
    assert manifest['presentation_sha256']==digest('refs/PRESENTATION.json')
    assert {qid for qid,q in qs.items() if q['text_zh']!=before[qid]['text_zh']}==REWRITES
    assert all(q['text_en']==before[qid]['text_en'] and q['split']==before[qid]['split'] for qid,q in qs.items())
    details=[];transitions=[];self_matches=[]
    for q in qs.values():
        for ref in q['refs']:
            path=ref['result_path'];record=records[path];rule=effective_rules(q,ref);rows=csv_rows(record)
            assert rule==record['rules']
            assert record['sql_sha256']==hashlib.sha256(ref['sql'].encode()).hexdigest()
            assert record['sha256']==digest(path)
            assert [c['type'] for c in record['columns']]==rule['value_types']
            assert len(rule['value_kinds'])==len(record['columns'])
            required=rule['required_columns'];assert required and len(set(required))==len(required) and all(0<=i<len(record['columns']) for i in required)
            with (ROOT/path).open() as stream:
                reader=csv.reader(stream);assert next(reader)==[c['name'] for c in record['columns']];assert sum(1 for _ in reader)==record['row_count']
            old_record=prior.get(path)
            changed=not old_record or old_record['sha256']!=record['sha256'] or old_record['sql_sha256']!=record['sql_sha256']
            added=[]
            if old_record:
                old_names=[c['name'] for c in old_record['columns']];names=[c['name'] for c in record['columns']]
                initial=cfg['base_required_columns'][path]
                original_annotation=initial
                # Keep identifier rulings separate from the new UX definition.
                original_codex_path=ROOT/'audit/2026-10-18-presentation-annotations.json'
                original_annotation=json.loads(original_codex_path.read_text()).get(Path(path).stem,{}).get('required',initial)
                for i,column in enumerate(record['columns']):
                    if column['name'] in old_names:
                        old_i=old_names.index(column['name'])
                        if i in required and old_i not in original_annotation:
                            reason='新系统约定：已有分母／名次／变化表达' if old_i in cfg['existing_required_columns'].get(path,[]) else '缺失或占位名称的已有对象键裁决'
                            transitions.append({'reference':path,'old_column':old_i,'new_column':i,'name':column['name'],'reason':reason})
                    else:
                        added.append({'column':i,'name':column['name'],'required':i in required})
                assert all(a['required'] for a in added),path
            witness=rows[:rule['top_n']] if rule['top_n'] is not None else sample_selection(rows,rule) if rule.get('selection') else rows
            candidate=[[row[i] for i in required] for row in witness]
            assert score(candidate,[rows],rule)=='correct', (path,'projected self-match')
            self_matches.append(path)
            if rule.get('rankings'):
                for style in ('dense','position'):
                    print(path,style,flush=True)
                    styled=[list(row) for row in witness]
                    assigned={}
                    for row in styled:
                        for domain in rule['rankings']:
                            col=domain['column'];group=[row[i] for i in domain['group_columns']]
                            block=next(b for b in domain['blocks'] if b['group']==group and b['rank']==row[col])
                            if style=='dense':row[col]=block['dense']
                            else:
                                key=(col,tuple(group),block['rank'])
                                objects=assigned.setdefault(key,{})
                                obj=tuple(row[i] for i in domain['object_columns'])
                                if obj not in objects:objects[obj]=block['rank']+len(objects)
                                row[col]=objects[obj]
                    projected=[[row[i] for i in required] for row in styled]
                    assert score(projected,[rows],rule)=='correct',(path,style,'whole-answer rank self-match')
            if changed or old_record is None or old_record.get('rules')!=rule:
                details.append({'question_id':q['id'],'reference':path,'sql_changed':not old_record or old_record['sql_sha256']!=record['sql_sha256'],'csv_changed':not old_record or old_record['sha256']!=record['sha256'],'old_rows':old_record['row_count'] if old_record else None,'new_rows':record['row_count'],'columns':record['columns'],'required_columns':required,'identifier_columns':rule.get('identifier_columns',[]),'rank_columns':rule.get('rank_columns',[]),'new_columns':added,'sql_sha256':record['sql_sha256'],'sha256':record['sha256']})
            for row in rows:
                for value,column in zip(row,record['columns'],strict=True):
                    if column['type']=='Date':assert value is None or re.fullmatch(r'\d{4}-\d{2}-\d{2}',value)
            spec=cfg['references'].get(path,{})
            if spec.get('ranks'):
                _,ranked=apply_presentation(record['columns'],rows,policy,{'ranks':spec['ranks']})
                assert ranked==rows,(path,'competition rank recomputation')
            for period in spec.get('periods',[]):
                for row in rows:
                    if period['kind']=='quarter_label':assert row[period['column']] in {'Q1','Q2','Q3','Q4'}
                    else:assert 1<=row[period['column']]<=12
    key_columns={'Q20-2':0,'Q22-1':0,'Q34-1':4,'Q87-1':4,'Q112-1':0,'Q100-1':4,'Q75-1':5,'Q88-1':2,'Q65-2':3}
    for stem,column in key_columns.items():
        record=next(r for path,r in records.items() if Path(path).stem==stem)
        assert column in record['rules']['required_columns'],stem
    assert records['refs/cube/Q85-1.csv']['rules']['required_columns']==[0,1,3,4,5]
    assert records['refs/cube/Q50-1.csv']['rules']['required_columns']==[2,3]
    assert records['refs/cube/Q99-1.csv']['rules']['required_columns']==[0,3,4]
    for path,cols in cfg['existing_required_columns'].items():assert set(cols)<=set(records[path]['rules']['required_columns'])
    for path in ['refs/cube/Q33-1.csv','refs/new/Q122-1.csv']:assert records[path]['rules']['unordered_pairs']
    # The missing-object selection fix survives, and empty-set shortfalls are zero.
    assert all(row[1] is not None for row in csv_rows(records['refs/cube/Q71-1.csv']))
    r112=csv_rows(records['refs/new/Q112-1.csv']);assert all(row[3]==0 for row in r112 if row[2]==0)
    for row in csv_rows(records['refs/new/Q111-1.csv']):
        assert row[1] is None if row[4]==0 else True
        assert row[2] is None if row[5]==0 else True
    # Snapshot membership stays the same; new rank and rule version need independent recheck.
    previous_q79=table(old('refs/cube/Q79-1.csv'))
    current_q79=table((ROOT/'refs/cube/Q79-1.csv').read_bytes())
    assert Counter(tuple(r.items()) for r in previous_q79)==Counter(tuple((k,r[k]) for k in previous_q79[0]) for r in current_q79)
    assert {r['rank'] for r in current_q79}=={'1'}
    snapshot=json.loads((ROOT/'audit/Q79-boundary-members.json').read_text());assert snapshot['row_count']==42 and snapshot['reference_sha256']==records['refs/cube/Q79-1.csv']['sha256']
    # Long tables preserve the requested counts and values rather than grouping them away.
    cohort=table(old('refs/cube/Q83-1.csv'))[0]
    r83=csv_rows(records['refs/cube/Q83-1.csv']);assert r83==[[2007,2007,int(cohort['cohort_size_2007'])],[2007,2008,int(cohort['returned_2008'])],[2007,2009,int(cohort['returned_2008_and_2009'])]]
    for row in csv_rows(records['refs/cube/Q31-1.csv']):
        original=next(r for r in table(old('refs/cube/Q31-1.csv')) if r['ProductCategoryName']==row[0])
        assert _cells_equal(row[2],float(original['actual' if row[1]=='Actual' else 'budget']))
    rewritten=[]
    for qid in sorted(REWRITES):
        q=qs[qid];profiles=[]
        for ref in q['refs']:
            r=records[ref['result_path']];rows=csv_rows(r);rule=effective_rules(q,ref)
            sort_columns=[k['column'] for k in rule.get('order_by',[])]
            zero_candidate=[[0 if isinstance(row[i],(int,float,Decimal)) and not isinstance(row[i],bool) else row[i] for i in rule['required_columns']] for row in (rows[:rule['top_n']] if rule['top_n'] else rows)]
            profiles.append({'all_zero_required_numeric':score(zero_candidate,[rows],rule),'reference':ref['result_path'],'rows':len(rows),'order_key_distinct':{str(i):len({str(policy.quantize_tie(row[i],rule['value_kinds'][i])) for row in rows}) for i in sort_columns},'empty_candidate':score([],[rows],rule),'declared_low_discrimination':q['labels']['low_discrimination']['criteria'],'C_scope':'full ordered list, no new Top-N cutoff; existing internal selection constraints retained'})
        rewritten.append({'question_id':qid,'old_text':before[qid]['text_zh'],'new_text':q['text_zh'],'profiles':profiles,'A':'Q69保留单类别退化A；其他题非零/非空，不以单行计算结果本身当常数','B':'六题均不涉及首购/复购或节假日与周末互换，B条两组必测口径不适用','C':'排序键按冻结量化逐份统计；不更改既有边界或把全排序误作Top-1'})
    remaining=[{'question_id':qid,'text':q['text_zh'],'explicit_top_n':bool(re.search(r'(?:前|最大的|最高的|最少的)\s*\d+',q['text_zh']))} for qid,q in qs.items() if qid not in REWRITES and re.search(r'哪些|哪几',q['text_zh']) and re.search(r'最高|最强|最大|最依赖|最贵',q['text_zh'])]
    report={'baseline':BASE,'questions':122,'references':137,'annotation_agreement':109,'annotation_disputes_resolved':5,'new_total_accuracy_reference':'refs/cube/Q38-3.csv','details':details,'became_required':transitions,'rewrites':rewritten,'other_similar_phrasing':remaining,'rank_style_self_matched_references':sum(bool(r['rules'].get('rankings')) for r in records.values()),'self_matched_references':len(self_matches),'question_sha256':{p:digest(p) for p in qfiles},'manifest_sha256':digest('refs/MANIFEST.json'),'presentation_sha256':digest('refs/PRESENTATION.json'),'independent_T05b':'pending; no eval-v1.1 tag created'}
    if args.write:
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        lines=['# eval-v1.1 展示约定与逐参考变更审计','','基线455e96f；122题、137份参考。137份必答列投影后的自匹配通过。新增Q38总准确率，不删除原品类参考；不打冻结tag。','','## 原来不必答、现在必答（逐列）','','| 参考 | 原列号 | 新列号 | 列名 | 原因 |','|---|---:|---:|---|---|']
        for r in transitions:lines.append(f"| {r['reference']} | {r['old_column']} | {r['new_column']} | {r['name']} | {r['reason']} |")
        lines+=['','## 逐参考改动','','| 参考 | SQL变化 | CSV变化 | 行数（旧→新） | 必答列 |','|---|---|---|---|---|']
        for r in details:lines.append(f"| {r['reference']} | {r['sql_changed']} | {r['csv_changed']} | {r['old_rows']}→{r['new_rows']} | {r['required_columns']} |")
        lines+=['','## 标识列与名次列（0起）','','| 参考 | identifier_columns | rank_columns |','|---|---|---|']
        for r in details:
            if r['identifier_columns'] or r['rank_columns']:
                lines.append(f"| {r['reference']} | {r['identifier_columns']} | {r['rank_columns']} |")
        lines+=['','## 六题改写与A/B/C证据','']
        for item in rewritten:
            lines += ['- '+item['question_id']+'：'+item['new_text'], '  - '+item['A']+'；'+item['B']+'。', '  - 排序取值及逐参考记录：'+json.dumps(item['profiles'],ensure_ascii=False)]
        lines+=['','## 其余同类句式（只列不改）','']
        for r in remaining:lines.append('- '+r['question_id']+'：'+r['text']+'；已明示前N：'+str(r['explicit_top_n']))
        lines+=['','21份含名次的参考分别构造竞赛、稠密、位置编号三种完整答案并全部自匹配通过；分组及筛选总体保持原排名域。排名按全局固定量化计算竞赛排名1、1、3；名次不参与原有选择边界。月分群显示年和月份数字，季度用语义上下文Q1–Q4，不合并跨年组。Q112空集合缺口为0，无分母的比例、无基期变化保留NULL。第八节边界不补相应列。','','独立pandas复核待T05b；旧T06覆盖/低区分度报告保留为eval-v1历史。本报告是新参考与改写的变更证据，不宣称已重新冻结或完成600条/T12重评。']
        (ROOT/'audit/2026-10-18-presentation-review.md').write_text('\n'.join(lines)+'\n')
    else:
        assert json.loads(REPORT.read_text())==report,'review stale'
    print(f'PASS: 137 reference self-matches, six rewrites, key requirements, {len(transitions)} existing columns newly required, long/period/null/rank fixtures')


if __name__=='__main__':main()
