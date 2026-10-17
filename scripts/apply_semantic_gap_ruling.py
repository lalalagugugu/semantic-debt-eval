#!/usr/bin/env python
"""Apply the user-approved 2026-10-17 semantic-gap ruling to draft PR15."""
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def spearman_sql(domain, alias, group=None, count_alias=None):
    """Weighted average-tie ranks, preserving exact duplicate observations."""
    keys = f'{group},' if group else ''
    partition = f'PARTITION BY {group} ' if group else ''
    whole = f'PARTITION BY {group}' if group else ''
    tail = (f',sum(w) AS {count_alias}' if count_alias else '')
    return f'''WITH domain AS ({domain}),
frequency AS (SELECT {keys}x,y,count() AS w FROM domain WHERE x IS NOT NULL AND y IS NOT NULL GROUP BY {keys}x,y),
ranks AS (SELECT *,
sum(w) OVER ({partition}ORDER BY x RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)-(sum(w) OVER (PARTITION BY {keys}x)-1)/2.0 AS rx,
sum(w) OVER ({partition}ORDER BY y RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)-(sum(w) OVER (PARTITION BY {keys}y)-1)/2.0 AS ry FROM frequency),
centered AS (SELECT *,sum(w*rx) OVER ({whole})/sum(w) OVER ({whole}) AS mx,
sum(w*ry) OVER ({whole})/sum(w) OVER ({whole}) AS my FROM ranks)
SELECT {keys}sum(w*(rx-mx)*(ry-my))/nullIf(sqrt(sum(w*pow(rx-mx,2))*sum(w*pow(ry-my,2))),0) AS {alias}{tail}
FROM centered''' + (f' GROUP BY {group}' if group else '')


