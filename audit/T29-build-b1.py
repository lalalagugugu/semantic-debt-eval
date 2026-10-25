"""Materialize Codex's manual, pre-answer T29 B1 annotation (no model calls).

Run from the main T29 clone with its existing uv environment:
  uv run python "$SEMDEBT_DATA_DIR/t29-b1-eval/audit/T29-build-b1.py"
Only audit/T29-* is written; frozen questions/ and refs/ are never modified.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audit" / "T29-b1-results"

# Manually reviewed against the Chinese wording, source.yaml, and l1plus.yaml.
# These are per-question rationales, not an automatic ambiguity classifier.
NOTES = {
1: "产品目录的产品实体计数，不是事实表行数或在售产品数。A31。",
2: "明确线上销售额；约定7限定金额。",
3: "购买客户去重；A12明确含只有退货行的客户。",
4: "品牌限定明确；所有产品不缩到在售产品。A31。",
5: "产品目录按品类计产品实体，不是交易行或销量。",
6: "年份、渠道、指标都明确。",
7: "约定9/A16限定标价；D18允许的并列策略另记为展示政策。",
8: "销售人员由IsSalesPerson标识，不凭职位名称猜。",
9: "产品维度单位成本的算术平均；A36不剔异常。",
10: "营业状态On；A01含虚拟门店，不把门店读成实体店。",
11: "约定1默认线上；A20保留未知品类。",
12: "2008年逐月线上金额，时间粒度明确。",
13: "约定2全渠道；A16单价=销售额/销量。",
14: "D08终身累计消费；严格大于阈值；按客户计数。",
15: "A04/A05明确客户所在地；不是门店所在地。",
16: "两年各自汇总；差额/增长率展示按系统提示。",
17: "问的是两类日子的销售份额，分母为全部销售额（A21），不是另造日均份额指标。",
18: "促销类型分组；约定10排除无折扣键；A06全历史。",
19: "约定8/A12固定客单价和去重订单；不是客均消费。",
20: "A22/A24固定最近门店产品快照后跨店汇总比较。",
21: "A22当前库存固定按组合取最近快照。",
22: "按客户国家内累计消费排前五；D08和D18。",
23: "单年逐月累计，年初到当月；D13。",
24: "约定7固定数量退货率；不是金额率D17。",
25: "约定4/A09/A10固定交易日日均和北美季节字段。",
26: "明确首次购买所在季度；D01全局首购，不能改成季度新客90天。",
27: "约定9/A13固定产品标价利润率。",
28: "A02明确渠道对比用FactSales；A16固定成交均价。",
29: "约定4/A09比较日均；按非节假日作基数。",
30: "未说明展示窗口起点之前的数据是否参与首六天移动平均。",
31: "A14/A15明确销售收入科目Actual和Budget，不改用销售目标表。",
32: "三年均购买条件及D08终身累计明确。",
34: "A22/A23明确快照日先汇总库存金额后平均。",
35: "员工及直属经理；H06以18为根的断环规则明确。旧参考保留原始环边，单列可疑。",
36: "约定13/A27固定参照日、月数和分层集合。",
37: "百分位排名未规定用PERCENT_RANK还是累计分布CUME_DIST。",
38: "未指定总体还是按品类展示；D31固定准确度公式，不固定展示粒度。",
41: "约定3/A07固定上季度为2009Q4。",
43: "裸题地区可有国家或大洲读法；同义词及A39明确地区=国家，B2只认国家。",
47: "机器平均可指每次故障平均，也可指店内每台故障设备的累计停机时长平均。",
49: "组织层级由H05定义；收入Actual/Sale Revenue，逐级上卷而非只给叶子。",
50: "A29固定同店集合，整年比较；金额及百分比按提示展示。",
51: "A01/A31门店主数据总数含虚拟门店和已关店。",
52: "明确产品目录标价最大值；约定9/A16。",
53: "约定8/A12去重订单号，含只有退货行的订单。",
54: "线上退货金额求和，不是退货率或净销售。",
55: "客户维度Gender=F计数。",
56: "A36全部客户年收入的算术平均，不剔离群值。",
57: "产品目录品牌去重计数，不是制造商。",
58: "一笔线上销售未明说订单行还是整个订单。约定8仅定义订单，不把销售记录自动等同订单。",
59: "日历维度全部节假日，A06明确主数据不截到事实区间。",
60: "部门名Production筛员工；空集也可回答，不凭职位猜生产人员。",
61: "子类层、2009、线上金额和严格阈值明确。",
62: "品牌层、2008、线上及销量>=500明确。",
63: "职业层线上客单价，约定8固定订单分母。",
64: "约定7/A11固定毛利金额与毛利率；逐月范围明确。",
65: "可以逐店检查门槛列经理，也可按每位经理所管门店合计后检查门槛。",
66: "各季度累计可指各季合计，或各季末年初至今累计；未说逐季累计。",
67: "题面明确成交均价、销量门槛、线上；A36颜色不合并大小写。",
68: "明确节假日分组的订单数和收入，不是日均。",
69: "A17固定折前金额加权折扣率，不能另选促销主表折扣率平均。",
70: "销售与面积各自汇总；A36每家门店一次的算术平均，不能事实连接后加权。",
71: "品类内最高子类；D18并列政策，不等于另一个业务理解。",
72: "季度累计可跨2007—2009连续累计，也可每年重置年初至今。",
73: "差额未明确方向，可能指库存减安全库存、安全库存减库存或绝对差。",
74: "门店内产品前3，A21完整门店销售分母。",
75: "两年消费比较、严格超过50%；A08零基数为NULL。",
76: "回头客的两单可以在全目录内认定，也可以在当前品类内认定；D05规定时间窗口但未固定品类作用域。",
77: "A08固定前一个月，一月要比较2008年12月，不接受窗口内缺基期。",
78: "明确折扣金额排位和完整折扣分母；约定10排无折扣。",
79: "约定12/A26正式预算目标、整年比值；并列按D18。",
80: "客户首末购相隔自然天，按国家平均；A12/D01/D02。",
81: "全局首购年队列、D08客户终身消费平均和人数明确。",
82: "人数明确直属；团队年限可能只指直属成员，也可指含经理的直属团队，或全部下属；均遵H06断环。旧参考未断环。",
83: "题面逐层限定2008回购者中2009再回购，不是每年独立留存率。D04。",
84: "题面ABC跨界组可前后累计；D19明确加入后累计，因此前累计参考只记可疑，不进入B2。",
85: "A26整年正式目标比值；两端各5，NULL不具备最高最低比率。",
87: "D29明确默认线上、交易日日均；不能用无声明的全渠道或90日历日。",
88: "2009四季度都有购买，全年消费排前20；A12固定购买事件。",
89: "A27客户分层及A06全历史消费，平均以客户为单位，不是订单平均。",
90: "按年毛利率及相邻年份百分点差，首年无前期值。",
92: "盈利能力未明确毛利额还是毛利率；A13只规定利润率的含义，并未将盈利能力映射为利润率。",
94: "即字后已定义走弱为第四季低于第三季，不再引入其他趋势定义。",
96: "之后任一年回购过，明确D04任意后续期回购，不是连续或逐期留存。",
98: "未指定年份，A06要求全部数据按年；仅2009的旧参考违反A06，单列可疑。最大季度份额衡量单季依赖。",
99: "约定4/A09逐类交易日日均；高多少同时展示金额和百分比。",
100: "前10%可用P90值阈值，或先按对象排名取ceil(N*10%)；D18未规定百分位阈值算法。",
101: "约定3/7与A07确定2009Q4线上SalesAmount。",
102: "约定7净销售额扣退货；A07今年2009；A20保留未知组。",
103: "明确订单、年度、严格金额阈值；约定8先按订单汇总。",
104: "两年收入增且毛利减；约定7及D14固定两项带符号变化。",
105: "卖了多少未明确金额或件数；同义词只将卖了多少件映射销量，不规定本题省略单位。",
106: "城市内全部门店全渠道年度同比；A01/A03及地点别名。",
107: "明确单店净额占全城门店净额；A21总体不能改成线上或单店。",
108: "约定1/5/8固定线上、客户国家、订单号。",
109: "A09交易日日均及A08去年同期；旧参考补日历的写法不扩展为新的B2允许口径。",
110: "A02渠道占比同表FactSales，按百分点相减。",
111: "截至9月底的年内实际额分别除同期与全年预算；A26。",
112: "120%挑战线、店级判定后经理汇总、正缺口已明说。",
113: "全年正式目标/12、连续至少3个月，列最大连续段而非重叠子区间。",
114: "全局首购和每月末90天窗口均明确；A28/D01。",
115: "期初已购买集合、两个截止日分层及迁移方向明确；A27。",
116: "全局首购次日起7天、排未完成观察、月队列明确；D06b。",
117: "同店降幅率选店，再按品类销售减少额选最大拖累；A29/D14。",
118: "产品前10%可取P90值阈值或ceil(N*10%)排名；不是营收累计前10%。A21固定2009完整分母。",
119: "店内最畅销可指销量或销售额；全公司排名明确按销售额，竞赛与稠密排名未被D18唯一限定。",
120: "Pearson、当年消费、全体和职业组、样本人数已明确；A36不擅自剔离群客户。",
121: "变异系数的总体或样本标准差均可；L1plus未规定标准差分母。D12规定月均。",
122: "共同订单数明确，提升度的概率总体可为全部线上订单或至少含一款Contoso的订单；L1plus未规定lift总体。",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    frozen = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "eval-v1.2^{commit}"], text=True).strip()
    questions = []
    for name in ("cube_100.yaml", "new.yaml"):
        questions += json.loads((ROOT / "questions" / name).read_text())["questions"]
    questions = [q for q in questions if q["scoring"] == "deterministic"]
    assert len(questions) == 109
    assert {int(q["id"][1:]) for q in questions} == set(NOTES)
    records = []
    for q in questions:
        variants = []
        for i, ref in enumerate(q["refs"], 1):
            variants.append({
                "id": f"{q['id']}-existing-{i}", "interpretation": ref["interpretation"],
                "b2_eligible": True, "existing_reference": ref["result_path"],
                "sql": ref["sql"], "sql_sha256": digest(ref["sql"].encode()),
                "result": {"path": ref["result_path"], "sha256": digest((ROOT / ref["result_path"]).read_bytes())},
                "note": "沿用冻结参考结果；部分SQL返回选择域，最终答案生成过程见原题库scripts及refs/MANIFEST.json，不把域当成最终答案。",
            })
        records.append({"qid": q["id"], "text_zh": q["text_zh"], "split": q["split"],
                        "manual_rationale": NOTES[int(q["id"][1:])],
                        "question_only_multiple": False, "multiple_b2_eligible": False,
                        "interpretations": variants, "suspicious_references": []})
    by_id = {r["qid"]: r for r in records}

    def add(qid, name, sql, *, eligible=True, reason=None):
        r = by_id[qid]
        variant = {"id": f"{qid}-b1-{1+sum(v.get('existing_reference') is None for v in r['interpretations'])}",
                   "interpretation": name, "b2_eligible": eligible, "existing_reference": None,
                   "sql": sql, "sql_sha256": digest(sql.encode()), "exclusion_reason": reason}
        r["interpretations"].append(variant)

    for qid, index, rule in [("Q43", 0, "source.synonyms地区=RegionCountryName；L1plus A39"),
                              ("Q84", 0, "L1plus D19加入后累计归类"),
                              ("Q98", 0, "L1plus A06无时间条件须覆盖全部事实年份")]:
        v = by_id[qid]["interpretations"][index]
        v.update(b2_eligible=False, exclusion_reason=rule)
        by_id[qid]["suspicious_references"].append({"reference": v["existing_reference"], "reason": rule})

    # Each alternative was identified before any answer was read. Only SQL and
    # frozen reference results are consulted here; never runs/ or runs-raw/.
    q = by_id["Q30"]["interpretations"][0]["sql"]
    add("Q30", "12月展示，但首6天移动平均包含11月最后6天，始终7个自然日", "WITH daily AS (SELECT DateKey,sum(SalesAmount) AS daily_sales FROM retail.FactOnlineSales WHERE DateKey BETWEEN toDate('2009-11-25') AND toDate('2009-12-31') GROUP BY DateKey), rolling AS (SELECT DateKey,daily_sales,avg(daily_sales) OVER (ORDER BY DateKey ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7d FROM daily) SELECT * FROM rolling WHERE DateKey>=toDate('2009-12-01') ORDER BY DateKey")
    add("Q37", "百分位采用累计分布：销售额不超过本店的门店占比", "SELECT s.StoreName,sum(f.SalesAmount) AS total_sales,cume_dist() OVER (ORDER BY sum(f.SalesAmount))*100 AS percentile FROM retail.FactSales f JOIN retail.DimStore s ON f.StoreKey=s.StoreKey GROUP BY s.StoreKey,s.StoreName ORDER BY total_sales DESC")
    add("Q47", "先按发生故障门店×设备汇总全历史停机，再平均设备累计停机（有故障设备集合）", "WITH devices AS (SELECT StoreKey,MachineKey,sum(DownTime) AS down FROM retail.FactITSLA GROUP BY StoreKey,MachineKey) SELECT s.StoreName,avg(d.down) AS avg_downtime_minutes FROM devices d JOIN retail.DimStore s ON d.StoreKey=s.StoreKey GROUP BY s.StoreKey,s.StoreName ORDER BY avg_downtime_minutes DESC")
    add("Q58", "一笔销售指整个线上订单，先合并该订单全部行", "SELECT max(amount) AS max_order_sales_amount FROM (SELECT SalesOrderNumber,sum(SalesAmount) AS amount FROM retail.FactOnlineSales GROUP BY SalesOrderNumber)")
    add("Q65", "按每位经理管理的门店合计判断500万美元，列经理及其门店合计", "WITH managers AS (SELECT s.EmployeeKey,sum(f.SalesAmount) AS total_sales FROM retail.FactSales f JOIN retail.DimStore s ON f.StoreKey=s.StoreKey GROUP BY s.EmployeeKey HAVING total_sales>5000000) SELECT m.EmployeeKey,if(e.EmployeeKey=0,NULL,concat(e.FirstName,' ',e.LastName)) AS manager_name,m.total_sales FROM managers m LEFT JOIN retail.DimEmployee e ON m.EmployeeKey=e.EmployeeKey ORDER BY total_sales DESC")
    add("Q66", "各季末从2009年初累计的折扣金额", "SELECT toQuarter(DateKey) AS quarter,sum(sum(DiscountAmount)) OVER (ORDER BY toQuarter(DateKey)) AS total_discount FROM retail.FactOnlineSales WHERE toYear(DateKey)=2009 AND PromotionKey<>1 GROUP BY quarter ORDER BY quarter")
    add("Q72", "2007—2009分别在每年年初重置，逐季展示本年累计", "SELECT toYear(DateKey) AS year,toQuarter(DateKey) AS quarter,sum(SalesAmount) AS quarterly_sales,sum(sum(SalesAmount)) OVER (PARTITION BY toYear(DateKey) ORDER BY toQuarter(DateKey)) AS cumulative_sales FROM retail.FactOnlineSales WHERE toYear(DateKey) BETWEEN 2007 AND 2009 GROUP BY year,quarter ORDER BY year,quarter")
    q73 = by_id["Q73"]["interpretations"][0]["sql"]
    add("Q73", "差额指安全库存减当前库存（缺口），取缺口最大10产品", q73.replace("sum(i.OnHandQuantity) - sum(i.SafetyStockQuantity) AS gap", "sum(i.SafetyStockQuantity) - sum(i.OnHandQuantity) AS gap").replace("sum(i.OnHandQuantity) - sum(i.SafetyStockQuantity) as gap", "sum(i.SafetyStockQuantity) - sum(i.OnHandQuantity) as gap"))
    add("Q73", "差额指当前库存与安全库存的绝对差，取绝对差最大10产品", q73.replace("sum(i.OnHandQuantity) - sum(i.SafetyStockQuantity) as gap", "abs(sum(i.OnHandQuantity) - sum(i.SafetyStockQuantity)) AS gap").replace("sum(i.OnHandQuantity) - sum(i.SafetyStockQuantity) AS gap", "abs(sum(i.OnHandQuantity) - sum(i.SafetyStockQuantity)) AS gap"))

    # H06's root is binding even for the existing reference's intended meaning.
    old82 = by_id["Q82"]["interpretations"][0]
    old82.update(b2_eligible=False, exclusion_reason="H06以员工18为根，不把18算作1的下属")
    by_id["Q82"]["suspicious_references"].append({"reference": old82["existing_reference"], "reason": old82["exclusion_reason"]})
    add("Q82", "直属下属人数；团队平均仅含直属下属，按H06去掉18→1环边", old82["sql"].replace("WHERE ParentEmployeeKey IS NOT NULL AND HireDate IS NOT NULL", "WHERE EmployeeKey!=18 AND ParentEmployeeKey IS NOT NULL AND HireDate IS NOT NULL"))
    add("Q82", "直属下属人数；直属团队平均含经理本人，按H06断环", "WITH edges AS (SELECT EmployeeKey,ParentEmployeeKey FROM retail.DimEmployee WHERE EmployeeKey!=18), managers AS (SELECT ParentEmployeeKey AS manager,count() AS direct_reports FROM edges GROUP BY manager), members AS (SELECT ParentEmployeeKey AS manager,EmployeeKey AS member FROM edges UNION ALL SELECT manager,manager AS member FROM managers) SELECT m.EmployeeKey,concat(m.FirstName,' ',m.LastName) AS manager_name,r.direct_reports,avg(dateDiff('day',toDate(e.HireDate),toDate('2009-12-31'))/365.25) AS avg_team_tenure_years FROM members x JOIN retail.DimEmployee e ON x.member=e.EmployeeKey JOIN retail.DimEmployee m ON x.manager=m.EmployeeKey JOIN managers r ON r.manager=x.manager GROUP BY m.EmployeeKey,manager_name,r.direct_reports ORDER BY r.direct_reports DESC,manager_name")
    add("Q82", "直属下属人数；团队平均含全部层级下属但不含经理，按H06断环", "WITH RECURSIVE edges AS (SELECT EmployeeKey,ParentEmployeeKey FROM retail.DimEmployee WHERE EmployeeKey!=18), descendants AS (SELECT ParentEmployeeKey AS manager,EmployeeKey AS member FROM edges UNION ALL SELECT d.manager,e.EmployeeKey FROM descendants d JOIN edges e ON e.ParentEmployeeKey=d.member), counts AS (SELECT ParentEmployeeKey AS manager,count() AS direct_reports FROM edges GROUP BY manager) SELECT m.EmployeeKey,concat(m.FirstName,' ',m.LastName) AS manager_name,c.direct_reports,avg(dateDiff('day',toDate(e.HireDate),toDate('2009-12-31'))/365.25) AS avg_team_tenure_years FROM descendants d JOIN retail.DimEmployee e ON d.member=e.EmployeeKey JOIN retail.DimEmployee m ON d.manager=m.EmployeeKey JOIN counts c ON c.manager=d.manager GROUP BY m.EmployeeKey,manager_name,c.direct_reports ORDER BY c.direct_reports DESC,manager_name")
    old35 = by_id["Q35"]["interpretations"][0]
    old35.update(b2_eligible=False, exclusion_reason="H06根18没有上级；原SQL直接连接原始18→1环边")
    by_id["Q35"]["suspicious_references"].append({"reference": old35["existing_reference"], "reason": old35["exclusion_reason"]})
    add("Q35", "按H06断环后的员工直属上级，根18上级为NULL", "SELECT e.FirstName,e.LastName,e.Title,if(e.EmployeeKey=18,NULL,m.FirstName) AS manager_first,if(e.EmployeeKey=18,NULL,m.LastName) AS manager_last FROM retail.DimEmployee e LEFT JOIN retail.DimEmployee m ON e.ParentEmployeeKey=m.EmployeeKey")
    add("Q92", "盈利能力以毛利金额衡量，按上季度毛利金额降序", by_id["Q92"]["interpretations"][0]["sql"].replace("ORDER BY gross_margin_pct DESC", "ORDER BY gross_margin_dollars DESC"))
    customer_domain = "SELECT CustomerKey,countDistinct(SalesOrderNumber) AS orders,sum(SalesAmount)/countDistinct(SalesOrderNumber) AS avg_order_amount,sum(SalesAmount) AS lifetime_value FROM retail.FactOnlineSales GROUP BY CustomerKey"
    add("Q100", "两指标分别取人数前ceil(N*10%)，阈值同值全保留，再取交集", f"WITH domain AS ({customer_domain}), ranks AS (SELECT *,rank() OVER (ORDER BY orders DESC) AS order_rank,rank() OVER (ORDER BY avg_order_amount DESC) AS aov_rank,count() OVER () AS n FROM domain) SELECT concat(c.FirstName,' ',c.LastName) AS customer_name,r.orders,r.avg_order_amount,r.lifetime_value,r.CustomerKey FROM ranks r JOIN retail.DimCustomer c ON r.CustomerKey=c.CustomerKey WHERE order_rank<=ceil(n*0.1) AND aov_rank<=ceil(n*0.1)")
    add("Q105", "卖了多少指销售件数；全渠道、点名门店和年份不变", "SELECT sum(f.SalesQuantity) AS sales_quantity FROM retail.FactSales f JOIN retail.DimStore s ON f.StoreKey=s.StoreKey WHERE s.StoreName='Contoso Seattle No.2 Store' AND toYear(f.DateKey)=2009")
    product_domain = "SELECT ProductKey,sumIf(SalesAmount,toYear(DateKey)=2008) AS base_sales,sumIf(SalesAmount,toYear(DateKey)=2009) AS future_sales,countIf(toYear(DateKey)=2008) AS base_rows FROM retail.FactOnlineSales WHERE toYear(DateKey) IN (2008,2009) GROUP BY ProductKey HAVING base_rows>0"
    add("Q118", "按2008年产品数取前ceil(N*10%)，边界并列全部保留", f"WITH base AS ({product_domain}), ranked AS (SELECT *,rank() OVER (ORDER BY base_sales DESC) AS r,count() OVER () AS n FROM base), total AS (SELECT sum(SalesAmount) AS denominator FROM retail.FactOnlineSales WHERE toYear(DateKey)=2009) SELECT sumIf(future_sales,r<=ceil(n*0.1)) AS sales_amount,sales_amount*100.0/any(denominator) AS share_pct,any(denominator) AS total_sales FROM ranked CROSS JOIN total")
    # Actual final answers, not the original selection-domain SQL with a dummy rank.
    for metric in ("SalesAmount", "SalesQuantity"):
        for ranking in ("rank", "dense_rank"):
            if metric == "SalesAmount" and ranking == "rank":
                continue  # the existing materialized reference covers this interpretation
            add("Q119", f"店内按{'销售额' if metric=='SalesAmount' else '销量'}选最畅销产品；公司销售额采用{ranking}排名，并列最高都列出", f"WITH stores AS (SELECT StoreKey,ProductKey,sum(SalesAmount) AS amount,sum({metric}) AS criterion FROM retail.FactSales WHERE toYear(DateKey)=2009 GROUP BY StoreKey,ProductKey), global AS (SELECT ProductKey,sum(amount) AS company_sales,{ranking}() OVER (ORDER BY sum(amount) DESC) AS global_rank FROM stores GROUP BY ProductKey), selected AS (SELECT *,rank() OVER (PARTITION BY StoreKey ORDER BY criterion DESC) AS r FROM stores) SELECT x.StoreKey,s.StoreName,x.ProductKey,if(p.ProductKey=0,NULL,p.ProductName) AS ProductName,x.amount AS product_sales,g.global_rank FROM selected x JOIN global g ON x.ProductKey=g.ProductKey LEFT JOIN retail.DimStore s ON x.StoreKey=s.StoreKey LEFT JOIN retail.DimProduct p ON x.ProductKey=p.ProductKey WHERE x.r=1 ORDER BY x.StoreKey,x.ProductKey")
    add("Q122", "提升度概率总体为当年含至少一款Contoso的线上订单；共同订单数仍按产品对去重订单", by_id["Q122"]["interpretations"][0]["sql"].replace("SELECT count() AS all_orders FROM baskets", "SELECT countIf(length(products)>0) AS all_orders FROM baskets"))

    for qid, interpretation in {
        "Q30": "只用12月数据的向后窗口；月初不足7天时按已有天数平均",
        "Q37": "百分位采用PERCENT_RANK：(升序rank-1)/(门店数-1)",
        "Q47": "每个门店全部故障事件的DownTime算术平均",
        "Q58": "一笔销售指一条线上订单行，取行金额最大值",
        "Q65": "逐店销售额超过500万美元，逐店列出其经理",
        "Q66": "每个季度各自合计折扣金额，不跨季累计",
        "Q72": "从2007年起至当前季度跨年连续累计",
        "Q73": "当前在手库存减安全库存，取正向差额最大10款",
        "Q92": "盈利能力以毛利率衡量，按上季度毛利率降序",
        "Q100": "订单数和客单价各取精确线性插值P90阈值，保留阈值并列后取交集",
        "Q105": "卖了多少指销售金额（美元）",
        "Q118": "按2008年销售额的精确线性插值P90阈值选产品，保留阈值并列",
        "Q119": "店内按销售额选最畅销产品；全公司销售额按竞赛排名，并列最高都列出",
        "Q122": "提升度的概率总体为2009年全部线上订单",
    }.items():
        by_id[qid]["interpretations"][0]["interpretation"] = interpretation

    # Some frozen reference SQL returns a domain which the original build
    # scripts transform. Supply standalone final-answer SQL as well as the
    # immutable CSV link; do not pass a domain off as a final answer.
    for i, before in enumerate((True, False)):
        cumulative = "cum-group_amount" if before else "cum"
        by_id["Q84"]["interpretations"][i]["answer_sql"] = f"WITH amounts AS (SELECT ProductKey,sum(SalesAmount) AS revenue FROM retail.FactOnlineSales WHERE toYear(DateKey)=2009 GROUP BY ProductKey), shares AS (SELECT *,sum(revenue) OVER (ORDER BY revenue DESC RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum,sum(revenue) OVER (PARTITION BY revenue) AS group_amount,sum(revenue) OVER () AS total FROM amounts), classified AS (SELECT *,multiIf(({cumulative})/total<=0.8,'A',({cumulative})/total<=0.95,'B','C') AS abc_class FROM shares) SELECT abc_class,count() AS product_count,sum(c.revenue) AS revenue,sum(c.revenue)*100.0/any(total) AS pct_of_revenue,any(total) AS total_revenue_amount FROM classified c GROUP BY abc_class ORDER BY abc_class"
    for i in (0, 1):
        q98 = by_id["Q98"]["interpretations"][i]["sql"]
        # Original quarter share query has one row per category × quarter.
        domain = q98[:q98.rfind(" ORDER BY")] if " ORDER BY" in q98 else q98
        if i == 0:
            by_id["Q98"]["interpretations"][i]["answer_sql"] = f"WITH domain AS ({domain}), marked AS (SELECT *,rank() OVER (PARTITION BY ProductCategoryName ORDER BY peak_quarter_share_pct DESC) AS r FROM domain) SELECT ProductCategoryName,peak_quarter_share_pct,concat('Q',toString(peak_quarter)) AS peak_quarter,annual_sales_amount,rank() OVER (ORDER BY peak_quarter_share_pct DESC) AS rank FROM marked WHERE r=1 ORDER BY peak_quarter_share_pct DESC"
        else:
            by_id["Q98"]["interpretations"][i]["answer_sql"] = f"WITH domain AS ({domain}), marked AS (SELECT *,rank() OVER (PARTITION BY ProductCategoryName,year ORDER BY peak_quarter_share_pct DESC) AS r FROM domain) SELECT ProductCategoryName,year,peak_quarter_share_pct,concat('Q',toString(peak_quarter)) AS peak_quarter,annual_sales_amount,rank() OVER (PARTITION BY year ORDER BY peak_quarter_share_pct DESC) AS rank FROM marked WHERE r=1 ORDER BY year,peak_quarter_share_pct DESC"
    by_id["Q100"]["interpretations"][0]["answer_sql"] = f"WITH domain AS ({customer_domain}), thresholds AS (SELECT quantileExactInclusive(0.9)(orders) AS o,quantileExactInclusive(0.9)(avg_order_amount) AS a FROM domain) SELECT concat(c.FirstName,' ',c.LastName) AS customer_name,d.orders,d.avg_order_amount,d.lifetime_value,d.CustomerKey FROM domain d CROSS JOIN thresholds t JOIN retail.DimCustomer c ON d.CustomerKey=c.CustomerKey WHERE d.orders>=t.o AND d.avg_order_amount>=t.a"
    by_id["Q118"]["interpretations"][0]["answer_sql"] = f"WITH base AS ({product_domain}), threshold AS (SELECT quantileExactInclusive(0.9)(base_sales) AS p90 FROM base), total AS (SELECT sum(SalesAmount) AS denominator FROM retail.FactOnlineSales WHERE toYear(DateKey)=2009) SELECT sumIf(future_sales,base_sales>=p90) AS sales_amount,sales_amount*100.0/any(denominator) AS share_pct,any(denominator) AS total_sales FROM base CROSS JOIN threshold CROSS JOIN total"
    by_id["Q119"]["interpretations"][0]["answer_sql"] = by_id["Q119"]["interpretations"][1]["sql"].replace("dense_rank()", "rank()")
    old109 = by_id["Q109"]["interpretations"][0]
    old109.update(b2_eligible=False, exclusion_reason="A09默认交易日日均，题面未明确要求补零日历日；原SQL显式补完整日历")
    by_id["Q109"]["suspicious_references"].append({"reference": old109["existing_reference"], "reason": old109["exclusion_reason"], "note": "这是口径/实现疑点，不声称当前数据上数值必然不同，交题库负责方核对。"})
    add("Q109", "按A09在各年各季有交易的日子上平均每日销售，再与去年同期比较", "WITH daily AS (SELECT DateKey,toQuarter(DateKey) AS quarter,toYear(DateKey) AS y,sum(SalesAmount) AS day_sales FROM retail.FactOnlineSales WHERE toYear(DateKey) IN (2008,2009) GROUP BY DateKey,quarter,y) SELECT quarter,(avgIf(day_sales,y=2009)/nullIf(avgIf(day_sales,y=2008),0)-1)*100 AS daily_sales_growth_pct,avgIf(day_sales,y=2009)-avgIf(day_sales,y=2008) AS daily_sales_change_amount FROM daily GROUP BY quarter ORDER BY quarter")

    # All sensible, question-only alternatives above remain marked even when
    # an explicit L1plus clause rules them out. Correcting a tree edge is not
    # itself a second interpretation of an unambiguous question.
    ambiguous = {30,37,38,43,47,58,65,66,72,73,76,82,84,92,98,100,105,118,119,121,122}
    for r in records:
        r["question_only_multiple"] = int(r["qid"][1:]) in ambiguous
        r["multiple_b2_eligible"] = sum(v["b2_eligible"] for v in r["interpretations"]) > 1
        if not r["question_only_multiple"]:
            assert sum(v["b2_eligible"] for v in r["interpretations"]) == 1

    from chdb import session
    OUT.mkdir(exist_ok=True)
    db = session.Session(str(Path(os.environ["SEMDEBT_DATA_DIR"]) / "chdb-eval"))
    try:
        db.query("SET max_threads=2, max_execution_time=120, max_memory_usage=8000000000")
        for r in records:
            for v in r["interpretations"]:
                if v["existing_reference"] is not None and "answer_sql" not in v:
                    continue
                # No silent retries: a failure stops this build and is visible
                # in stderr. Fixing reference SQL requires an explicit new run.
                print("materializing", v["id"], flush=True)
                payload = json.loads(str(db.query(v.get("answer_sql", v["sql"]), "JSONCompact")))
                artifact = {"columns": payload["meta"], "rows": payload["data"]}
                data = (json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
                target = OUT / f"{v['id']}.json"
                target.write_bytes(data)
                key = "answer_result" if v["existing_reference"] is not None else "result"
                v[key] = {"path": str(target.relative_to(ROOT)), "sha256": digest(data), "rows": len(payload["data"])}
                if "answer_sql" in v:
                    v["answer_sql_sha256"] = digest(v["answer_sql"].encode())
    finally:
        db.close()

    summary = {"questions": len(records), "existing_reference_count": sum(len(q["refs"]) for q in questions),
               "existing_multi_reference_qids": [q["id"] for q in questions if len(q["refs"])>1],
               "question_only_multiple": sum(r["question_only_multiple"] for r in records),
               "multiple_b2_eligible": sum(r["multiple_b2_eligible"] for r in records),
               "excluded_existing_reference_count": sum(len(r["suspicious_references"]) for r in records),
               "new_result_count": sum(v["existing_reference"] is None for r in records for v in r["interpretations"])}
    document = {"schema_version": 1, "annotator": "Codex manual review", "before_model_answers": True,
                "eval_tag": "eval-v1.2", "eval_commit": frozen, "semantic_tag": "semantic-v1.6-l1plus",
                "semantic_commit": subprocess.check_output(["git", "rev-parse", "semantic-v1.6-l1plus^{commit}"], text=True).strip(),
                "decision": "用户2026-10-25：B2只认可符合L1plus明确约定的理解；违反者单列，不改主评分；可疑既有参考交题库负责方核对。",
                "scope": "逐题审阅109道deterministic题。企业默认、指标定义、相对时间及显式约束先适用；不把改渠道、换公式、删未知行等违反约定算成可认可歧义。D18已允许的边界并列策略是通用输出政策，不穷举为业务理解。",
                "reference_coverage": "existing_reference非空表示该解读已有冻结参考；其SQL可能需原题库脚本中的物化转换。新增结果JSON直接保存最终列和行。已有参考不足时不修改题库冻结目录，只新增audit结果。",
                "summary": summary, "records": records}
    (ROOT / "audit" / "T29-b1.json").write_text(json.dumps(document, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
