#!/usr/bin/env python
"""Inventory reference risks against frozen data_quality; never rewrite answers.

Existing first-round SQL is inspected as superseded history, not as proof that
the approved second-round questions have SQL. Optional probes use chdb-eval.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import yaml

from build_refs import load_unit_policy

ROOT = Path(__file__).resolve().parent.parent
AGGREGATE = re.compile(r'\b(?:sum\w*|avg\w*|count\w*|uniq\w*|max|min|corr)\s*\(', re.I)
JOIN = re.compile(r'\b(?:(INNER|LEFT|RIGHT|FULL|CROSS)\s+(?:(?:OUTER|ANY|ALL)\s+)?)?JOIN\s+(?:retail\.)?(DimProduct|DimEmployee)\b', re.I)
DIMENSIONS = {'dimproduct': 'DimProduct', 'dimemployee': 'DimEmployee'}

# These are human review annotations, not scorer rules or SQL rewrites.
SCOPED_CATALOG = {'Q39': '新旧产品识别需要上市日期；缺维度产品无法判定新旧，须披露可分类范围，不编造日期。',
                  'Q42': '题干限定相机品类；孤儿产品无法归类，不应凭空归入相机，须披露分类缺失。'}
REFERENCE_RISK_NOTES = {
    'Q11': '全品类销售内连接后缺未分类销售；建议单列未分类额，核对已分类＋未分类与事实总额守恒。',
    'Q20': '最近门店×产品库存已经从事实取得；再连名称不应删掉孤儿，两个输出层级均须保事实ProductKey。',
    'Q21': '逐店逐产品的最近库存丢孤儿；建议左连名称并增加事实产品键，不能把多个缺名产品合并。',
    'Q24': '已知品类比率未必改变，但未知品类的退货量／销量整组消失；须处理未分类组及分子分母同域。',
    'Q33': '两端产品名称内连接会删共购对；须以两个事实产品键保身份。完整域探查超时，入选数未验证。',
    'Q34': '成本与库存先按产品汇总后仍因名字缺失而删行；建议保产品键，另核成本／库存相交域，不补造库存。',
    'Q61': '子品类金额阈值前删掉不可分类事实；建议披露未分类金额，不能编造其真实子品类。',
    'Q62': '全品牌聚合丢失品牌未知销售；未分类合计并非一个真实品牌，须明确报告范围与数量门槛。',
    'Q67': '颜色未知组消失，另有blue／Blue同码异写；需分别处理缺分类与颜色归一，不能把左连当作已解决。',
    'Q71': '已知品类内赢家可算，但未知品类／子品类组被删；需审定未分类组，不为孤儿猜品类。',
    'Q73': '库存差额先因产品内连接缩域；完整事实键域前10此次无孤儿入选，仍保留风险记录，未改参考。',
    'Q76': '两种复购粒度均丢未知品类；品类内订单计数域亦受分类缺失影响，须分别审阅，不混成一个修复。',
    'Q86': '相关性观察样本因缺子品类而减少；未知观察可单列但不可分配到已知子品类，应披露样本范围。',
    'Q90': '各年未知品类毛利率组消失；已知组数值不一定变，不能把全额缺失率直接套作每个比率误差。',
    'Q92': '原SQL同时内连和BrandName IS NOT NULL；只改LEFT仍会删未知组，须先确认是否要求全品牌含未知。',
    'Q95': '未知品类的促销／原价金额被删；未分类需保持两类分子分母一致，比例不是促销因果增量。',
    'Q98': '两种年度解读都缺未分类季度序列；不能把多个未知真实品类假装成一个已知品类，须说明可分类域。',
    'Q99': '未分类品类的日销售序列被删；处理未知组时还要保持对应日类型分母和年度范围一致。',
}
QUALITY_NOTES = {
    'missing-products': '已实测四张事实的孤儿规模；Q74/Q87/Q97保键修复，其余逐题未知分类策略未批量改。',
    'inventory-weekly': '既有库存题用每店×产品最近快照，Q34用观察快照平均；未将多个周快照直接当销售流量相加。新SQL仍须复核。',
    'holiday-equals-weekend': '两种标签是相同数据划分，不改题造差异；Q109日历归一的新版SQL尚未写。',
    'new-customer-degenerate': '0/1不是坏题理由；原首购题与新版Q114均不因值低换窗口。',
    'online-sales-mismatch': '按已批准选表裁决核对；Q74已用FactSales。新Q110要求同源分子分母，不能跨表拼接。',
    'promotion-vs-discount-amount': '当前命中的促销参考使用FactOnlineSales；全渠道存在两种筛选不等价，不可推广该等价关系。',
    'store-manager-is-id': 'Q65返回经理ID；按姓名作答与ID参考的身份等价尚需契约处理，不据此自动删除ID或改judge。',
    'orphan-store-employee': '实测StoreKey 227→245缺行；原参考无事实聚合＋员工内连，新Q112必须保门店和员工键。',
    'sentinel-close-date': 'Q10已有在营／时点等批准解读；未来2090关闭日不是已关闭，不因哨兵值重写定义。',
    'mislabeled-stylename': '当前参考与第二轮问句均未用StyleName定义款式；不把未命中扩张为其他列已验证。',
    'dirty-enum-values': 'Q67颜色分组需审blue／Blue；Q60限定Production不受Human Resources脏名影响，不能全部机械归一。',
    'outlier-values': '收入、面积等原值不按结果方向删去；已有统计题可声明稳健定义，但不为改善相关性清洗。',
    'no-fact-on-employee-or-territory': '原员工题是维度／层级查询；新经理绩效题需经门店，不推断员工直接销售归属。',
    'date-dim-wider-than-facts': '原Q59问日历本身，不能限成销售日期；日均类走事实日期／限定期间，新Q109/Q121须限定观察年份。',
    'country-name-mismatch': '当前参考未按辖区国家名直接连接地理国家名；新题连接仍需SQL落地后复核。',
}
NEW_RISKS = {
    'Q102': '品类净额：保留无法分类的事实金额，审查未知组及合计守恒。',
    'Q104': '品类两期收入／毛利：两年均保留未知组，不让维表连接改变符号筛选。',
    'Q108': '客户地理路径及空国家标签；不按名称连接地理表。',
    'Q109': '节假日=周末；完整年内日历分母，不能延伸到事实范围之外。',
    'Q112': '经理经门店关联员工必须左连接；StoreKey 227／EmployeeKey 245保留键、披露缺姓名。',
    'Q114': '首购新客0/1是数据事实；不改90天窗口筛出非零结果。',
    'Q117': '先在完整事实域选门店；品类缺失不能改变店总降幅，未知贡献须单列。',
    'Q119': '门店局部赢家和公司全局排名都保留事实ProductKey；逐题列出孤儿入选者。',
    'Q120': '收入离群值保留；不依据相关方向或显著性删客户。',
    'Q121': '品类未知组、完整12个月和0销售月份需一致，不由日期表引入额外年份。',
    'Q122': 'Contoso域只可由已知品牌判定；全部订单分母先算，不因品牌／产品内连接缩小总体。',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def masked(sql):
    return re.sub(r"--[^\n]*|/\*.*?\*/|'(?:''|[^'])*'", lambda m: ' ' * len(m.group()), sql, flags=re.S)


def inspect_reference(question, ref, generation):
    sql = masked(ref['sql'])
    facts = sorted(set(re.findall(r'\b(?:retail\.)?(Fact\w+)\b', sql, re.I)))
    joins = [{'kind': (kind or 'INNER').upper(), 'table': DIMENSIONS[table.lower()]}
             for kind, table in JOIN.findall(sql)]
    product_present = bool(re.search(r'\bDimProduct\b', sql, re.I))
    employee_present = bool(re.search(r'\bDimEmployee\b', sql, re.I))
    product_inner = any(j == {'kind': 'INNER', 'table': 'DimProduct'} for j in joins)
    if facts and re.search(r'\bFROM\s+retail\.DimProduct\b', sql, re.I):
        product_inner = product_inner or bool(re.search(r'\bJOIN\s+retail\.Fact\w+', sql, re.I))
    employee_inner = any(j == {'kind': 'INNER', 'table': 'DimEmployee'} for j in joins)
    product_risk = bool(facts and AGGREGATE.search(sql) and product_inner)
    employee_risk = bool(facts and AGGREGATE.search(sql) and employee_inner)
    if question['id'] == 'Q74' and generation == 'active_original' and not product_risk:
        assessment = '已批准修复：完整事实分母、左连产品、按ProductKey保留孤儿；结果见清单。'
    elif question['id'] in {'Q87', 'Q97'} and generation == 'active_original' and not product_risk:
        assessment = '按用户第3条修复排名参考：事实ProductKey保身份、左连名称、NULL披露；不改变既有计算及评分路径。'
    elif product_risk:
        assessment = SCOPED_CATALOG.get(question['id'], REFERENCE_RISK_NOTES.get(question['id'], '存在事实／事实派生量的内连接丢失路径；未知组、范围及输出键待逐题处理，尚未修改参考。'))
    elif employee_risk:
        assessment = '经理维表内连接可能漏StoreKey 227，须保留原门店及员工键。'
    elif (product_present or employee_present) and not facts:
        assessment = '仅查维度目录／员工层级；不是事实销售总额被维表内连接丢失的情形。'
    else:
        assessment = '未命中这两个事实内连接模式；不等于全部数据质量条目已验证通过。'
    return {'question_id': question['id'], 'generation': generation, 'result_path': ref['result_path'],
            'sql_sha256': hashlib.sha256(ref['sql'].encode()).hexdigest(), 'fact_tables': facts,
            'dimension_joins': joins, 'fact_product_inner_exposure': product_risk,
            'fact_employee_inner_exposure': employee_risk, 'assessment': assessment,
            'masked_sql': sql}


def quality_match(rule, sql):
    tests = {
        'missing-products': r'\bDimProduct\b', 'inventory-weekly': r'\bFactInventory\b',
        'holiday-equals-weekend': r'\b(?:IsHoliday|IsWorkDay)\b',
        'new-customer-degenerate': r'\b(?:first_purchase|first_purchase_date|first_date|cohort|new_customers)\b',
        'online-sales-mismatch': r'\b(?:FactSales|FactOnlineSales)\b',
        'promotion-vs-discount-amount': r'\b(?:PromotionKey|DiscountAmount)\b',
        'store-manager-is-id': r'\bStoreManager\b', 'orphan-store-employee': r'\bDimEmployee\b',
        'sentinel-close-date': r'\bCloseDate\b', 'mislabeled-stylename': r'\bStyleName\b',
        'dirty-enum-values': r'\b(?:ColorName|DepartmentName|PromotionName|RegionCountryName)\b',
        'outlier-values': r'\b(?:YearlyIncome|SellingAreaSize|EmployeeCount)\b',
        'no-fact-on-employee-or-territory': r'\b(?:DimEmployee|DimSalesTerritory)\b',
        'date-dim-wider-than-facts': r'\bDimDate\b',
        'country-name-mismatch': r'\b(?:SalesTerritoryCountry|DimSalesTerritory)\b',
    }
    if rule not in tests:
        raise ValueError(f'new data_quality rule requires explicit audit routing: {rule}')
    return bool(re.search(tests[rule], sql, re.I))


def rank_probes():
    latest = 'SELECT StoreKey,ProductKey,max(DateKey) AS last_date FROM retail.FactInventory GROUP BY StoreKey,ProductKey'
    current = f'SELECT i.* FROM retail.FactInventory i JOIN ({latest}) l ON i.StoreKey=l.StoreKey AND i.ProductKey=l.ProductKey AND i.DateKey=l.last_date'
    # Deliberately diagnostic: retain existing reference calculation, only remove
    # dimension filtering and identify each object with its fact-side key.
    return [
        {'id': 'Q73', 'n': 10, 'column': 'gap', 'kind': 'other', 'ascending': False,
         'sql': f'WITH current_stock AS ({current}) SELECT i.ProductKey AS ProductKey,if(p.ProductKey=0,NULL,p.ProductName) AS ProductName,sum(i.OnHandQuantity)-sum(i.SafetyStockQuantity) AS gap FROM current_stock i LEFT JOIN retail.DimProduct p ON i.ProductKey=p.ProductKey GROUP BY i.ProductKey,p.ProductKey,p.ProductName'},
        {'id': 'Q87', 'n': 20, 'column': 'days_of_coverage', 'kind': 'other', 'ascending': True,
         'sql': f'WITH current_stock AS ({current}), inv AS (SELECT ProductKey,sum(OnHandQuantity) AS on_hand FROM current_stock GROUP BY ProductKey), recent AS (SELECT ProductKey,sum(SalesQuantity)/90.0 AS daily_qty FROM retail.FactOnlineSales WHERE DateKey BETWEEN toDate(\'2009-10-03\') AND toDate(\'2009-12-31\') GROUP BY ProductKey HAVING daily_qty>0) SELECT i.ProductKey AS ProductKey,if(p.ProductKey=0,NULL,p.ProductName) AS ProductName,round(i.on_hand/r.daily_qty,1) AS days_of_coverage FROM inv i JOIN recent r ON i.ProductKey=r.ProductKey LEFT JOIN retail.DimProduct p ON i.ProductKey=p.ProductKey'},
        {'id': 'Q97-1', 'n': 15, 'column': 'h2_vs_h1_pct', 'kind': 'percentage', 'ascending': False,
         'sql': "WITH amounts AS (SELECT ProductKey,sumIf(SalesAmount,toMonth(DateKey)<=6) AS h1_sales,sumIf(SalesAmount,toMonth(DateKey)>=7) AS h2_sales FROM retail.FactOnlineSales WHERE toYear(DateKey)=2009 GROUP BY ProductKey HAVING h1_sales>=1000 AND h2_sales>h1_sales) SELECT a.ProductKey AS ProductKey,if(p.ProductKey=0,NULL,p.ProductName) AS ProductName,(a.h2_sales-a.h1_sales)*100.0/a.h1_sales AS h2_vs_h1_pct FROM amounts a LEFT JOIN retail.DimProduct p ON a.ProductKey=p.ProductKey"},
        {'id': 'Q97-2', 'n': 15, 'column': 'sales_increase', 'kind': 'amount', 'ascending': False,
         'sql': "WITH amounts AS (SELECT ProductKey,sumIf(SalesAmount,toMonth(DateKey)<=6) AS h1_sales,sumIf(SalesAmount,toMonth(DateKey)>=7) AS h2_sales FROM retail.FactOnlineSales WHERE toYear(DateKey)=2009 GROUP BY ProductKey HAVING h2_sales>h1_sales) SELECT a.ProductKey AS ProductKey,if(p.ProductKey=0,NULL,p.ProductName) AS ProductName,a.h2_sales-a.h1_sales AS sales_increase FROM amounts a LEFT JOIN retail.DimProduct p ON a.ProductKey=p.ProductKey"},
        {'id': 'Q33', 'n': 20, 'column': 'times_together', 'kind': 'count', 'ascending': False,
         'sql': "WITH pairs AS (SELECT a.ProductKey AS product1_key,b.ProductKey AS product2_key,count() AS times_together FROM retail.FactOnlineSales a JOIN retail.FactOnlineSales b ON a.SalesOrderNumber=b.SalesOrderNumber AND a.ProductKey<b.ProductKey GROUP BY a.ProductKey,b.ProductKey) SELECT x.product1_key AS product1_key,x.product2_key AS product2_key,if(p1.ProductKey=0,NULL,p1.ProductName) AS product1,if(p2.ProductKey=0,NULL,p2.ProductName) AS product2,x.times_together AS times_together FROM pairs x LEFT JOIN retail.DimProduct p1 ON x.product1_key=p1.ProductKey LEFT JOIN retail.DimProduct p2 ON x.product2_key=p2.ProductKey"},
    ]


def run_probes(policy):
    from chdb import session
    db = Path(os.environ['SEMDEBT_DATA_DIR']) / 'chdb-eval'
    def open_session():
        sess = session.Session(str(db))
        sess.query('SET max_threads=1')
        sess.query('SET max_execution_time=30')
        return sess
    sess = open_session()
    results = []
    def execute(label, sql):
        nonlocal sess
        try:
            payload = json.loads(str(sess.query(sql, 'JSONCompact')))
        except Exception as error:
            results.append({'id': label, 'status': 'exec_error', 'error': str(error), 'sql': sql})
            print(f'PROBE_ERROR {label}: {error}', file=sys.stderr, flush=True)
            sess.close()
            sess = open_session()
            return None
        names = [c['name'] for c in payload['meta']]
        return [dict(zip(names, row, strict=True)) for row in payload['data']]
    try:
        for table in ('FactSales', 'FactOnlineSales', 'FactSalesQuota', 'FactInventory'):
            amount = ',sum(f.SalesAmount) AS total_sales,sumIf(f.SalesAmount,p.ProductKey=0) AS orphan_sales' if table in {'FactSales', 'FactOnlineSales'} else ''
            sql = f'SELECT toYear(f.DateKey) AS year,count() AS total_rows,countIf(p.ProductKey=0) AS orphan_rows,uniqExactIf(f.ProductKey,p.ProductKey=0) AS orphan_keys{amount} FROM retail.{table} f LEFT JOIN retail.DimProduct p ON f.ProductKey=p.ProductKey GROUP BY year ORDER BY year'
            rows = execute(table, sql)
            if rows is not None:
                results.append({'id': table, 'status': 'measured', 'rows': rows, 'sql': sql, 'scope': 'whole fact table by year; NOT the exact filtered loss of each reference'})
        sql = 'SELECT s.StoreKey AS StoreKey,s.StoreName AS StoreName,s.EmployeeKey AS EmployeeKey FROM retail.DimStore s LEFT JOIN retail.DimEmployee e ON s.EmployeeKey=e.EmployeeKey WHERE e.EmployeeKey=0 ORDER BY s.StoreKey'
        rows = execute('orphan-store-employee', sql)
        if rows is not None:
            results.append({'id': 'orphan-store-employee', 'status': 'measured', 'rows': rows, 'sql': sql})
        for probe in rank_probes():
            rows = execute(probe['id'], probe['sql'])
            if rows is None:
                continue
            key = lambda row: policy.quantize_tie(row[probe['column']], probe['kind'])
            rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))
            rows.sort(key=key, reverse=not probe['ascending'])
            if not rows:
                selected = []
                boundary = None
            else:
                boundary = key(rows[min(probe['n'], len(rows))-1])
                selected = [row for row in rows if key(row) <= boundary] if probe['ascending'] else [row for row in rows if key(row) >= boundary]
            orphans = [row for row in selected if row.get('ProductName', '') is None or row.get('product1', '') is None or row.get('product2', '') is None]
            results.append({**probe, 'status': 'measured_diagnostic_not_adopted_reference', 'domain_rows': len(rows), 'complete_boundary_rows': len(selected), 'boundary': str(boundary), 'orphan_topn_members': orphans, 'note': 'Q97 is judge-scored; 15 is its existing example cutoff, not a new question requirement. Diagnostic retains the existing arithmetic, not independent verification.'})
            print(f'RANK_PROBE {probe["id"]}: {len(orphans)} orphan boundary members', flush=True)
    finally:
        sess.close()
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--probe-orphans', action='store_true')
    mode.add_argument('--reuse-probes', action='store_true', help='render saved measured evidence without rerunning failed SQL')
    parser.add_argument('--current-only', action='store_true', help='audit both active rounds and manifest without claiming old probes were rerun')
    args = parser.parse_args()
    main_dir = Path(os.environ['SEMDEBT_MAIN_DIR'])
    source = main_dir / 'semantic/source.yaml'
    frozen = subprocess.run(['git', '-C', str(main_dir), 'show', 'semantic-v1:semantic/source.yaml'], check=True, capture_output=True).stdout
    if frozen != source.read_bytes():
        raise ValueError('source.yaml differs from semantic-v1; do not audit an unfrozen variant')
    quality = yaml.safe_load(source.read_text())['data_quality']
    if args.current_only:
        if args.probe_orphans or args.reuse_probes:
            parser.error('--current-only does not reuse or rerun historical probes')
        manifest = json.loads((ROOT/'refs/MANIFEST.json').read_text())
        by_path = {r['result_path']:r for r in manifest['records']}
        current = []
        for filename,generation in [('cube_100.yaml','active_original'),('new.yaml','active_new')]:
            for question in yaml.safe_load((ROOT/'questions'/filename).read_text())['questions']:
                for ref in question['refs']:
                    record = inspect_reference(question,ref,generation)
                    record['quality_routes'] = [item['id'] for item in quality if quality_match(item['id'],record['masked_sql'])]
                    record.pop('masked_sql')
                    stored = by_path[ref['result_path']]
                    if record['sql_sha256'] != stored['sql_sha256'] or digest(ROOT/ref['result_path']) != stored['sha256']:
                        raise ValueError('stale SQL/CSV manifest: '+ref['result_path'])
                    record['manifest_hashes_match'] = True
                    current.append(record)
        if len({r['question_id'] for r in current}) != 122 or len(current) != len(by_path):
            raise ValueError('incomplete active reference audit')
        result = {'scope':'122 active questions, both formal rounds', 'source_sha256':digest(source), 'quantization_sha256':manifest['unit_policy_sha256'], 'references':current,
                  'execution':'static SQL routes and current manifest hashes; historical probes were not rerun',
                  'purchase_event_ruling':'see audit/T05-purchase-events.md', 'T05b_independent_verification':'pending'}
        (ROOT/'audit/T05-current-data-quality.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        risks = [r for r in current if r['fact_product_inner_exposure'] or r['fact_employee_inner_exposure']]
        lines = ['# 第二轮现行参考数据质量审计','',f'122题／{len(current)}份正式参考的SQL及CSV哈希均与当前manifest一致。这里只做静态风险路由和哈希核对，不宣称所有业务定义已独立通过。',
                 '', '20题／24份内连接实测及修复见T05-inner-left.json/md；Q33当前参考已完成离线计算，旧审计30秒超时属于历史探查，不再代表当前参考未验证。',
                 '', '纯退货购买事件口径见T05-purchase-events.md；T05b与Q79独立成员复现仍待执行。', '', '| 仍存在内连接路径 | 参考 | 处置依据 |','|---|---|---|']
        for r in risks:
            lines.append(f"| {r['question_id']} | {r['result_path']} | 已测过滤后结果无影响；见逐参考对照，不把路径存在直接判为丢失结果 |")
        lines += ['', f'semantic/source.yaml与semantic-v1逐字核对；冻结语义层、企业约定及主仓库评分代码均未改。完整数据质量条目路由及{len(current)}份记录见配套JSON。旧版审计作为修复前历史保留。']
        (ROOT/'audit/T05-current-data-quality.md').write_text('\n'.join(lines)+'\n')
        print(json.dumps({'questions':122,'references':len(current),'remaining_inner_paths':len(risks),'historical_probes_rerun':False}))
        return
    original_path = ROOT / 'questions/cube_100.yaml'
    legacy_path = ROOT / 'questions/new.yaml'
    draft_path = ROOT / 'audit/T05-rewrite-draft.md'
    originals = yaml.safe_load(original_path.read_text())['questions']
    legacy = yaml.safe_load(legacy_path.read_text())['questions']
    archived = yaml.safe_load((ROOT / 'audit/reviews/2026-10-16-t05-first-questions.yaml').read_text())['questions']
    if legacy != archived:
        raise ValueError('questions/new.yaml is no longer the archived first round; update generation routing before auditing, do not silently call it legacy or missing SQL')
    planned = re.findall(r'^\| (D\d{2})→(Q\d{3}) \| ([^|]+) \| ([^|]+) \|$', draft_path.read_text(), re.M)
    if len(originals) != 100 or len(legacy) != 22 or len(planned) != 22:
        raise ValueError('expected 100 active originals, 22 superseded artifacts, 22 approved designs')
    records = [inspect_reference(q, r, generation) for qs, generation in [(originals, 'active_original'), (legacy, 'superseded_first_round')] for q in qs for r in q['refs']]
    checklist = []
    for item in quality:
        matches = [r for r in records if quality_match(item['id'], r['masked_sql'])]
        checklist.append({'id': item['id'], 'title': item['title'], 'severity': item['severity'],
                          'review_mode': 'candidate routing, not a passed assertion',
                          'manual_review': QUALITY_NOTES[item['id']],
                          'active_question_ids': sorted({r['question_id'] for r in matches if r['generation'] == 'active_original'}),
                          'legacy_question_ids': sorted({r['question_id'] for r in matches if r['generation'] == 'superseded_first_round'})})
    for record in records:
        del record['masked_sql']
    policy, policy_hash = load_unit_policy()
    if args.reuse_probes:
        saved = json.loads((ROOT / 'audit/T05-reference-data-quality.json').read_text())
        if saved['source_sha256'] != digest(source) or saved['quantization_sha256'] != policy_hash:
            raise ValueError('cannot reuse probes across semantic or quantization versions')
        specifications = {probe['id']: probe['sql'] for probe in rank_probes()}
        for probe in saved['probes']:
            if probe['id'] in specifications and probe['sql'] != specifications[probe['id']]:
                raise ValueError('diagnostic SQL changed; saved probe cannot stand in for new execution')
        probes = saved['probes']
    else:
        probes = run_probes(policy) if args.probe_orphans else []
    manifest = json.loads((ROOT / 'refs/MANIFEST.json').read_text())
    manifest_by_path = {r['result_path']: r for r in manifest['records']}
    for record in records:
        stored = manifest_by_path[record['result_path']]
        record['result_recompute_status'] = 'current_sql' if stored['sql_sha256'] == record['sql_sha256'] else 'stale_SQL_hash_needs_recompute'
        record['csv_sha256_matches_manifest'] = digest(ROOT / record['result_path']) == stored['sha256']
        if not record['csv_sha256_matches_manifest']:
            record['result_recompute_status'] = 'stale_CSV_hash_needs_recompute'
        if record['result_recompute_status'] != 'current_sql':
            record['assessment'] += ' SQL已改但结果仍旧版，不能验收。'
    q74 = next(r for r in manifest['records'] if r['result_path'] == 'refs/cube/Q74-1.csv')
    ranked_corrections = []
    for record in manifest['records']:
        if record['question_id'] not in {'Q74', 'Q87', 'Q97'}:
            continue
        with (ROOT / record['result_path']).open() as stream:
            rows = list(csv.DictReader(stream))
        state = next(r['result_recompute_status'] for r in records if r['result_path'] == record['result_path'])
        if state == 'current_sql' and (not rows or 'ProductKey' not in rows[0]):
            raise ValueError('corrected ranked reference must retain ProductKey')
        ranked_corrections.append({'question_id': record['question_id'], 'result_path': record['result_path'],
                                   'row_count': len(rows), 'sha256': record['sha256'], 'recompute_status': state,
                                   'orphan_topn_members': [row for row in rows if row['ProductName'] == '\\N'] if state == 'current_sql' else None})
    result = {'date': '2026-10-16', 'scope': '100 active SQL questions; 22 approved designs pending SQL; legacy 22 SQL inspected separately',
              'source_sha256': digest(source), 'cube_sha256': digest(original_path), 'legacy_sha256': digest(legacy_path), 'draft_sha256': digest(draft_path),
              'quantization_sha256': policy_hash, 'checklist': checklist, 'references': records,
              'approved_new_questions': [{'question_id': qid, 'design_id': did, 'text_zh': text.strip(), 'sql_status': 'missing_second_round_SQL', 'review_note': NEW_RISKS.get(qid, '尚无第二轮SQL，不能宣称已排除不必要维表关联。')} for did, qid, text, _ in planned],
              'probes': probes, 'probe_execution': 'saved evidence reused; no rerun' if args.reuse_probes else 'executed' if args.probe_orphans else 'not run',
              'ranked_corrected_references': ranked_corrections, 'Q74_reference': q74,
              'execution_notes': ['Q74 was built and targeted-check verified before the concurrent rules backfill.',
                                  'A targeted Q87/Q97 build failed at session creation with CANNOT_OPEN_FILE while another validation owned chdb-eval; no processes were terminated.',
                                  'The concurrent rules-backfill build subsequently generated Q87/Q97 from the corrected SQL; this audit checked current SQL/CSV hashes and exact orphan key sets against its earlier probes.',
                                  'The full T04 offline validator passed using the T02 working-branch selection dependency; this is not an independent pandas recomputation.'],
              'limitations': ['static SQL screening is not an AST proof and does not assign unknown catalog attributes', 'per-table/year orphan amounts are not per-question filtered losses', 'no production scorer changes or 600-candidate verdict claims', 'second-round references have not been generated or independently verified']}
    path = ROOT / 'audit/T05-reference-data-quality.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    active = [r for r in records if r['generation'] == 'active_original']
    hits = [r for r in active if r['fact_product_inner_exposure'] or r['fact_employee_inner_exposure']]
    lines = ['# 参考答案数据质量审计（2026-10-16）', '',
             '按semantic-v1冻结的source.yaml/data_quality清单筛查；没有修改语义层、评分器或容差。', '',
             '## 覆盖边界', '',
             f'- 122题全部登记：原100题的{len(active)}份现行SQL已扫描；第二轮22题均尚无正式SQL，逐题记为待完成，不记通过。',
             f'- 另扫描第一轮22题的{len(records)-len(active)}份旧SQL，明确为已被替代的历史工件，不冒充第二轮参考。',
             '- 下表是风险路由与人工审阅，不是自动证明所有参考正确；未测的逐题过滤后损失不冒充已知。', '',
             '## 两类孤儿键的逐参考命中', '',
             f'现行产品内连接风险：{len({r["question_id"] for r in hits if r["fact_product_inner_exposure"]})}题／{sum(r["fact_product_inner_exposure"] for r in hits)}份参考。',
             f'现行事实聚合＋员工内连接风险：{len({r["question_id"] for r in hits if r["fact_employee_inner_exposure"]})}题。员工目录／层级查询另记，不据此声称缺员工键没有风险。', '',
             '| 题号 | 参考 | 事实域 | 风险／建议（未批量修复） |', '|---|---|---|---|']
    for r in hits:
        lines.append(f'| {r["question_id"]} | {r["result_path"]} | {", ".join(r["fact_tables"])} | {r["assessment"]} |')
    lines += ['', '## Q74已批准修复与孤儿入选', '',
              '这是更正外部基准参考，裁决见decisions/2026-10-16-q74-orphan-products-reference-correction.md。分母在完整FactSales域先算，ProductKey保身份，缺名称NULL；不把孤儿合并、不丢事实。', '',
              f'当前参考{q74["row_count"]}行；完整边界不是要求候选交N+k。下列是合法边界域内孤儿产品，不代表所有边界成员都必须同时选择。', '',
              '| 门店键 | 门店 | 产品键 | 销售额 | 份额% | 严格前缀／边界 |', '|---|---|---|---:|---:|---|']
    for row in q74['postprocess_details'].get('orphan_topn_members', []):
        lines.append(f'| {row["StoreKey"]} | {row["StoreName"]} | {row["ProductKey"]} | {row["product_sales"]} | {row["pct_of_store"]} | {row["selection_role"]} |')
    if not q74['postprocess_details'].get('orphan_topn_members'):
        lines.append('| — | 本次没有孤儿入选，明细仍保留产品键 | — | — | — | — |')
    lines += ['', '## 其他排名域的孤儿前N诊断（不自动改参考）', '']
    for probe in probes:
        if probe['id'] in {p['id'] for p in rank_probes()}:
            if probe['status'] == 'exec_error':
                lines.append(f'- {probe["id"]}：执行失败，未验证，不能记孤儿数0。错误：{probe["error"]}。未静默重试。')
            else:
                lines.append(f'- {probe["id"]}：{probe["status"]}；孤儿边界成员{len(probe["orphan_topn_members"])}。逐个产品键、数值及复算SQL见JSON的probes。')
    lines += ['', 'Q97的15只来自既有judge示例截断，不是题意新增限制。诊断计算未作为跨厂商独立复核。', '',
              '## 已更正排名参考中的孤儿产品键', '',
              'Q87／Q97按用户“孤儿进入前N则按键列出”条件修复，不批量更改其他参考。Q74另有独立裁决。ProductKey必须按对象身份精确匹配，不能把0.5%金额容差用于产品键；此项也须进入后续通用契约及合成测试。', '',
              '| 题号／参考 | 参考行数 | 重算状态 | 孤儿入选数 |', '|---|---:|---|---:|']
    lines += [f'| {r["question_id"]} / {r["result_path"]} | {r["row_count"]} | {r["recompute_status"]} | {len(r["orphan_topn_members"]) if r["orphan_topn_members"] is not None else "未重算，不记0"} |' for r in ranked_corrections]
    for correction in ranked_corrections:
        if correction['orphan_topn_members']:
            lines += ['', f'### {correction["result_path"]}', '', '| 产品键 | 名称 | 参考数值（原列名） |', '|---|---|---|']
            for row in correction['orphan_topn_members']:
                values = {k: v for k, v in row.items() if k not in {'ProductKey', 'ProductName'}}
                lines.append(f'| {row["ProductKey"]} | NULL（名称缺失） | {json.dumps(values, ensure_ascii=False)} |')
    lines += ['', '## 数据域探查（不是每题过滤后的精确损失）', '', '| 事实域／年 | 全部行 | 孤儿行 | 孤儿销售额（如适用） |', '|---|---:|---:|---:|']
    for probe in probes:
        if probe['id'].startswith('Fact') and probe['status'] == 'measured':
            for row in probe['rows']:
                lines.append(f'| {probe["id"]} / {row["year"]} | {row["total_rows"]} | {row["orphan_rows"]} | {row.get("orphan_sales", "不加总跨期库存／多场景目标")} |')
        elif probe['id'] == 'orphan-store-employee' and probe['status'] == 'measured':
            lines += ['', f'员工缺失实测：{json.dumps(probe["rows"], ensure_ascii=False)}。新版Q112必须保留此门店及EmployeeKey 245；现行原题没有相应事实内连接，不把这个0解读为全题库没有经理风险。']
    if not probes:
        lines.append('本次未运行数据库探查，不把未测记0；使用--probe-orphans执行。')
    lines += ['', '## data_quality完整清单', '', '| 条目 | 待审原题候选（仅路由） | 人工核对／保留项 |', '|---|---|---|']
    lines += [f'| {c["id"]} | {"、".join(c["active_question_ids"]) or "未命中静态模式；非通过证明"} | {c["manual_review"]} |' for c in checklist]
    lines += ['', '## 原100题逐题索引', '', '| 题号 | 参考数 | 此次两类孤儿检查结论 |', '|---|---:|---|']
    for q in originals:
        rs = [r for r in active if r['question_id'] == q['id']]
        lines.append(f'| {q["id"]} | {len(rs)} | {"；".join(dict.fromkeys(r["assessment"] for r in rs))} |')
    lines += ['', '## 第二轮22题逐题检查（尚无SQL，全部待完成）', '', '| 题号 | 状态 | 设计级检查要求 |', '|---|---|---|']
    lines += [f'| {q["question_id"]} | 未生成SQL／未验参考 | {q["review_note"]} |' for q in result['approved_new_questions']]
    lines += ['', '## 第一轮工件的历史风险（不作为第二轮批准）', '', '| 题号 | 参考 | 风险 |', '|---|---|---|']
    lines += [f'| {r["question_id"]} | {r["result_path"]} | {r["assessment"]} |' for r in records if r['generation'] == 'superseded_first_round' and (r['fact_product_inner_exposure'] or r['fact_employee_inner_exposure'])]
    lines += ['', '## 执行与后续', '',
              '`uv run --locked python scripts/audit_reference_data_quality.py --probe-orphans`：只读chdb-eval，生成本报告及JSON；单条失败留原错误并重置会话，不静默重试。',
              '定向验证：`uv run --locked python scripts/build_refs.py --question Q74 --question Q87 --question Q97 --check`；窄检查：`uv run --locked python scripts/validate_t04.py`。',
              f'本次证据方式：{result["probe_execution"]}；`--reuse-probes`只重新渲染已保存证据，不声称再次执行或挽回Q33超时。',
              '其余风险须逐题决定未知组／可分类样本范围，不直接把所有INNER改成LEFT，也不擅自给孤儿填品牌、品类、上市日。',
              '600条尚未复验；后续固定输入分别记录契约变化、参考修复及联合影响，T19披露参考偏离，T02/G0保留历史并更新新证据。',
              'T05b须pandas独立复算Q74完整边界及孤儿产品键；本轮SQL诊断和同引擎复验均不代替独立验收。', '']
    lines += ['## 执行记录及并行任务边界', '',
              '- Q74定向构建与--check实际完成；随后新增保键／缺名／重复对象合成检查通过。',
              '- 一次Q87/Q97定向构建在连接阶段因CANNOT_OPEN_FILE停止，没有更新这两题CSV；未终止持锁进程。',
              '- 并行rules回填随后按修正SQL完成构建。本审计重新检查SQL指纹、CSV哈希及孤儿键集合，当前Q74/Q87/Q97四份结果均与现行SQL对应；不把并行任务的构建说成本会话再次执行。',
              '- 当前完整T04离线检查通过（100题113份参考）；尚未合并的selection依赖来自T02工作分支，验证时SEMDEBT_MAIN_DIR指向该分支工作区。没有把第一轮22题的现存参考纳入第二轮验收。',
              '- Q74修复前后完整边界成员925个未变，925行份额全部变化且均超过0.5%相对容差；这是参考行的变化，不是600条候选判定翻转数。',
              '- 本审计不覆盖另一会话的rules／通用评分器补丁，不重复提交或回滚其改动；600条影响以那份固定输入、分轴复验的实际结果为准，当前不预报0。', '']
    (ROOT / 'audit/T05-reference-data-quality.md').write_text('\n'.join(lines))
    print(json.dumps({'active_SQL_questions': 100, 'approved_new_SQL_pending': 22, 'legacy_SQL_questions': 22, 'active_product_risk_questions': len({r['question_id'] for r in hits if r['fact_product_inner_exposure']}), 'active_employee_fact_inner_questions': len({r['question_id'] for r in hits if r['fact_employee_inner_exposure']}), 'probe_errors': sum(p['status'] == 'exec_error' for p in probes)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
