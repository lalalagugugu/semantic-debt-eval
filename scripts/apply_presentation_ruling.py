#!/usr/bin/env python
"""Apply the approved eval-v1.1 presentation revision from its fixed baseline."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
BASE = '455e96f'


def baseline(path):
    return json.loads(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT))


def append_columns(sql, expressions):
    tokens = re.finditer(r"--[^\n]*|/\*[\s\S]*?\*/|'(?:''|\\.|[^'])*'|\"(?:\"\"|[^\"])*\"|`(?:``|[^`])*`|[()]|\b(?:SELECT|FROM)\b", sql, re.I)
    depth = 0; select = None; outer_from = None
    for match in tokens:
        token = match[0].upper()
        if token == '(':
            depth += 1
        elif token == ')':
            depth -= 1
        elif depth == 0 and token == 'SELECT':
            select = match.end()
        elif depth == 0 and token == 'FROM' and select is not None:
            outer_from = match.start(); break
    if outer_from is None:
        raise ValueError('reference needs a final SELECT/FROM')
    return sql[:outer_from].rstrip() + ', ' + ', '.join(expressions) + '\n' + sql[outer_from:]


def main():
    old_manifest = baseline('refs/MANIFEST.json')
    old_records = {r['result_path']:r for r in old_manifest['records']}
    files = {p:baseline(p) for p in ['questions/cube_100.yaml','questions/new.yaml']}
    qs = {q['id']:q for data in files.values() for q in data['questions']}
    refs = {r['result_path']:r for q in qs.values() for r in q['refs']}
    cfg = {}; changes = []
    def ref(stem):
        path = f'refs/{"new" if int(stem[1:stem.index("-")]) > 100 else "cube"}/{stem}.csv'
        return refs[path], path
    def spec(stem):
        _, path = ref(stem)
        return cfg.setdefault(path, {})
    def add(stem, *expressions):
        r,path = ref(stem); r['sql'] = append_columns(r['sql'], expressions)
        changes.append({'reference':path,'action':'append SQL columns','expressions':expressions})
    def replace_sql(stem, old, new):
        r,_ = ref(stem); assert old in r['sql'], (stem, old); r['sql']=r['sql'].replace(old,new)
    def rank(stem, column, descending=True, groups=None, objects=None, name='rank', where=None):
        s=spec(stem);s.setdefault('ranks',[]).append({'name':name,'group_columns':groups or [],'object_columns':objects or [0], 'order_by':[{'column':column,'descending':descending}],'where':where or []})
    # Absolute changes and relative changes: only the approved non-boundary list.
    add('Q29-1','h.avg_sales - r.avg_sales AS sales_difference_amount')
    add('Q77-1','raw_sales - raw_previous AS mom_change_amount')
    add('Q104-1',"sales_change_amount*100.0/nullIf(sumIf(f.SalesAmount,toYear(f.DateKey)=2008),0) AS sales_change_pct", "margin_change_amount*100.0/nullIf(sumIf(f.SalesAmount-f.TotalCost,toYear(f.DateKey)=2008),0) AS margin_change_pct")
    add('Q106-1','sumIf(f.SalesAmount,toYear(f.DateKey)=2009)-sumIf(f.SalesAmount,toYear(f.DateKey)=2008) AS sales_change_amount')
    add('Q109-1','avgIf(day_sales,y=2009)-avgIf(day_sales,y=2008) AS daily_sales_change_amount')
    replace_sql('Q117-1', 'AS decline_amount\nFROM', "AS decline_amount, sumIf(f.SalesAmount,toYear(f.DateKey)=2008) AS category_base_sales\nFROM")
    add('Q117-1','t.sales_2008-t.sales_2009 AS store_decline_amount','c.decline_amount*100.0/nullIf(c.category_base_sales,0) AS category_decline_pct')
    add('Q42-1','yoy_change*100.0/nullIf(lagInFrame(toNullable(sum(s.SalesAmount))) OVER (ORDER BY toYear(s.DateKey) ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING),0) AS yoy_change_pct')
    add('Q44-1','sales-previous_sales AS sales_change_amount')
    add('Q95-1','incremental_average_sales*100.0/nullIf(full_price_average_sales,0) AS incremental_sales_pct')
    add('Q97-1','h2_sales-h1_sales AS sales_change_amount')
    add('Q97-2','sales_increase*100.0/nullIf(h1_sales,0) AS sales_change_pct')
    # Existing ratio denominators are preserved; add missing numerator/base columns.
    add('Q17-1','(SELECT sum(SalesAmount) FROM retail.FactOnlineSales) AS total_sales_amount')
    add('Q64-1','sum(SalesAmount) AS revenue_amount')
    add('Q69-1','sum(f.SalesAmount+f.DiscountAmount) AS original_sales_amount')
    add('Q74-1','t.store_total AS store_total_sales')
    add('Q76-1','sumIf(f.SalesAmount,co.n_orders>=2) AS repeat_sales_amount','sum(f.SalesAmount) AS category_sales_amount')
    add('Q76-2','sumIf(t.SalesAmount,c.orders>=2) AS repeat_sales_amount','sum(t.SalesAmount) AS category_sales_amount')
    add('Q78-1','sum(disc) OVER () AS total_discount_amount')
    add('Q98-1','sum(q_sales) OVER (PARTITION BY ProductCategoryName) AS annual_sales_amount')
    add('Q98-2','sum(quarter_sales) OVER (PARTITION BY ProductCategoryName,year) AS annual_sales_amount')
    add('Q103-1','sumIf(order_sales,order_sales>1000) AS selected_sales_amount','sum(order_sales) AS total_sales_amount')
    add('Q107-1',"sumIf(f.SalesAmount-f.ReturnAmount,s.StoreName='Contoso New York No.2 Store') AS store_net_sales_amount",'sum(f.SalesAmount-f.ReturnAmount) AS city_net_sales_amount')
    add('Q111-1','a.sales_amount AS actual_sales_amount','t.quota_ytd AS ytd_target_amount','t.quota_year AS annual_target_amount')
    add('Q116-1','count() AS cohort_customers')
    # These two generic postprocessors already have their base available.
    spec('Q84-1')['append_postprocess_total']=True
    spec('Q84-2')['append_postprocess_total']=True
    spec('Q118-1')['append_postprocess_total']=True
    # Missing/placeholder entity names require their actual entity key.
    add('Q65-2','s.manager_key AS manager_key')
    add('Q75-1','y.CustomerKey AS CustomerKey')
    add('Q88-1','s.CustomerKey AS CustomerKey')
    add('Q100-1','f.CustomerKey AS CustomerKey')
    # Long tables. Each cohort/stage remains explicit, not an ambiguous value column.
    r,_=ref('Q31-1'); r['sql']="SELECT pc.ProductCategoryName, if(sp.ScenarioKey=1,'Actual','Budget') AS scenario, sum(sp.Amount) AS sales_amount FROM retail.FactStrategyPlan sp JOIN retail.DimProductCategory pc ON sp.ProductCategoryKey=pc.ProductCategoryKey JOIN retail.DimAccount a ON sp.AccountKey=a.AccountKey WHERE a.AccountName='Sale Revenue' AND toYear(sp.DateKey)=2009 AND sp.ScenarioKey IN (1,2) GROUP BY pc.ProductCategoryName,sp.ScenarioKey"
    r,_=ref('Q83-1'); r['sql']='WITH counted AS ('+r['sql']+") SELECT toUInt16(2007) AS cohort_year, toUInt16(tupleElement(stage,1)) AS activity_year, tupleElement(stage,2) AS customers FROM counted ARRAY JOIN [(2007,cohort_size_2007),(2008,returned_2008),(2009,returned_2008_and_2009)] AS stage"
    r,_=ref('Q90-1'); cut=r['sql'].index('),\nmargins AS'); yearly=r['sql'][:cut+1]
    r['sql']=yearly+", margins AS (SELECT category,y,rev,(rev-cost)*100.0/nullIf(rev,0) AS margin_pct FROM yearly) SELECT category,y AS year,margin_pct, margin_pct-lagInFrame(toNullable(margin_pct)) OVER (PARTITION BY category ORDER BY y ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS change_pp, rev AS revenue_amount FROM margins ORDER BY category,y"
    r,_=ref('Q110-1');r['sql']="WITH shares AS (SELECT toYear(f.DateKey) AS y,sumIf(f.SalesAmount,c.ChannelName='Online')*100.0/nullIf(sum(f.SalesAmount),0) AS online_share_pct,sum(f.SalesAmount) AS total_sales_amount FROM retail.FactSales f LEFT JOIN retail.DimChannel c ON f.channelKey=c.ChannelKey WHERE toYear(f.DateKey) IN (2008,2009) GROUP BY y) SELECT y AS year,online_share_pct,online_share_pct-lagInFrame(toNullable(online_share_pct)) OVER (ORDER BY y ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS change_pp,total_sales_amount FROM shares ORDER BY y"
    # Empty-set sums are zero; undefined ratios / missing prior periods remain NULL.
    replace_sql('Q112-1','sumIf(gap,gap>0) AS shortfall_amount','coalesce(sumIf(gap,gap>0),0) AS shortfall_amount')
    # Add a total-accuracy interpretation without dropping the category answer.
    qs['Q38']['refs'].append({'interpretation':'同一季度总体预测准确率：汇总实际与预测后计算；与按品类展示均可接受','sql':"WITH actual AS (SELECT sum(Amount) AS actual FROM retail.FactStrategyPlan WHERE ScenarioKey=1 AND DateKey>='2009-10-01' AND DateKey<='2009-12-31' AND AccountKey=4), forecast AS (SELECT sum(Amount) AS forecast FROM retail.FactStrategyPlan WHERE ScenarioKey=3 AND DateKey>='2009-10-01' AND DateKey<='2009-12-31' AND AccountKey=4) SELECT a.actual,f.forecast,100.0-abs(a.actual-f.forecast)*100.0/nullIf(a.actual,0) AS accuracy_pct FROM actual a CROSS JOIN forecast f",'result_path':'refs/cube/Q38-3.csv','rules':{'ordered':False,'top_n':None,'tie_columns':[],'value_kinds':['other','other','percentage'],'value_types':['Float64','Float64','Nullable(Float64)'],'required_columns':[0,2]}})
    # Competition ranks use frozen quantization and distinct object identities.
    for stem,col,descending,obj in [('Q07-1',1,True,[0]),('Q27-1',3,True,[0]),('Q67-1',1,True,[0]),('Q73-1',3,True,[0]),('Q79-1',3,True,[0]),('Q87-1',3,False,[4]),('Q88-1',1,True,[2]),('Q92-1',3,True,[0]),('Q33-1',4,True,[0,1]),('Q45-1',3,True,[0]),('Q97-1',3,True,[4]),('Q97-2',4,True,[0]),('Q122-1',4,True,[0,2])]:
        rank(stem,col,descending,objects=obj)
    replace_sql('Q22-1','ROW_NUMBER()','rank()')
    rank('Q22-1',4,groups=[3],objects=[0],name='rn')
    rank('Q74-1',2,groups=[0],objects=[4])
    rank('Q85-1',4,groups=[0],objects=[1],where=[{'column':0,'equals':'最高'}])
    rank('Q85-1',4,False,groups=[0],objects=[1],where=[{'column':0,'equals':'最低'}])
    rank('Q98-1',1,objects=[0])
    rank('Q98-2',2,groups=[1],objects=[0])
    rank('Q117-1',2,objects=[0],name='store_rank')
    rank('Q117-1',4,groups=[0],objects=[3],name='category_rank')
    for stem,column in [('Q26-1',0),('Q66-1',0),('Q72-1',1),('Q98-1',2),('Q98-2',3),('Q109-1',0)]:
        spec(stem).setdefault('periods',[]).append({'column':column,'kind':'quarter_label'})
    for stem,column,year_name in [('Q44-2',0,'year'),('Q116-1',0,'cohort_year')]:
        spec(stem).setdefault('periods',[]).append({'column':column,'kind':'calendar_month','year_name':year_name})
    # Explicit required columns start with the independently agreed annotation.
    data_dir=Path(os.environ['SEMDEBT_DATA_DIR'])
    codex=json.loads((data_dir/'handoff-codex/required-columns.json').read_text())
    claude=json.loads((data_dir/'handoff-claude/T05b-required-columns.v4.json').read_text())
    theirs={Path(r['ref']).stem:r['required_columns'] for r in claude['references'] if r.get('required_columns') is not None}
    overrides={'Q50-1':[2,3],'Q99-1':[0,3,4],'Q78-1':[0,2,3],'Q83-1':[0,1,2],'Q65-2':[0]}
    for q in qs.values():
        q['rules']=deepcopy(q['rules'])
        for r in q['refs']:
            path=r['result_path'];stem=Path(path).stem
            if path not in old_records: continue
            rule=deepcopy(r.get('rules',q['rules']))
            if q['scoring']=='judge': required=list(range(len(old_records[path]['columns'])))
            else:
                required=codex[stem]['required']; assert required==theirs[stem] or stem in overrides,stem
            rule['required_columns']=overrides.get(stem,required)
            if stem in {'Q20-2','Q22-1','Q34-1','Q87-1','Q112-1'}:
                key={'Q20-2':0,'Q22-1':0,'Q34-1':4,'Q87-1':4,'Q112-1':0}[stem]
                rule['required_columns']=sorted(set(rule['required_columns']+[key]))
            if stem=='Q33-1':rule['unordered_pairs']=[{'left':[0,2],'right':[1,3]}]
            if stem=='Q122-1':rule['unordered_pairs']=[{'left':[0,1],'right':[2,3]}]
            r['rules']=rule
    rewrites={'Q67':'仅考虑销量至少 1000 件的产品颜色，按线上实际成交均价从高到低列出各颜色。','Q92':'按上季度盈利能力从高到低列出各产品品牌。','Q98':'按全年销售对单个季度的依赖程度从高到低列出各产品品类。','Q69':'哪个促销类别带来的线上促销营收最高？其平均折扣比例是多少？','Q45':'按销售坪效从高到低列出各门店。','Q97':'按 2009 年下半年销售相对上半年的反弹幅度从高到低列出产品。'}
    for qid,text in rewrites.items():qs[qid]['text_zh']=text
    # Metadata is finalized by the builder using actual post-presentation output.
    # Preserve old explicit kinds for new questions by column name, declare additions.
    declared={path:{c['name']:kind for c,kind in zip(r['columns'],r['value_kinds'])} for path,r in old_records.items() if path.startswith('refs/new/')}
    for path in declared:
        declared[path].update({'sales_change_pct':'percentage','margin_change_pct':'percentage','category_decline_pct':'percentage','sales_change_amount':'amount','daily_sales_change_amount':'amount','store_decline_amount':'amount','selected_sales_amount':'amount','total_sales_amount':'amount','store_net_sales_amount':'amount','city_net_sales_amount':'amount','actual_sales_amount':'amount','ytd_target_amount':'amount','annual_target_amount':'amount','cohort_customers':'count','rank':'other','store_rank':'other','category_rank':'other','year':'other','online_share_pct':'percentage','change_pp':'percentage','cohort_year':'other','total_sales':'amount'})
    base_required={r['result_path']:r.get('rules',q['rules'])['required_columns'] for q in qs.values() for r in q['refs']}
    existing_required={'Q24-1':[2],'Q27-1':[1],'Q34-1':[2],'Q38-2':[1],'Q79-1':[2],'Q85-1':[3],'Q87-1':[2],'Q92-1':[1],'Q96-1':[1],'Q22-1':[5],'Q37-1':[2],'Q78-1':[2],'Q119-1':[5]}
    existing_changes={'Q50-1':[2,3],'Q99-1':[3,4],'Q29-1':[0],'Q77-1':[3],'Q104-1':[1,2],'Q106-1':[0],'Q109-1':[1],'Q117-1':[2,4,5],'Q42-1':[2],'Q44-1':[2],'Q95-1':[3],'Q97-1':[3],'Q97-2':[4]}
    for stem,cols in existing_changes.items():existing_required[stem]=sorted(set(existing_required.get(stem,[])+cols))
    existing_required={ref(stem)[1]:cols for stem,cols in existing_required.items()}
    identifier_names={path:[c['name'] for c in r['columns'] if c['name'].lower().endswith('key')] for path,r in old_records.items()}
    for stem,name in [('Q65-2','manager_key'),('Q75-1','CustomerKey'),('Q88-1','CustomerKey'),('Q100-1','CustomerKey')]:identifier_names.setdefault(ref(stem)[1],[]).append(name)
    rank_names={path:sorted({r['name'] for r in plan.get('ranks',[])}) for path,plan in cfg.items() if plan.get('ranks')}
    rank_names.update({ref('Q78-1')[1]:['rnk'],ref('Q119-1')[1]:['global_rank']})
    presentation={'version':1,'identifier_column_names':identifier_names,'rank_column_names':rank_names,'base_required_columns':base_required,'existing_required_columns':existing_required,'baseline':BASE,'references':cfg,'declared_new_value_kinds':declared,'overrides':{'refs/cube/Q31-1.csv':[0,1,2],'refs/cube/Q83-1.csv':[0,1,2],'refs/cube/Q90-1.csv':[0,1,2,3,4],'refs/new/Q110-1.csv':[0,1,2,3]},'new_columns_required':True}
    for path,data in files.items():(ROOT/path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'refs/PRESENTATION.json').write_text(json.dumps(presentation,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'audit/2026-10-18-presentation-application.json').write_text(json.dumps({'baseline':BASE,'sql_appends':changes,'rewrites':rewrites,'annotation_sources':{'codex_sha256':hashlib.sha256((data_dir/'handoff-codex/required-columns.json').read_bytes()).hexdigest(),'claude_v4_sha256':hashlib.sha256((data_dir/'handoff-claude/T05b-required-columns.v4.json').read_bytes()).hexdigest()},'required_overrides':overrides,'pending':[], 'clarifications':{'zero_groups':'required count zero and other required numeric values zero or NULL','existing_denominators':'all required, including Q85 column 3'}},ensure_ascii=False,indent=2)+'\n')
    print('Applied',len(changes),'SQL append groups,',len(cfg),'presentation transforms; total accuracy reference added')


if __name__=='__main__':main()
