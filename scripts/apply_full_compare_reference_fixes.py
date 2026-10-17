#!/usr/bin/env python
"""Apply the unambiguous reference-value and label rulings; defer Q48."""
import json
from pathlib import Path
import subprocess

from apply_t05b_reference_corrections import round_projections

ROOT=Path(__file__).resolve().parent.parent


def main():
    ledger=ROOT/'audit/2026-10-17-full-compare-application.json'
    if ledger.exists():raise ValueError('One-shot application already recorded')
    baseline=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    p=ROOT/'questions/cube_100.yaml';d=json.loads(p.read_text());rounding=[];labels=[]
    for q in d['questions']:
        for ref in q['refs']:
            sql=ref['sql'];calls=list(round_projections(sql))
            for start,end,expression,alias in reversed(calls):
                sql=sql[:start]+'('+expression+')'+sql[end:]
            if calls:
                ref['sql']=sql
                rounding.append({'question_id':q['id'],'reference':ref['result_path'],
                                 'columns':[{'name':alias,'expression':expr} for _,_,expr,alias in calls]})
            if q['id'] in ('Q36','Q89'):
                for old,new in [('Active','活跃'),('At Risk','有流失风险'),('Churned','已流失')]:
                    ref['sql']=ref['sql'].replace("'"+old+"'","'"+new+"'")
                labels.append({'question_id':q['id'],'reference':ref['result_path'],'source':'题面及冻结语义层客户分层枚举','values':['活跃','有流失风险','已流失']})
            if q['id']=='Q85':
                ref['sql']=ref['sql'].replace("'TOP'","'最高'").replace("'BOTTOM'","'最低'")
                labels.append({'question_id':'Q85','reference':ref['result_path'],'source':'题面已用最高/最低','values':['最高','最低']})
                for rules in [q['rules']]+([ref['rules']] if 'rules' in ref else []):
                    for stage in rules['selection']['stages']:
                        for condition in stage['where']:
                            condition['equals']={'TOP':'最高','BOTTOM':'最低'}.get(condition['equals'],condition['equals'])
            if q['id']=='Q92':
                ref['sql']=ref['sql'].replace('JOIN retail.DimProduct p ON','LEFT JOIN retail.DimProduct p ON').replace('  AND p.BrandName IS NOT NULL\n','')
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    ledger.write_text(json.dumps({'baseline_commit':baseline,'rounding_removed':rounding,'labels_changed':labels,
        'Q92':'名称维度左连接，删除空品牌过滤，保留NULL品牌分组',
        'Q48_status':'pending_user_clarification: downtime labels are not customer segments'},ensure_ascii=False,indent=2)+'\n')
    print('Removed ROUND projections from',len(rounding),'references; changed labels Q36/Q89/Q85; fixed Q92; Q48 deferred')


if __name__=='__main__':main()
