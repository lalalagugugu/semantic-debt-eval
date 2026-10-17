#!/usr/bin/env python
"""List unresolved semantic defaults with measured alternatives, without ruling."""
from collections import Counter, defaultdict
import argparse
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path

from build_refs import effective_rules, exact_percentile, load_unit_policy, postprocess_reference
from check_rules_impact import csv_rows

ROOT=Path(__file__).resolve().parent.parent
OUTPUT=ROOT/'audit/2026-10-17-semantic-gaps.json'


def signature(rows):
    values=Counter(json.dumps(row,ensure_ascii=False,default=str) for row in rows)
    return hashlib.sha256(json.dumps(sorted(values.items()),ensure_ascii=False).encode()).hexdigest()


def profile(rows):
    return {'rows':len(rows),'sha256':signature(rows)}


def ranks(values):
    counts=Counter(values);result={};offset=0
    for value,count in sorted(counts.items()):
        result[value]=offset+(count+1)/2
        offset+=count
    return [result[v] for v in values]


def correlation(xs,ys):
    mx=sum(xs)/len(xs);my=sum(ys)/len(ys)
    xx=sum((x-mx)**2 for x in xs);yy=sum((y-my)**2 for y in ys)
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys,strict=True))/math.sqrt(xx*yy) if xx and yy else None


def weighted_correlations(rows):
    """Exact tie midranks from joint frequencies, without expanding fact rows."""
    def midranks(counts):
        offset=0;result={}
        for value,count in sorted(counts.items()):
            result[value]=offset+(count+1)/2;offset+=count
        return result
    xcounts=Counter();ycounts=Counter()
    for x,y,n in rows:xcounts[x]+=n;ycounts[y]+=n
    xr=midranks(xcounts);yr=midranks(ycounts)
    def corr(transform):
        total=sum(r[2] for r in rows)
        values=[(*transform(x,y),n) for x,y,n in rows]
        mx=sum(x*n for x,y,n in values)/total;my=sum(y*n for x,y,n in values)/total
        xx=sum(n*(x-mx)**2 for x,y,n in values);yy=sum(n*(y-my)**2 for x,y,n in values)
        return sum(n*(x-mx)*(y-my) for x,y,n in values)/math.sqrt(xx*yy) if xx and yy else None
    return corr(lambda x,y:(x,y)),corr(lambda x,y:(xr[x],yr[y]))


