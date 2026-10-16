#!/usr/bin/env python
"""Apply the data-only new-question rewrites authorized on 2026-10-16."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from build_refs import effective_rules, load_unit_policy
from check_q79_membership import member_counts

ROOT=Path(__file__).resolve().parent.parent
CHANGED={'Q109','Q112','Q113','Q114','Q116'}


def proposals(question):
    qid=question['id']; base=question['refs'][0]['sql']
    if qid=='Q109':
        return ('今年各季度的日均销售额，各比去年同期增长了百分之多少？',
                'For each quarter this year, how much did average daily sales grow year over year?',
                '保留日粒度聚合、完整日历分母及同比增长；移除与周末重合的节假日分类。',
                [('完整季度日历，含零销售日；先逐日汇总再按季度计算日均值',
                  """WITH daily AS (
SELECT d.DateKey AS day,toQuarter(d.DateKey) AS quarter,toYear(d.DateKey) AS y,sum(f.SalesAmount) AS day_sales
FROM retail.DimDate d LEFT JOIN retail.FactOnlineSales f ON d.DateKey=f.DateKey
WHERE toYear(d.DateKey) IN (2008,2009) GROUP BY day,quarter,y)
SELECT quarter,(avgIf(day_sales,y=2009)/nullIf(avgIf(day_sales,y=2008),0)-1)*100 AS daily_sales_growth_pct
FROM daily GROUP BY quarter""")])
    if qid=='Q112':
        return ('2009年，以正式销售目标的120%为挑战线，每位门店经理手下有多少家门店未达到这条线？这些门店距离挑战线的销售额缺口合计是多少？',
                'In 2009, using 120% of the official sales target as a stretch line, how many stores under each manager fell short, and what was their total shortfall?',
                '保留逐店实际与正式目标对齐、实体派生缺口、按经理二次汇总；120%是题干挑战线，不改正式目标定义。',
                [('正式目标ScenarioKey=2；挑战缺口=max(1.2×目标−实际,0)；按经理汇总',base.replace('t.quota_amount-a.sales_amount','1.2*t.quota_amount-a.sales_amount'))])
    if qid=='Q113':
        return ('将各门店2009年的全年正式销售目标平均分摊到12个月后，哪些门店出现过连续至少3个月未达到月度均摊目标的时段？列出门店、起止月份和连续月数。',
                'After spreading each store’s official 2009 annual sales target evenly across 12 months, find periods of at least three consecutive months below that monthly target; report the store, start month, end month and duration.',
                '保留计划与实际的月粒度对齐和连续区间识别；改为题干明确的年度目标均摊，避免固定月度达成率使区间为空或整年恒定。',
                [('全年正式目标除以12；完整12月日历；无销售月份按0；无正式目标的门店不参与',
                  """WITH actual AS (SELECT StoreKey,toMonth(DateKey) AS m,sum(SalesAmount) AS sales_amount FROM retail.FactSales WHERE toYear(DateKey)=2009 GROUP BY StoreKey,m),
targets AS (SELECT StoreKey,sum(SalesAmountQuota) AS annual_quota FROM retail.FactSalesQuota WHERE ScenarioKey=2 AND toYear(DateKey)=2009 GROUP BY StoreKey),
monthly AS (SELECT s.StoreKey AS StoreKey,s.StoreName AS StoreName,toUInt8(n.number+1) AS m,ifNull(a.sales_amount,0) AS sales_amount,t.annual_quota/12 AS monthly_target
FROM retail.DimStore s CROSS JOIN numbers(12) n LEFT JOIN actual a ON s.StoreKey=a.StoreKey AND n.number+1=a.m
LEFT JOIN targets t ON s.StoreKey=t.StoreKey WHERE t.annual_quota>0),
under AS (SELECT StoreKey,StoreName,m,toInt64(m)-toInt64(row_number() OVER (PARTITION BY StoreKey ORDER BY m)) AS island
FROM monthly WHERE sales_amount<monthly_target)
SELECT StoreName,min(m) AS start_month,max(m) AS end_month,count() AS months
FROM under GROUP BY StoreKey,StoreName,island HAVING months>=3""")])
    if qid=='Q114':
        refs=[]
        for positive in (False,True):
            source='(SELECT * FROM retail.FactOnlineSales WHERE SalesQuantity>0)' if positive else 'retail.FactOnlineSales'
            for inclusive in (True,False):
                condition='f.first_date>=addDays(c.cutoff,-89) AND f.first_date<=c.cutoff' if inclusive else 'f.first_date>=addDays(c.cutoff,-90) AND f.first_date<c.cutoff'
                refs.append((('含截止日[T-89,T]' if inclusive else '不含截止日[T-90,T)')+'；购买事件='+('SalesQuantity>0' if positive else '全部行'),
                             f"""WITH firsts AS (SELECT CustomerKey,min(DateKey) AS first_date FROM {source} GROUP BY CustomerKey),
