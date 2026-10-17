#!/usr/bin/env python
"""Audit the 22 new questions using references and data only, never model runs."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from build_refs import effective_rules, load_unit_policy

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,os.environ['SEMDEBT_MAIN_DIR'])
from harness.questions import parse_value
from harness.scorer import _cells_equal, _is_numeric
from check_q79_membership import member_counts


def counterpart(qid, ref, rows):
    sql=ref['sql']
    source='(SELECT * FROM retail.FactOnlineSales WHERE SalesQuantity>0)' if 'SalesQuantity>0' in sql else 'retail.FactOnlineSales'
    if qid=='Q109' and 'IsHoliday' in sql:
        return 'holiday replaced by weekend',sql.replace('d.IsHoliday AS holiday',"if(d.IsWorkDay='WeekEnd','Yes','No') AS holiday")
    if qid=='Q114':
        return 'new means active in the window',sql.replace('countIf(f.first_date','countDistinctIf(f.CustomerKey,f.first_date').replace('f.first_date','f.DateKey').replace('FROM firsts f',f'FROM {source} f')
    if qid=='Q115':
        return 'cohort means active during 2008',sql.replace("HAVING first_date<=toDate('2008-12-31')","HAVING countIf(DateKey>=toDate('2008-01-01') AND DateKey<=toDate('2008-12-31'))>0")
    if qid=='Q116':
        # Hold the displayed month domain fixed, so adding unrelated months
        # cannot disguise a constant metric as sensitivity to the definition.
        head,tail=sql.split(',\nobserved AS',1)
        head=re.sub(r'GROUP BY CustomerKey\s+HAVING','GROUP BY CustomerKey,toStartOfMonth(DateKey) HAVING',head)
        months=','.join("'"+str(row[0])+"'" for row in rows)
        head=head[:-1]+f' AND toStartOfMonth(first_date) IN ({months}))'
        return 'first means first activity within each displayed month',head+',\nobserved AS'+tail
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',help='read immutable bank/reference inputs from this Git revision')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError('audit outputs are append-only; choose another path')
    def read(path):
        return subprocess.run(['git','show',f'{args.revision}:{path}'],cwd=ROOT,check=True,capture_output=True,text=True).stdout if args.revision else (ROOT/path).read_text()
    questions=json.loads(read('questions/new.yaml'))['questions']
    manifest={r['result_path']:r for r in json.loads(read('refs/MANIFEST.json'))['records']}
    policy,policy_hash=load_unit_policy()
    from chdb import session
    sess=session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR'])/'chdb-eval'))
    def query(sql):return json.loads(str(sess.query(sql,'JSONCompact')))['data']
    records=[]
    try:
        sess.query('SET max_threads=1');sess.query('SET max_execution_time=0')
        for question in questions:
            qid=question['id']; flags=set()
            item={'question_id':qid,'question':question['text_zh'],'A':[],'B':[],'C':[]}
            for ref in question['refs']:
                rec=manifest[ref['result_path']]
                text=read(ref['result_path'])
                if hashlib.sha256(text.encode()).hexdigest()!=rec['sha256']:
                    raise ValueError('reference hash differs: '+ref['result_path'])
                raw=list(csv.reader(io.StringIO(text)))
                rows=[[parse_value(value,col['type']) for value,col in zip(row,rec['columns'],strict=True)] for row in raw[1:]]
                rules=effective_rules(question,ref)
                positions=[i for i,k in enumerate(rules['value_kinds']) if k!='other']
                stats=[]
                for i in positions:
                    values=[row[i] for row in rows if row[i] is not None]
                    stats.append({'column':rec['columns'][i]['name'],'kind':rules['value_kinds'][i],
                                  'distinct':len({policy.quantize_tie(v,rules['value_kinds'][i]) for v in values}),
                                  'non_null':len(values),'minimum':min(values) if values else None,'maximum':max(values) if values else None})
                numeric=[(row[i],rules['value_kinds'][i]) for row in rows for i in positions if row[i] is not None and _is_numeric(row[i])]
                zero=bool(numeric) and all(_cells_equal(0,v,kind=k) for v,k in numeric)
                full=bool(numeric) and all(k in ('ratio','percentage') and _cells_equal(100 if k=='percentage' else 1,v,kind=k) for v,k in numeric)
                constant=len(rows)>1 and bool(stats) and all(s['distinct']<=1 for s in stats)
                reasons=[name for name,hit in [('empty',not rows),('all_zero_measures',zero),('all_full_ratios',full),('constant_measure_vector',constant)] if hit]
                if reasons:flags.add('A')
                item['A'].append({'reference':ref['result_path'],'row_count':len(rows),'measure_profile':stats,'hits':reasons,
                                  'note':'A tests data-induced empty/zero/full/constant measure vectors; a computed single scalar is not called constant merely because it has one cell'})
                other=counterpart(qid,ref,rows)
                if other:
                    definition,sql=other; alternate=query(sql)
                    equal=member_counts(rows,rules['value_kinds'],policy)==member_counts(alternate,rules['value_kinds'],policy)
                    if equal:flags.add('B')
                    item['B'].append({'reference':ref['result_path'],'replacement':definition,'replacement_sql':sql,'equal':equal,'original_rows':rows,'replacement_rows':alternate})
            if not item['B']:
                item['B']={'applicable':False,'reason':'no first-purchase or holiday/weekend definition in the question'}
            if qid in ('Q117','Q119'):
                ref=question['refs'][0]; rec=manifest[ref['result_path']]; rule=effective_rules(question,ref)
                domain=query(ref['sql'])
                # Q119's ranking postprocess does not change its selection key.
                for index,stage in enumerate(rule['selection']['stages']):
                    keys=defaultdict(set)
                    for row in domain:
                        group=tuple(row[i] for i in stage['group_columns'])
                        keys[group].add(tuple(policy.quantize_tie(row[o['column']],rule['value_kinds'][o['column']]) for o in stage['order_by']))
                    checks=rec['selection_checks'][index]
                    maximum=max(c['boundary'] for c in checks)
                    if any(c['boundary']>=3*c['required'] for c in checks):flags.add('C')
                    item['C'].append({'stage':index,'groups_checked':len(checks),'n':stage['n'],'maximum_boundary_members':maximum,
                                      'minimum_distinct_sort_keys_in_full_domain':min(map(len,keys.values())),
                                      'maximum_distinct_sort_keys_in_full_domain':max(map(len,keys.values()))})
            elif qid=='Q118':
                ref=question['refs'][0]; rec=manifest[ref['result_path']]; domain=query(ref['sql'])
                values=sorted((policy.quantize_tie(row[1],'amount') for row in domain),reverse=True)
                n=rec['postprocess_details']['selected_products']; boundary=values[n-1]; ties=values.count(boundary)
                if ties>=3*n:flags.add('C')
                item['C']=[{'n':n,'domain_products':len(values),'distinct_sort_keys':len(set(values)),'boundary_members':ties,'nth_key':str(boundary)}]
            elif any(effective_rules(question,r)['top_n'] is not None for r in question['refs']):
                item['C']=[]
                for ref in question['refs']:
                    rule=effective_rules(question,ref);n=rule['top_n']
                    if n is None:continue
                    sql,count=re.subn(rf'\bLIMIT\s+{n}\s*;?\s*$','',ref['sql'],flags=re.I)
                    assert count==1
                    domain=query(sql)
                    keys=[tuple(policy.quantize_tie(row[i],rule['value_kinds'][i]) for i in rule['tie_columns']) for row in domain]
                    boundary=keys[n-1];ties=keys.count(boundary)
                    if ties>=3*n:flags.add('C')
                    item['C'].append({'reference':ref['result_path'],'n':n,'domain_rows':len(domain),
                                      'distinct_sort_keys':len(set(keys)),'boundary_members':ties,
                                      'nth_key':list(map(str,boundary)),'three_n_threshold':3*n})
            else:item['C']={'applicable':False,'reason':'not a Top-N/quantile selection question'}
            item['hits']=sorted(flags);records.append(item)
            print(qid,item['hits'],flush=True)
    finally:sess.close()
    result={'scope':'Q101-Q122 only; data and reference inputs, no model outputs or published system answers',
            'revision':args.revision,'questions_scanned':len(records),'unit_policy_sha256':policy_hash,
            'question_sha256':hashlib.sha256(read('questions/new.yaml').encode()).hexdigest(),
            'hits':[r['question_id'] for r in records if r['hits']],'records':records}
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
    print(json.dumps({'questions_scanned':len(records),'hits':result['hits']},ensure_ascii=False))


if __name__=='__main__':main()
