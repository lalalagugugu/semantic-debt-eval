#!/usr/bin/env python
"""Apply the explicitly approved T05b differences to the pre-freeze bank."""
from copy import deepcopy
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def round_projections(sql):
    """Yield the expression and output alias of balanced ROUND calls."""
    for match in re.finditer(r'\bround\s*\(', sql, re.I):
        start = match.end()
        depth = 1
        commas = []
        quote = None
        for pos in range(start, len(sql)):
            char = sql[pos]
            if quote:
                if char == quote:
                    quote = None
                continue
            if char in "'\"`":
                quote = char
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    alias = re.match(r'\s+AS\s+(\w+)', sql[pos+1:], re.I)
                    if alias and len(commas) == 1:
                        yield match.start(), pos+1, sql[start:commas[0]].strip(), alias[1]
                    break
            elif char == ',' and depth == 1:
                commas.append(pos)


def main():
    paths = [ROOT / 'questions/cube_100.yaml', ROOT / 'questions/new.yaml']
    groups = [json.loads(path.read_text()) for path in paths]
    old = {q['id']: q for q in groups[0]['questions']}
    new = {q['id']: q for q in groups[1]['questions']}
    archive = ROOT / 'audit/reviews/2026-10-16-before-t05b-corrections.json'
    if archive.exists():
        raise ValueError('one-shot correction already applied; use build_refs.py to recompute')
    archive.write_text(json.dumps({'questions': groups[0]['questions'] + groups[1]['questions']}, ensure_ascii=False, indent=2) + '\n')

    q = old['Q34']
    q['refs'][0]['sql'] = q['refs'][0]['sql'].replace(
        'avg(OnHandQuantity * UnitCost) as avg_inventory FROM retail.FactInventory WHERE toYear(DateKey) = 2009 GROUP BY ProductKey',
        'avg(inventory_amount) as avg_inventory FROM (SELECT ProductKey,DateKey,sum(OnHandQuantity * UnitCost) AS inventory_amount FROM retail.FactInventory WHERE toYear(DateKey) = 2009 GROUP BY ProductKey,DateKey) GROUP BY ProductKey')
    q['refs'][0]['sql'] = q['refs'][0]['sql'].replace('ORDER BY turnover_ratio DESC', 'ORDER BY c.total_cogs / nullIf(a.avg_inventory, 0) DESC')
    q['refs'][0]['interpretation'] = '公司产品粒度：每个快照日先跨店汇总库存金额，再平均；同年公司产品销货成本除以平均库存'

    q = old['Q38']
    ref = deepcopy(q['refs'][0])
    ref['sql'] = ref['sql'].replace('round(abs(a.actual - f.forecast) * 100.0 / nullIf(a.actual, 0), 2) as error_pct', 'round(100.0 - abs(a.actual - f.forecast) * 100.0 / nullIf(a.actual, 0), 2) as accuracy_pct')
    ref['result_path'] = 'refs/cube/Q38-2.csv'
    ref['interpretation'] = '准确率=100%-绝对百分比误差；题面未点名误差率或准确率，保留互补解读'
    q['refs'].append(ref)

    q = old['Q48']
    q['refs'][0]['sql'] = q['refs'][0]['sql'].replace('FROM store_outages so JOIN store_sales ss ON so.StoreKey = ss.StoreKey', 'FROM store_sales ss LEFT JOIN store_outages so ON so.StoreKey = ss.StoreKey')
    q['refs'][0]['sql'] = q['refs'][0]['sql'].replace('so.total_downtime > 1000', 'ifNull(so.total_downtime,0) > 1000')
    q['refs'][1]['sql'] = q['refs'][1]['sql'].replace('corr(o.downtime,s.sales_amount)', 'corr(ifNull(o.downtime,0),s.sales_amount)').replace('FROM outages o JOIN sales s ON o.StoreKey=s.StoreKey', 'FROM sales s LEFT JOIN outages o ON o.StoreKey=s.StoreKey')
    q['scoring_notes'] += '\nT05b裁决：保留全部有销售门店，无SLA记录按0停机；两份示例均从销售域左连接。'

    q = old['Q65']
    ref = deepcopy(q['refs'][0])
    ref['sql'] = "WITH stores AS (SELECT StoreManager,StoreName,sum(f.SalesAmount) AS total_sales FROM retail.FactSales f JOIN retail.DimStore s ON f.StoreKey=s.StoreKey GROUP BY StoreManager,StoreName HAVING total_sales>5000000) SELECT if(e.EmployeeKey=0,NULL,e.FirstName||' '||e.LastName) AS manager_name,s.StoreName,s.total_sales FROM stores s LEFT JOIN retail.DimEmployee e ON toInt32OrNull(s.StoreManager)=e.EmployeeKey ORDER BY total_sales DESC"
    ref['result_path'] = 'refs/cube/Q65-2.csv'
    ref['interpretation'] = '以经理姓名标识，同名经理不合并门店；无员工映射保留门店及NULL姓名'
    q['refs'].append(ref)

    q = old['Q66']
    q['refs'][0]['sql'] = q['refs'][0]['sql'].replace(', countDistinct(SalesOrderNumber) AS discounted_orders', '')
    q['rules']['value_kinds'] = q['rules']['value_kinds'][:2]
    q['rules']['value_types'] = q['rules']['value_types'][:2]
    q['refs'][0].pop('rules', None)

    old['Q77']['refs'][0]['sql'] = "WITH monthly AS (SELECT toStartOfMonth(DateKey) AS month_date,sum(SalesAmount) AS raw_sales FROM retail.FactOnlineSales WHERE DateKey>=toDate('2008-12-01') AND DateKey<toDate('2010-01-01') GROUP BY month_date), growth AS (SELECT month_date,raw_sales,lagInFrame(raw_sales) OVER (ORDER BY month_date ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS raw_previous FROM monthly) SELECT toMonth(month_date) AS month,round(raw_sales,2) AS sales,round(raw_previous,2) AS prev_month_sales,round((raw_sales-raw_previous)*100.0/nullIf(raw_previous,0),2) AS mom_growth_pct FROM growth WHERE toYear(month_date)=2009 ORDER BY month_date"
    for qid in ('Q75', 'Q76', 'Q80'):
        for ref in old[qid]['refs']:
            sql = ref['sql']
            for _, _, expression, alias in round_projections(sql):
                sql = re.sub(r'\bORDER BY\s+'+re.escape(alias)+r'\s+DESC\b', 'ORDER BY '+expression+' DESC', sql, flags=re.I)
            ref['sql'] = sql
    for qid, alias in (('Q71', 'sales_amount'), ('Q88', 'total_spend_2009')):
        for ref in old[qid]['refs']:
            sql = ref['sql']
            for start, end, expression, name in reversed(list(round_projections(sql))):
                if name == alias:
                    sql = sql[:start] + '(' + expression + ')' + sql[end:]
            ref['sql'] = sql
    for ref in old['Q86']['refs']:
        ref['sql'] = ref['sql'].replace('\nLIMIT 20', '')
        ref['interpretation'] += '；按题面补全全部满足原样本下限的子品类，不截前20'
    old['Q86']['scoring_notes'] += '\nT05b裁决：题面未要求前N，示例补全所有满足已声明样本下限的子品类。'

    q = old['Q100']
    ref = deepcopy(q['refs'][0])
    ref['sql'] = ref['sql'].replace('FROM retail.FactOnlineSales', 'FROM (SELECT * FROM retail.FactOnlineSales WHERE SalesQuantity>0)', 1)
    ref['result_path'] = 'refs/cube/Q100-2.csv'
    ref['interpretation'] = '购买事件=SalesQuantity>0；正销量订单数及客单价的两个P90阈值交集，含阈值并列'
    q['refs'].append(ref)

    new['Q115']['text_zh'] += '状态标签统一使用“活跃”“有流失风险”“已流失”，分别列出期初状态和期末状态。'
    new['Q120']['text_zh'] += '范围标签统一使用“全体”和“职业内”；全体行的职业列为空，职业内行使用数据中的职业名称。'
    new['Q115']['text_en'] += ' Use the exact labels 活跃, 有流失风险 and 已流失 for both initial and final states.'
    new['Q120']['text_en'] += ' Use scope labels 全体 and 职业内; the overall occupation is NULL, while occupation rows use the recorded occupation names.'
    for path, group in zip(paths, groups, strict=True):
        path.write_text(json.dumps(group, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