cutoffs AS (SELECT toLastDayOfMonth(addMonths(toDate('2007-01-01'),number)) AS cutoff FROM numbers(6))
SELECT c.cutoff,countIf({condition}) AS new_customers FROM firsts f CROSS JOIN cutoffs c GROUP BY c.cutoff"""))
        return ('以2007年上半年每个月末为截止日，近90天内首次购买的新客各有多少？',
                'At each month end in the first half of 2007, how many customers made their first-ever purchase within the preceding 90 days?',
                '保留全历史首购、滚动90日窗与逐月截止日；改用实际存在首购分布的时期，不用活跃客户替代新客。',refs)
    if qid=='Q116':
        refs=[]
        for positive in (False,True):
            source='(SELECT * FROM retail.FactOnlineSales WHERE SalesQuantity>0)' if positive else 'retail.FactOnlineSales'
            refs.append(('首购次日起7个自然日；截止2009-12-31已完成观察；购买事件='+('SalesQuantity>0' if positive else '全部行'),
                         f"""WITH cohorts AS (SELECT CustomerKey,min(DateKey) AS first_date FROM {source} GROUP BY CustomerKey
HAVING addDays(first_date,7)<=toDate('2009-12-31')),
observed AS (SELECT c.CustomerKey AS CustomerKey,c.first_date AS first_date,countDistinctIf(f.SalesOrderNumber,f.DateKey>c.first_date AND f.DateKey<=addDays(c.first_date,7)) AS purchases
FROM cohorts c LEFT JOIN {source} f ON c.CustomerKey=f.CustomerKey GROUP BY c.CustomerKey,c.first_date)
SELECT toStartOfMonth(first_date) AS cohort_month,countIf(purchases>0)*100.0/count() AS repurchase_pct FROM observed GROUP BY cohort_month"""))
        return ('以2009年12月31日为观察截止日，按客户的真实首购月份分群，首购次日起7个自然日内的复购率分别是多少？排除观察期不足7天的客户。',
                'As of December 31, 2009, by true first-purchase month, what share of customers purchased again during the seven calendar days starting the day after their first purchase? Exclude customers without seven full days of follow-up.',
                '保留全历史首购分群、客户级复购事件、完整随访和分组比率；缩短明确观察窗，避免90天复购率全满。',refs)
    raise ValueError('unreviewed question')


def main():
    before=json.loads((ROOT/'audit/T05-degeneracy-before.json').read_text())
    if set(before['hits'])!=CHANGED:
        raise ValueError('review unexpected degeneration before applying rewrites')
    path=ROOT/'questions/new.yaml'; questions=json.loads(path.read_text())['questions']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=before['question_sha256']:
        raise ValueError('questions changed since the pre-rewrite audit')
    output=ROOT/'audit/T05-degeneracy-rewrites.json'
    if output.exists():raise ValueError('rewrites already applied')
    policy,policy_hash=load_unit_policy()
    from chdb import session
    sess=session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR'])/'chdb-eval'))
    records=[]
    try:
        sess.query('SET max_threads=1');sess.query('SET max_execution_time=0')
        for q in questions:
            original=deepcopy(q); old=next(r for r in before['records'] if r['question_id']==q['id'])
            item={'question_id':q['id'],'original_question':q['text_zh'],'original_hits':old['hits'],'changed':q['id'] in CHANGED}
            if q['id'] in CHANGED:
                text,en,ability,refs=proposals(q); newrefs=[]; seen={}
                kinds=effective_rules(q,q['refs'][0])['value_kinds']
                for interpretation,sql in refs:
                    payload=json.loads(str(sess.query(sql,'JSONCompact')))
                    signature=frozenset(member_counts(payload['data'],kinds,policy).items())
                    if signature in seen:
                        newrefs[seen[signature]]['interpretation']+='；亦覆盖：'+interpretation
                        continue
                    seen[signature]=len(newrefs)
                    rules={'ordered':False,'top_n':None,'tie_columns':[],'value_kinds':kinds,'value_types':[c['type'] for c in payload['meta']]}
                    newrefs.append({'interpretation':interpretation,'sql':sql,'result_path':f"refs/new/{q['id']}-{len(newrefs)+1}.csv",'rules':rules})
                q.update(text_zh=text,text_en=en,refs=newrefs,rules=deepcopy(newrefs[0]['rules']),
                         scoring_notes='2026-10-16退化新题裁决改写。'+ability+' 购买事件若有歧义仍保留全部行与正销量两种参考，相同量化结果共用参考；时间窗口以题干及逐参考解读为准。原题及A/B/C证据见audit/T05-degeneracy-before.json，改写交接见audit/T05-degeneracy-rewrites.json。')
                item.update(original_record=original,preserved_ability=ability,new_reference_count=len(newrefs))
                print(q['id'],len(original['refs']),'->',len(newrefs),'references',flush=True)
            item['new_question']=q['text_zh']; item['new_reference_paths']=[r['result_path'] for r in q['refs']]
            records.append(item)
    finally:sess.close()
    path.write_text(json.dumps({'questions':questions},ensure_ascii=False,indent=2)+'\n')
    output.write_text(json.dumps({'decision':'2026-10-16-tie-order-and-degenerate-new-questions.md section 2','before_audit_sha256':hashlib.sha256((ROOT/'audit/T05-degeneracy-before.json').read_bytes()).hexdigest(),
                                  'unit_policy_sha256':policy_hash,'questions_reviewed':22,'rewritten_questions':sorted(CHANGED),'post_rewrite_audit_required':True,'records':records},ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