def main():
    archive = ROOT / 'audit/reviews/2026-10-17-before-gap-ruling.json'
    if archive.exists():
        raise ValueError('One-shot ruling already applied; use build_refs.py for recomputation')
    paths = [ROOT / f'questions/{name}.yaml' for name in ('cube_100', 'new')]
    groups = [json.loads(p.read_text()) for p in paths]
    questions = {q['id']: q for g in groups for q in g['questions']}
    archive.write_text(json.dumps({'questions': list(questions.values()),
        'manifest': json.loads((ROOT/'refs/MANIFEST.json').read_text())}, ensure_ascii=False, indent=2)+'\n')
    q = questions['Q13']
    q['text_zh'] = '按门店列出销售额、平均单价和销售数量。'
    q['refs'][0].update(interpretation='全渠道按门店统计销售额、平均单价和销售数量；沿用约定2及已有指标',
        sql='SELECT s.StoreKey,s.StoreName,sum(f.SalesAmount) AS total_sales,sum(f.SalesAmount)/nullIf(sum(f.SalesQuantity),0) AS average_unit_price,sum(f.SalesQuantity) AS sales_quantity FROM retail.FactSales f JOIN retail.DimStore s ON f.StoreKey=s.StoreKey GROUP BY s.StoreKey,s.StoreName')
    q['scoring_notes'] = '按2026-10-17裁决第五节改问已有全渠道指标；不缩为线上门店。EN13不纳入修订参考敏感性对照。'
    q['labels']['semantic_dependency']['notes'] = '门店分析用全渠道销售；平均单价沿用语义层已有指标。'
    q = questions['Q28']
    q['text_zh'] = '比较门店渠道和线上渠道的平均单价。'
    q['refs'][0].update(interpretation='全渠道Store与Online按已有平均单价指标比较',
        sql="SELECT c.ChannelName,sum(f.SalesAmount)/nullIf(sum(f.SalesQuantity),0) AS average_unit_price FROM retail.FactSales f JOIN retail.DimChannel c ON f.channelKey=c.ChannelKey WHERE c.ChannelName IN ('Store','Online') GROUP BY c.ChannelName")
    q['scoring_notes'] = '按2026-10-17裁决第五节改问平均单价；保留Store与Online比较对象。EN28不纳入修订参考敏感性对照。'
    q['labels']['semantic_dependency']['notes'] = '渠道对比用全渠道销售；平均单价沿用语义层已有指标。'
    questions['Q36']['text_zh'] = '当前活跃、有流失风险和已流失的客户各有多少人？'
    questions['Q89']['text_zh'] = '活跃、有流失风险和已流失客户的平均消费金额与平均购买产品种类数是多少？'
    for qid in ('Q36', 'Q89'):
        questions[qid]['scoring_notes'] += ' 2026-10-17按真实问法改写，不附定义；英文原题标识保留，修订参考敏感性对照剔除'+qid.replace('Q','EN')+'。'
    q = questions['Q38']; q['refs'] = [q['refs'][1]]
    q['refs'][0]['interpretation'] = '按裁决仅报告准确率=100%-绝对百分比误差'
    q['scoring_notes'] = '2026-10-17丙组裁决：准确度只认准确率，不再接受误差率。'
    q = questions['Q39']; r = deepcopy(q['refs'][0])
    marker = "least(dateDiff('day',toDate('2007-01-01'),introduction_date),dateDiff('day',introduction_date,toDate('2010-01-01')))"
    assert r['sql'].count(marker) == 1
    r.update(sql=r['sql'].replace(marker,'toInt64(90)'), result_path='refs/cube/Q39-2.csv',
             interpretation='问法歧义：同一新品/老品范围，上市前后各90日比较老品日均销售')
    q['refs'].append(r)
    q = questions['Q40']; q['refs'][0].update(
        interpretation='缺失报价日沿用此前最近EUR收盘价；覆盖全部线上销售日',
        sql="WITH daily AS (SELECT DateKey,sum(SalesAmount) AS sales FROM retail.FactOnlineSales WHERE CurrencyKey=1 GROUP BY DateKey) SELECT sum(d.sales*e.EndOfDayRate) AS sales_eur FROM (SELECT *,toUInt8(1) AS k FROM daily ORDER BY DateKey) d ASOF LEFT JOIN (SELECT r.DateKey,r.EndOfDayRate,toUInt8(1) AS k FROM retail.FactExchangeRate r JOIN retail.DimCurrency c ON r.CurrencyKey=c.CurrencyKey WHERE c.CurrencyName='EUR' ORDER BY DateKey) e ON d.k=e.k AND d.DateKey>=e.DateKey")
    q['scoring_notes'] = '2026-10-17裁决：不丢弃无当日汇率的销售日，沿用此前最近收盘价。'
    q = questions['Q84']; r = deepcopy(q['refs'][0])
    r.update(postprocess='abc_groups_after', result_path='refs/cube/Q84-2.csv',
             interpretation='问法歧义：同额组整体归类，以加入后的累计占比划分80%/95%边界')
    q['refs'].append(r)
    domains = {
        'Q48': 'WITH o AS (SELECT StoreKey,sum(DownTime) AS downtime FROM retail.FactITSLA GROUP BY StoreKey),s AS (SELECT StoreKey,sum(SalesAmount) AS sales FROM retail.FactSales GROUP BY StoreKey) SELECT ifNull(o.downtime,0) AS x,s.sales AS y FROM s LEFT JOIN o ON s.StoreKey=o.StoreKey',
        'Q91': 'SELECT c.YearlyIncome AS x,sum(f.SalesAmount) AS y FROM retail.FactOnlineSales f JOIN retail.DimCustomer c ON f.CustomerKey=c.CustomerKey WHERE c.YearlyIncome IS NOT NULL GROUP BY f.CustomerKey,c.YearlyIncome',
    }
    for qid, alias, count in [('Q48','correlation',None), ('Q91','income_spend_correlation','customers_analyzed')]:
        q = questions[qid]
        q['refs'].append({'interpretation':'问法歧义：Spearman相关，重复值使用平均秩，观察域与Pearson一致',
            'sql':spearman_sql(domains[qid],alias,count_alias=count),
            'result_path':f"refs/cube/{qid}-{len(q['refs'])+1}.csv",
            'rules':{'ordered':False,'top_n':None,'tie_columns':[],
                'value_kinds':['ratio']+(['count'] if count else []),
                'value_types':['Nullable(Float64)']+(['UInt64'] if count else [])}})
    q = questions['Q86']; sql = q['refs'][0]['sql']; stop=sql.index('),\nstats AS')
    domain = sql[:stop]+') SELECT ProductSubcategoryName,DiscountPercent AS x,SalesQuantity AS y FROM enriched'
    q['refs'].append({'interpretation':'问法歧义：Spearman相关，按全部促销观察的精确频数计算并列中秩，样本域同Pearson',
        'sql':spearman_sql(domain,'corr_discount_vs_qty','ProductSubcategoryName','observations')+' HAVING observations>100',
        'result_path':'refs/cube/Q86-3.csv'})
    q = questions['Q92']; r=q['refs'][0]
    r['sql']=r['sql'].replace('ORDER BY gross_margin_dollars DESC','ORDER BY gross_margin_pct DESC')
    r['interpretation']='按裁决以毛利率衡量盈利能力并降序排名'
    q['rules']['order_by']=[{'column':3,'descending':True}]
    if 'rules' in r:r['rules']['order_by']=deepcopy(q['rules']['order_by'])
    q['scoring_notes']='2026-10-17丙组裁决：按毛利率排序，仅保留该参考。'
    q = questions['Q95']; r=q['refs'][0]
    old=r['sql']; joins=old[old.index('FROM retail.FactOnlineSales'):old.index('GROUP BY pc.ProductCategoryName')]
    r['sql']='SELECT pc.ProductCategoryName,avgIf(f.SalesAmount,f.PromotionKey<>1) AS promo_average_sales,avgIf(f.SalesAmount,f.PromotionKey=1) AS full_price_average_sales,promo_average_sales-full_price_average_sales AS incremental_average_sales '+joins+'GROUP BY pc.ProductCategoryName'
    r['interpretation']='按裁决仅保留促销行均销售减原价行均销售；包含孤儿产品属性组'
    q['scoring_notes']='2026-10-17丙组裁决：报告促销与原价交易的行均销售差，不再用总额或总额比代替。'
    questions['Q119']['refs']=questions['Q119']['refs'][:1]
    questions['Q119']['scoring_notes']='2026-10-17裁决：竞赛/稠密排名在当前返回结果完全相同，仅保留竞赛排名参考。'
    for path, group in zip(paths, groups, strict=True):
        path.write_text(json.dumps(group,ensure_ascii=False,indent=2)+'\n')
    oldpaths={r['result_path'] for q in json.loads(archive.read_text())['questions'] for r in q['refs']}
    current={r['result_path'] for q in questions.values() for r in q['refs']}
    for path in oldpaths-current:
        (ROOT/path).unlink()
    print(f'Applied approved ruling: {len(questions)} questions, {len(current)} references; full rebuild required')


if __name__ == '__main__':
    main()