def correlation_details(output):
    if output.exists():raise ValueError('correlation audit is append-only')
    questions={q['id']:q for q in json.loads((ROOT/'questions/cube_100.yaml').read_text())['questions']}
    unit,sha=load_unit_policy()
    from chdb import session
    sess=session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR'])/'chdb-eval'))
    records=[]
    try:
        sess.query('SET max_threads=1');sess.query('SET max_execution_time=0')
        query=lambda sql:json.loads(str(sess.query(sql,'JSONCompact')))['data']
        for qid,sql in [('Q48','WITH o AS (SELECT StoreKey,sum(DownTime) AS downtime FROM retail.FactITSLA GROUP BY StoreKey),s AS (SELECT StoreKey,sum(SalesAmount) AS sales FROM retail.FactSales GROUP BY StoreKey) SELECT ifNull(o.downtime,0),s.sales FROM s LEFT JOIN o ON s.StoreKey=o.StoreKey'),('Q91','SELECT c.YearlyIncome,sum(f.SalesAmount) AS spending FROM retail.FactOnlineSales f JOIN retail.DimCustomer c ON f.CustomerKey=c.CustomerKey GROUP BY f.CustomerKey,c.YearlyIncome')]:
            rows=[r for r in query(sql) if all(v is not None for v in r)]
            a=correlation([r[0] for r in rows],[r[1] for r in rows]);b=correlation(ranks([r[0] for r in rows]),ranks([r[1] for r in rows]))
            records.append({'question_id':qid,'observations':len(rows),'pearson':a,'spearman':b,'results_equal':unit.quantize_tie(a,'ratio')==unit.quantize_tie(b,'ratio')})
        sql=questions['Q86']['refs'][0]['sql'];stop=sql.index('),\nstats AS')
        counts=query(sql[:stop]+') SELECT ProductSubcategoryName,DiscountPercent,SalesQuantity,count() FROM enriched GROUP BY ProductSubcategoryName,DiscountPercent,SalesQuantity')
        groups=defaultdict(list)
        for name,x,y,n in counts:groups[name].append((x,y,n))
        examples=[];all_examples=[]
        for name,rows in groups.items():
            a,b=weighted_correlations(rows)
            item={'subcategory':name,'observations':sum(r[2] for r in rows),'pearson':a,'spearman':b,'results_equal':unit.quantize_tie(a,'ratio')==unit.quantize_tie(b,'ratio')}
            all_examples.append(item)
            if item['observations']>100:examples.append(item)
        records.append({'question_id':'Q86','groups':len(examples),'different_groups':sum(not r['results_equal'] for r in examples),'results_equal':all(r['results_equal'] for r in examples),'sample_cutoff_review':{'interpretations':[0,100],'no_cutoff_groups':len(all_examples),'over_100_groups':len(examples),'results_equal':len(all_examples)==len(examples),'rule':'题面及L1未给样本下限；100只是当前judge示例的声明，不自行设为企业默认'},'details':examples})
    finally:sess.close()
    output.write_text(json.dumps({'unit_policy_sha256':sha,'accepted_reference_changes':False,'records':records},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k!='details'} for r in records],ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--correlation-output',type=Path)
    args=parser.parse_args()
    if args.correlation_output:
        correlation_details(args.correlation_output)
        return
    if args.output.exists():
        raise ValueError('gap audit is append-only; archive a new run explicitly')
    questions={q['id']:q for name in ('cube_100','new') for q in json.loads((ROOT/f'questions/{name}.yaml').read_text())['questions']}
    manifest={r['result_path']:r for r in json.loads((ROOT/'refs/MANIFEST.json').read_text())['records']}
    unit,unit_sha=load_unit_policy()
    main=Path(os.environ['SEMDEBT_MAIN_DIR'])
    source_sha={name:hashlib.sha256((main/'semantic'/name).read_bytes()).hexdigest() for name in ('conventions.md','source.yaml')}
    entries=[]
    def add(gid,qids,topic,missing,alternatives,equal=None,status='待用户裁决；不新增或替换参考'):
        entries.append({'id':gid,'questions':qids,'topic':topic,'missing_in_conventions_and_L1':missing,'interpretation_count':len(alternatives),'alternatives':alternatives,'results_equal':equal,'status':status})
        print(gid,topic,equal,flush=True)
    def existing(qid):
        q=questions[qid];alternatives=[];signatures=[]
        for ref in q['refs']:
            record=manifest[ref['result_path']];rows=csv_rows(record)
            normalized=[[unit.quantize_tie(v,k) for v,k in zip(row,effective_rules(q,ref)['value_kinds'],strict=True)] for row in rows]
            item={'interpretation':ref['interpretation'],'reference':ref['result_path'],'columns':record['columns'],**profile(normalized)}
            alternatives.append(item);signatures.append(item['sha256'])
        return alternatives,len({json.dumps(s,sort_keys=True) for s in signatures})==1
    # Genuine unspecified defaults, not already-defined channels or transaction filters.
    for gid,qid,topic,missing in [
        ('G03','Q38','预测准确度指标','场景和收入科目已定，但未定义准确度究竟报告绝对百分比误差还是其互补准确率'),
        ('G06','Q76','回头客订单累计范围','题面给出至少两笔订单，但未指定按客户全目录累计，还是在当前品类内累计；L1没有回头客指标'),
        ('G10','Q97','反弹幅度与大幅阈值','毛利／销售额定义不解决反弹按金额还是比例及大幅下限；现有两份只作judge示例'),
        ('G11','Q98','全年指哪一年或逐年','当前问题未点名年份；用户明确允许该问法多解，L1今天并未唯一规定这句全年是单年还是每年'),
        ('G14','Q119','公司排名的并列编号','L1未定义竞赛排名1/1/3还是稠密排名1/1/2；不是改并列成员的全局量化规则'),
        ('G15','Q121','变异系数标准差分母','L1没有变异系数指标，未指定12个月按总体还是样本；不能由参考作者新增企业定义'),
    ]:
        alternatives,equal=existing(qid)
        add(gid,[qid],topic,missing,alternatives,equal,'问法歧义现有参考保留；是否补统一默认待用户拍板')
    from chdb import session
    sess=session.Session(str(Path(os.environ['SEMDEBT_DATA_DIR'])/'chdb-eval'))
    def query(sql):return json.loads(str(sess.query(sql,'JSONCompact')))['data']
    try:
        sess.query('SET max_threads=1');sess.query('SET max_execution_time=0')
        rows=query("SELECT count() FROM system.columns WHERE database='retail' AND table='FactSales' AND name='SalesOrderNumber'")
        assert rows==[[0]]
        store_rows=query('SELECT countDistinct(StoreKey),count() FROM retail.FactSales')[0]
        add('G01',['Q13','Q28'],'全渠道交易单位与平均订单金额','约定2规定门店走FactSales，约定8客单价需要订单号，但全渠道汇总表没有订单号；未定义交易笔是否指聚合行',[
            {'interpretation':'交易=全渠道事实汇总行；参考当前avg(SalesAmount)/count()','stores':store_rows[0],'records':store_rows[1]},
            {'interpretation':'交易=真实订单，按订单金额计算均值','computable':False,'reason':'FactSales没有订单号，不能从汇总行还原订单；不能伪造等价结果'}],None)
        sql=questions['Q47']['refs'][0]['sql']
        left=query(sql)
        right=query('SELECT s.StoreName,avg(m.downtime) FROM (SELECT StoreKey,MachineKey,sum(DownTime) AS downtime FROM retail.FactITSLA WHERE DownTime IS NOT NULL GROUP BY StoreKey,MachineKey) m JOIN retail.DimStore s ON m.StoreKey=s.StoreKey GROUP BY s.StoreKey,s.StoreName')
        add('G02',['Q47'],'平均停机的分母','L1定义停机总时长、故障次数，未定义机器平均是按事件平均还是先按机器累计后平均',[
            {'interpretation':'每次故障的平均停机时长',**profile(left)}, {'interpretation':'每机器累计停机时长的平均',**profile(right)}],signature(left)==signature(right))
        sql=questions['Q39']['refs'][0]['sql']
        marker="least(dateDiff('day',toDate('2007-01-01'),introduction_date),dateDiff('day',introduction_date,toDate('2010-01-01')))"
        assert marker in sql
        a=query(sql);b=query(sql.replace(marker,'toInt64(90)'))
        add('G04',['Q39'],'新老产品观察窗口','L1描述上市日期，未定义新品的业务年限及上市前后观察窗口；以下只比较两种示例窗口，不私定默认',[
            {'interpretation':'按当前示例，以数据边界内最长对称窗口比较旧产品日均销售',**profile(a)},
            {'interpretation':'同一上市日期／老产品定义，比较上市前后各90日',**profile(b)}],signature(a)==signature(b))
        a=query(questions['Q40']['refs'][0]['sql'])
        b=query("WITH daily AS (SELECT DateKey,sum(SalesAmount) AS sales FROM retail.FactOnlineSales WHERE CurrencyKey=1 GROUP BY DateKey) SELECT sum(d.sales*e.EndOfDayRate),countIf(e.DateKey>toDate('1970-01-01')) FROM (SELECT *,toUInt8(1) AS k FROM daily ORDER BY DateKey) d ASOF LEFT JOIN (SELECT r.DateKey,r.EndOfDayRate,toUInt8(1) AS k FROM retail.FactExchangeRate r JOIN retail.DimCurrency c ON r.CurrencyKey=c.CurrencyKey WHERE c.CurrencyName='EUR' ORDER BY DateKey) e ON d.k=e.k AND d.DateKey>=e.DateKey")
        add('G05',['Q40'],'缺少当日收盘汇率的日期','约定6定义本币美元，但假设换汇的问题未给汇率缺失日处理；精确日匹配只是当前judge部分示例，不能私自当全期答案',[
            {'interpretation':'只按当日确有EUR汇率的日期匹配','sales_eur':a[0][0],'covered_days':31},
            {'interpretation':'缺报价日沿用之前最近一次EUR收盘价（仅敏感性试算，未批准）','sales_eur':b[0][0],'covered_days':b[0][1]}],a[0][0]==b[0][0])
        q=questions['Q84'];ref=q['refs'][0];payload=json.loads(str(sess.query(ref['sql'],'JSONCompact')))
        _,a,_=postprocess_reference(ref['postprocess'],payload['meta'],payload['data'],unit)
        cols={c['name']:i for i,c in enumerate(payload['meta'])};groups=defaultdict(list)
        for row in payload['data']:groups[unit.quantize_tie(row[cols['revenue']],'amount')].append(row)
        total=sum(v*len(rs) for v,rs in groups.items());cum=Decimal(0);buckets={name:[0,Decimal(0)] for name in 'ABC'}
        for revenue,members in sorted(groups.items(),reverse=True):
            cum+=revenue*len(members)
            bucket='A' if cum<=total*Decimal('.8') else 'B' if cum<=total*Decimal('.95') else 'C'
            buckets[bucket][0]+=len(members);buckets[bucket][1]+=revenue*len(members)
        b=[[name,count,float(revenue),float(revenue*100/total)] for name,(count,revenue) in buckets.items() if count]
        add('G07',['Q84'],'ABC跨阈值同额组归属','题面保留80/15/5参数，但L1未定义跨过阈值的整个同额产品组归前一类还是后一类；两算法均不拆同额组',[
            {'interpretation':'同额组开始前累计额决定类别（当前参考）','class_product_counts':{r[0]:r[1] for r in a}},
            {'interpretation':'加入同额组后累计额决定类别','class_product_counts':{r[0]:r[1] for r in b}}],a==b)
        for qid in ('Q100','Q118'):
            q=questions[qid];ref=q['refs'][0];payload=json.loads(str(sess.query(ref['sql'],'JSONCompact')));meta=payload['meta'];domain=payload['data'];pos={c['name']:i for i,c in enumerate(meta)}
            if qid=='Q100':
                metrics=('orders','avg_order_amount');kinds=('count','amount')
            else:metrics=('base_sales',);kinds=('amount',)
            quantized=[[unit.quantize_tie(row[pos[name]],kind) for name,kind in zip(metrics,kinds,strict=True)] for row in domain]
            linear=[exact_percentile([r[i] for r in quantized]) for i in range(len(metrics))]
            ordinal=[sorted([r[i] for r in quantized],reverse=True)[math.ceil(len(domain)*.1)-1] for i in range(len(metrics))]
            a=[i for i,r in enumerate(quantized) if all(v>=cut for v,cut in zip(r,linear,strict=True))]
            b=[i for i,r in enumerate(quantized) if all(v>=cut for v,cut in zip(r,ordinal,strict=True))]
            add('G08' if qid=='Q100' else 'G09',[qid],'前10%的阈值算法','题库已有精确线性插值裁决，但约定及L1未传达该算法；审计另一种按ceil(N/10)名次取阈值且含并列的解读，不修改现有参考',[
                {'interpretation':'(N-1)*0.9精确线性插值P90，含阈值并列','thresholds':list(map(str,linear)),'members':len(a),'membership_sha256':signature([[i] for i in a])},
                {'interpretation':'前ceil(N/10)的第N名值为阈值，含并列','thresholds':list(map(str,ordinal)),'members':len(b),'membership_sha256':signature([[i] for i in b])}],a==b)
        rows=query('SELECT StoreKey,sumIf(SalesAmount,toYear(DateKey)=2008) AS a,sumIf(SalesAmount,toYear(DateKey)=2009) AS b FROM retail.FactSales WHERE toYear(DateKey) IN (2008,2009) GROUP BY StoreKey HAVING a>0 AND b>0 AND b<a')
        percentage=sorted(rows,key=lambda r:(r[1]-r[2])/r[1],reverse=True)[:3];absolute=sorted(rows,key=lambda r:r[1]-r[2],reverse=True)[:3]
        add('G12',['Q117'],'降幅是相对比率还是绝对减少额','L1定义同比增长率，但题面只写降幅最大，没有把这个词唯一映射到比率或金额；两种排序都保持题目同店与年份',[
            {'interpretation':'按相对降幅选择3店（当前参考）','store_keys':[r[0] for r in percentage]},
            {'interpretation':'按销售减少金额选择3店','store_keys':[r[0] for r in absolute]}],{r[0] for r in percentage}=={r[0] for r in absolute})
        rows=query('SELECT p.BrandName,sum(f.SalesAmount-f.TotalCost) AS profit,sum(f.SalesAmount-f.TotalCost)/nullIf(sum(f.SalesAmount),0) AS margin FROM retail.FactOnlineSales f JOIN retail.DimProduct p ON f.ProductKey=p.ProductKey WHERE f.DateKey BETWEEN toDate(\'2009-10-01\') AND toDate(\'2009-12-31\') AND p.BrandName IS NOT NULL GROUP BY p.BrandName')
        a=[r[0] for r in sorted(rows,key=lambda r:r[1],reverse=True)];b=[r[0] for r in sorted(rows,key=lambda r:r[2],reverse=True)]
        add('G13',['Q92'],'盈利能力的排序指标','L1同时定义毛利额和毛利率，但未唯一解释盈利能力；这是开放judge问法，不私定只认一个',[
            {'interpretation':'按毛利额排序（当前示例）','brands':a},{'interpretation':'按毛利率排序','brands':b}],a==b,'开放问法保留；是否需要企业默认待用户审阅')
        rows=query('SELECT pc.ProductCategoryName,sumIf(f.SalesAmount,f.PromotionKey!=1) AS promo,sumIf(f.SalesAmount,f.PromotionKey=1) AS full,countIf(f.PromotionKey!=1) AS n_promo,countIf(f.PromotionKey=1) AS n_full FROM retail.FactOnlineSales f LEFT JOIN retail.DimProduct p ON f.ProductKey=p.ProductKey LEFT JOIN retail.DimProductSubcategory ps ON p.ProductSubcategoryKey=ps.ProductSubcategoryKey LEFT JOIN retail.DimProductCategory pc ON ps.ProductCategoryKey=pc.ProductCategoryKey GROUP BY pc.ProductCategoryName')
        a=[[r[0],r[1]-r[2]] for r in rows];b=[[r[0],r[1]/r[3]-r[2]/r[4] if r[3] and r[4] else None] for r in rows]
        add('G16',['Q95'],'促销增量的基准与因果含义','约定10规定促销筛选，却未定义增量反事实基准；两个描述性差值都不是因果识别，不能据此擅定增量口径',[
            {'interpretation':'促销收入合计减原价收入合计（仅敏感性示例）',**profile(a)},
            {'interpretation':'促销行均收入减原价行均收入（仅敏感性示例）',**profile(b)}],signature(a)==signature(b))
        rows=query('SELECT c.YearlyIncome,sum(f.SalesAmount) AS spending FROM retail.FactOnlineSales f JOIN retail.DimCustomer c ON f.CustomerKey=c.CustomerKey GROUP BY f.CustomerKey,c.YearlyIncome')
        rows=[r for r in rows if all(v is not None for v in r)];xs=[r[0] for r in rows];ys=[r[1] for r in rows]
        p=correlation(xs,ys);s=correlation(ranks(xs),ranks(ys))
        add('G17',['Q48','Q86','Q91'],'未点名的相关性方法','L1未指定未点名相关性默认Pearson还是Spearman；Q120已在题面点名Pearson，不属于此缺口。以下以Q91相同客户域实测',[
            {'interpretation':'Pearson线性相关','evidence_question':'Q91','value':p},
            {'interpretation':'Spearman秩相关','evidence_question':'Q91','value':s}],unit.quantize_tie(p,'ratio')==unit.quantize_tie(s,'ratio'),'开放judge允许声明方法；不把Q91的差异伪称为Q48/Q86已执行同一试算')
    finally:sess.close()
    result={'source_sha256':source_sha,'unit_policy_sha256':unit_sha,'rulings_added':False,'new_accepted_references_added':False,'entries':sorted(entries,key=lambda r:r['id']),
            'scope_note':'只列未传达或不明确的默认与真实不同问法；已定义的购买事件、空品类、营业状态、库存粒度、折扣率不作为可多解缺口；无法从全渠道数据还原订单者明确标不可比较'}
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
