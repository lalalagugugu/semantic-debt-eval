# T04 逐题批阅表

本页供你直接批阅100道题；每题的英文原句、中文草稿、证据和建议放在同一张小表里。按10题分组。

- **中文通过**：只确认译文忠实、自然，不等于批准新增的参考口径。
- **接受建议**：批准本题“建议”列的全部处理；我随后据此更新裁决与参考。Q40明确只批准调查方向，最终公式和缺失日期规则仍须另审。
- 未勾表示待审，不视为否决。不同意或想部分接受时，在“批注”处写明。
- 使用标准 Markdown 任务框。若当前预览不支持点击，可在编辑器把 `[ ]` 改为 `[x]`；请勿勾选本次尚未审阅的项目。

本次有 **22项待裁决建议**（此前未审计题20项，Q74/Q94重审2项）。其余既有裁决在题目旁注明，无须重复批准。当前所有新建议均未获批，SQL和参考结果保持T03版本。英文锚点保持原样。

证据／建议列的“—”表示本次未发现新疑点、无新增建议，不代表已经证明参考完全正确。

## Q01–Q10

**Q01 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many products are in the catalog? | 产品目录中共有多少种产品？ | — | — |

- [ ] Q01 中文通过

批注：

**Q02 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the total sales amount from online sales? | 线上销售额合计是多少？ | — | — |

- [ ] Q02 中文通过

批注：

**Q03 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many unique customers have made online purchases? | 有多少位客户在线上购买过商品？ | — | — |

- [ ] Q03 中文通过

批注：

**Q04 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| List all products from the brand Contoso | 列出 Contoso 品牌的所有产品。 | — | — |

- [ ] Q04 中文通过

批注：

**Q05 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many products are there in each product category? | 各产品品类分别有多少种产品？ | — | — |

- [ ] Q05 中文通过

批注：

**Q06 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What were the total online sales in 2009? | 2009 年的线上销售额是多少？ | — | — |

- [ ] Q06 中文通过

批注：

**Q07 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What are the top 10 most expensive products by unit price? | 按产品单价，最贵的前 10 款产品是哪些？ | — | — |

- [ ] Q07 中文通过

批注：

**Q08 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| List all employees who are sales people | 列出所有销售人员。 | — | — |

- [ ] Q08 中文通过

批注：

**Q09 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the average unit cost across all products? | 所有产品的平均单位成本是多少？ | — | — |

- [ ] Q09 中文通过

批注：

**Q10 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many stores are currently open? | 目前有多少家门店在营业？ | 实测三判据为294、0、294；未关门店CloseDate使用2090-12-31，非SQL NULL。 | 已裁决：状态为 'On'；关店日期为空；状态为 'On' 或关店日期为空（原参考） |

- [ ] Q10 中文通过

批注：

## Q11–Q20

**Q11 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Show total sales amount by product category | 按产品品类汇总销售额。 | — | — |

- [ ] Q11 中文通过

批注：

**Q12 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What were the monthly online sales for 2008? | 2008 年各月的线上销售额分别是多少？ | — | — |

- [ ] Q12 中文通过

批注：

**Q13 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each store, show total sales, average order value, and number of transactions | 按门店列出销售额、平均订单金额和交易笔数。 | 实测306个StoreName全部唯一；全渠道事实表没有订单号，平均值按销售记录解释。 | 已裁决：全渠道销售按门店：销售额合计、每条记录的平均金额、记录数（须声明「无订单号，按记录计算」）。不接受：只用线上销售（违反约定第 2 条：以门店为对象的问题用全渠道销售） |

- [ ] Q13 中文通过

批注：

**Q14 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which customers have spent more than $10,000 in total? | 哪些客户的累计消费超过 1 万美元？ | 结果被截成 100 行且无排序，比的是任意一段；候选里出现的「Not Provided」客户是公司客户，参考按 CustomerKey 分组时同样包含。 | 已裁决：比对完整结果集（按 CustomerKey 匹配）。 |

- [ ] Q14 中文通过

批注：

**Q15 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What are the total online sales by country? | 各国家的线上销售额是多少？ | — | — |

- [ ] Q15 中文通过

批注：

**Q16 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Compare total online sales between 2008 and 2009 | 比较 2008 年和 2009 年的线上销售总额。 | — | — |

- [ ] Q16 中文通过

批注：

**Q17 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What percentage of sales occur on weekends vs weekdays? | 周末和工作日的销售分别占多少比例？ | 【与约定可能冲突】问句问销售占比，参考用周末/工作日总额占比；约定4要求比较日类型时先算日均。 | 保留“销售占比”的原义，按周末/工作日销售总额÷全部销售额计算；约定4的日均比较不替代本题的构成占比。中文不补“日均”。 |

- [ ] Q17 中文通过
- [ ] Q17 接受建议

批注：

**Q18 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the total discount amount given by each promotion type? | 各促销类型累计提供了多少折扣金额？ | — | — |

- [ ] Q18 中文通过

批注：

**Q19 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the average order value by customer gender? | 不同性别客户的客单价分别是多少？ | 参考按销售行求平均（约 215 美元），但「平均订单金额」应为总额 ÷ 订单数（约 1,600 美元），相差约 7 倍。 | 已裁决：线上销售按性别分组，sum(SalesAmount) / countDistinct(SalesOrderNumber)。 |

- [ ] Q19 中文通过

批注：

**Q20 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which products currently have inventory below their safety stock level? | 哪些产品目前的库存低于安全库存水平？ | 已有门店×产品/产品汇总两种输出层级；不是地区粒度歧义。 | 已裁决：每个门店 × 产品取最近一次快照，列出在手量低于安全库存的门店 × 产品；每个门店 × 产品取最近一次快照后按产品汇总，列出汇总在手量低于汇总安全库存的产品。不接受：全表最后一天的快照（违反约定第 11 条；原参考只用于英文锚点） |

- [ ] Q20 中文通过

批注：

## Q21–Q30

**Q21 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the current inventory level for each product in each store? | 各门店每种产品目前的库存是多少？ | — | — |

- [ ] Q21 中文通过

批注：

**Q22 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Rank the top 5 customers by total spend in each country | 按各国家客户的累计消费额，列出排名前 5 的客户。 | — | — |

- [ ] Q22 中文通过

批注：

**Q23 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Show cumulative monthly sales for 2009 | 展示 2009 年逐月累计销售额。 | — | — |

- [ ] Q23 中文通过

批注：

**Q24 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the return rate by product category? | 各产品品类的退货率是多少？ | — | — |

- [ ] Q24 中文通过

批注：

**Q25 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which season has the highest average daily sales in North America? | 在北美，哪个季节的日均销售额最高？ | 【地理筛选歧义】原SQL仅使用NorthAmericaSeason标签，没有筛选北美客户；North America可能限定地域或仅限定季节命名。 | 把 North America 解释为地域限定，按约定5筛选客户所在地为北美，再使用北美季节划分计算日均销售；不再接受只选季节标签却不筛地域的参考。 |

- [ ] Q25 中文通过
- [ ] Q25 接受建议

批注：

**Q26 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many customers made their first purchase in each quarter of 2007? | 2007 年各季度分别有多少客户完成了首次购买？ | — | — |

- [ ] Q26 中文通过

批注：

**Q27 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What are the top 10 products by profit margin percentage? | 按利润率排名，前 10 款产品是哪些？ | 第 10 名有并列，参考先四舍五入再排序，tie-break 结果随写法变化。 | 已裁决：边界并列时，并列者任一都算对。 |

- [ ] Q27 中文通过

批注：

**Q28 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Compare average transaction value between Store and Online channels | 在全渠道销售中，比较门店渠道和线上渠道的平均每条销售记录金额。 | 线上表与全渠道表的「交易」粒度不同，参考答案拿两种口径直接比。 | 已裁决：全渠道销售按渠道（门店、线上）分组，avg(SalesAmount)。 |

- [ ] Q28 中文通过

批注：

**Q29 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What percentage more or less do we sell on holidays compared to regular days? | 节假日相比普通日，销售多或少了百分之多少？ | — | — |

- [ ] Q29 中文通过

批注：

**Q30 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Calculate a 7-day moving average of daily online sales for December 2009 | 计算 2009 年 12 月每日线上销售额的 7 日移动平均值。 | — | — |

- [ ] Q30 中文通过

批注：

## Q31–Q40

**Q31 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Compare actual sales revenue to budget for each product category in 2009 | 比较 2009 年各产品品类的实际销售收入与预算。 | 错在外部基准的语义文档（把销售科目写成键 50，实际是 Sale Revenue），题目本身没问题。 | 已裁决：原题及参考口径保留。 |

- [ ] Q31 中文通过

批注：

**Q32 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the total lifetime value for customers who made purchases in all 3 years? | 三个年份均有购买的客户，其终身消费价值合计是多少？ | — | — |

- [ ] Q32 中文通过

批注：

**Q33 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which products are most frequently purchased together in the same order? | 同一订单中，哪些产品最常被一起购买？ | 参考 SQL 在外部基准的服务器上 30 秒超时，被剔除。 | 已裁决：本地不设超时重算参考结果；归入统计类题。 |

- [ ] Q33 中文通过

批注：

**Q34 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Calculate inventory turnover ratio by product for 2009 | 计算 2009 年各产品的库存周转率。 | — | — |

- [ ] Q34 中文通过

批注：

**Q35 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| List all employees and their manager's name | 列出所有员工及其上级经理的姓名。 | — | — |

- [ ] Q35 中文通过

批注：

**Q36 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Classify customers into Active, At Risk, and Churned based on recency | 根据距最近一次购买的时间，将客户划分为活跃、有流失风险和已流失。 | — | — |

- [ ] Q36 中文通过

批注：

**Q37 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Show each store's total sales and its percentile rank | 展示各门店的销售总额及其百分位排名。 | 小数与百分数之争（0.9967 vs 99.67）；加文档的模型被引向线上表。 | 已裁决：全渠道销售按门店求和，并给出百分位排名（小数或百分数均可）。不接受：只用线上销售（违反约定第 2 条） |

- [ ] Q37 中文通过

批注：

**Q38 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How accurate were the sales forecasts compared to actuals for Q4 2009? | 2009 年第四季度，销售预测与实际相比有多准确？ | 同 Q31。 | 已裁决：原题及参考口径保留。 |

- [ ] Q38 中文通过

批注：

**Q39 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Analyze if new product introductions affected existing product sales by subcategory | 按子品类分析，新产品上市是否影响了老产品的销售？ | 算的是品类内的蚕食（新品上市后同子品类老产品的销售是否下降）；原参考返回 0 行。 | 已裁决：新品 = 2008–2009 年上市的产品；对每个有新品的子品类，比较老产品在首个新品上市前后的线上销售（日均或同长度窗口），由宽松裁判评分。 |

- [ ] Q39 中文通过

批注：

**Q40 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What would online sales have been in EUR using end-of-day exchange rates? | 如果采用每日收盘汇率折算，线上销售额相当于多少欧元？ | 【币种口径与参考可疑】问句要求折欧元；参考用销售自身CurrencyKey连汇率并筛CurrencyName='EUR'，而线上金额已是美元。公开非空标量为0，不能证明换汇正确。 本地已确认CurrencyName=EUR、键7，问题不是币种枚举不存在。 | 先核实 EUR 汇率的报价方向与覆盖日期，再把已是美元的线上销售额按日期换算；不按销售原币键筛选 EUR 交易。缺失日期的补值/剔除规则及最终公式另交审，不因本次勾选而自动获批。 |

- [ ] Q40 中文通过
- [ ] Q40 接受建议（仅批准上述调查方向）

批注：

## Q41–Q50

**Q41 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What were last quarter's sales? | 上季度销售额是多少？ | — | — |

- [ ] Q41 中文通过

批注：

**Q42 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How is the Cameras category performing? | 相机品类的经营表现如何？ | 【开放式指标未限定】“表现”未指定指标，参考仅给年度销售趋势。 | 保留开放问句，年度销售趋势仅作为示例；接受销售额、毛利、增长趋势中的一项或多项分析，要求说明所选指标和时间范围，由 judge 判断计算与结论是否相符。 |

- [ ] Q42 中文通过
- [ ] Q42 接受建议

批注：

**Q43 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Show me the gross margin by region | 按地区展示毛利。 | G0已批准大洲/国家双解读，中文保留“按地区”；本题不再测试地理粒度选择。 | 已裁决：按客户所在大洲的毛利；按客户所在国家的毛利 |

- [ ] Q43 中文通过

批注：

**Q44 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Are online sales growing? | 线上销售在增长吗？ | 【增长时间口径与非有限值】题干未指定增长周期；参考选年度同比，首年分母0生成inf。 | 保留开放问句；接受已声明时间粒度的年度同比或月度趋势分析。无基期时记 NULL/不可计算，不能把 inf 当作有效增长率；按此修复示例参考。 |

- [ ] Q44 中文通过
- [ ] Q44 接受建议

批注：

**Q45 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which stores have the best sales per square foot? | 哪些门店的单位营业面积销售额最高？ | 【隐含Top-N】题干仅问哪些门店最好，参考固定LIMIT 10。 | 中文保留“哪些门店最好”，不补前10；接受模型声明的正整数 Top-N，或完整排序结果。参考不把未声明的 LIMIT 10 作为唯一正确边界。 |

- [ ] Q45 中文通过
- [ ] Q45 接受建议

批注：

**Q46 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What's our most profitable customer segment? | 哪个客户群体带来的利润最多？ | 「客户群体」可按学历也可按职业，原参考选了学历。 | 已裁决：按学历分组，毛利（销售金额 − 总成本）最高的一组；按职业分组，同上 |

- [ ] Q46 中文通过

批注：

**Q47 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What's the average machine downtime per store? | 各门店的机器平均停机时长是多少？ | — | — |

- [ ] Q47 中文通过

批注：

**Q48 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Is there a correlation between IT outages and sales performance? | IT 故障与销售表现之间有相关关系吗？ | 原参考用「停机超过 1,000 分钟」这一问句没说的阈值分组。 | 已裁决：按停机时长分组（阈值由模型声明），比较各组门店的平均全渠道销售；计算门店层面停机时长与全渠道销售的相关系数 |

- [ ] Q48 中文通过

批注：

**Q49 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Roll up sales to the entity hierarchy level | 按实体层级汇总销售收入。 | 原递归以父键NULL作起点，但根节点实际自指；修复后顶层3行、各级420行。 | 已裁决：计划表「实际」场景、收入科目（Sale Revenue），沿实体层级汇总，只给顶层实体；同上，逐层给出每个实体的汇总 |

- [ ] Q49 中文通过

批注：

**Q50 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What's the same-store sales growth comparing 2009 to 2008? | 比较 2009 年与 2008 年，同店销售增长率是多少？ | — | — |

- [ ] Q50 中文通过

批注：

## Q51–Q60

**Q51 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many stores are there in total? | 共有多少家门店？ | — | — |

- [ ] Q51 中文通过

批注：

**Q52 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the highest unit price in the product catalog? | 产品目录中的最高单价是多少？ | — | — |

- [ ] Q52 中文通过

批注：

**Q53 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many online orders were placed in 2009? | 2009 年共下了多少笔线上订单？ | — | — |

- [ ] Q53 中文通过

批注：

**Q54 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the total return amount from online sales? | 线上销售的退货金额合计是多少？ | — | — |

- [ ] Q54 中文通过

批注：

**Q55 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many female customers are in the database? | 客户库中有多少位女性客户？ | — | — |

- [ ] Q55 中文通过

批注：

**Q56 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the average yearly income of our customers? | 客户的平均年收入是多少？ | — | — |

- [ ] Q56 中文通过

批注：

**Q57 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many distinct product brands do we carry? | 我们经营多少个不同的产品品牌？ | — | — |

- [ ] Q57 中文通过

批注：

**Q58 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What was the largest single online sale amount ever recorded? | 历史上金额最大的一笔线上销售是多少？ | — | — |

- [ ] Q58 中文通过

批注：

**Q59 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many holidays are on the calendar? | 日历中共有多少个节假日？ | — | — |

- [ ] Q59 中文通过

批注：

**Q60 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many employees work in the Production department? | 生产部门共有多少名员工？ | — | — |

- [ ] Q60 中文通过

批注：

## Q61–Q70

**Q61 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which product subcategories generated more than $1 million in online sales in 2009? | 2009 年哪些产品子品类的线上销售额超过 100 万美元？ | — | — |

- [ ] Q61 中文通过

批注：

**Q62 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each product brand, show total online revenue and units sold in 2008, listing only brands with at least 500 units. | 按产品品牌列出 2008 年线上营收和销量，仅保留销量至少 500 件的品牌。 | — | — |

- [ ] Q62 中文通过

批注：

**Q63 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What is the average online order value by customer occupation? | 按客户职业统计线上客单价。 | — | — |

- [ ] Q63 中文通过

批注：

**Q64 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Show monthly online gross margin dollars and margin percent for 2009. | 展示 2009 年每月的线上毛利金额和毛利率。 | — | — |

- [ ] Q64 中文通过

批注：

**Q65 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which store managers run stores with more than $5M in total all-channel sales? | 哪些门店经理管理的门店，其全渠道销售总额超过 500 万美元？ | 【隐含截断】题干要求所有超过500万美元的门店经理，参考LIMIT 50。 | 删除参考 LIMIT 50，返回全部销售额超过500万美元的门店及经理；保留原阈值，中文不增加名额限制。 |

- [ ] Q65 中文通过
- [ ] Q65 接受建议

批注：

**Q66 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| What's the total discount amount given in each quarter of 2009 (excluding no-discount transactions)? | 2009 年各季度累计提供了多少折扣金额？不计无折扣交易。 | — | — |

- [ ] Q66 中文通过

批注：

**Q67 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which product colors have the highest average online unit price realized, among colors with at least 1000 units sold? | 哪些产品颜色的线上实际成交均价最高？仅考虑销量至少 1000 件的颜色。 | 【隐含截断】题干规定销量至少1000件，但没有前20；参考LIMIT 20。 | 删除参考 LIMIT 20，按实际成交均价排序并返回全部销量至少1000件的颜色；不在中文里补前20。 |

- [ ] Q67 中文通过
- [ ] Q67 接受建议

批注：

**Q68 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How many online orders were placed on holidays vs non-holidays in 2009, and the revenue for each? | 2009 年节假日和非节假日分别有多少笔线上订单、多少营收？ | — | — |

- [ ] Q68 中文通过

批注：

**Q69 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which promotion categories drove the most discounted online revenue, and what average discount percent did they achieve? | 哪些促销类别带来的折扣线上营收最高？各自的平均折扣比例是多少？ | 【均值权重未明确】参考折扣比例为折扣总额÷折前销售总额，属于金额加权，而非简单平均促销DiscountPercent。 | 接受两种明确声明的权重：折前金额加权实际折扣率（折扣总额÷折前金额总额），或成交记录的实际折扣率简单平均。分别建立参考；不把这两种均值混为同一数值。 |

- [ ] Q69 中文通过
- [ ] Q69 接受建议

批注：

**Q70 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each store type, what are the total all-channel sales and average selling area size? | 按门店类型统计全渠道销售总额和平均营业面积。 | 【平均面积受事实表扇出加权】参考在销售事实JOIN后avg(SellingAreaSize)，按销售记录数给门店面积加权。 | 按 DimStore 中唯一门店、不按销售记录数，对各门店类型计算平均营业面积；销售额按全渠道单独汇总再对齐。无销售门店仍计入该类型的门店面积均值。 |

- [ ] Q70 中文通过
- [ ] Q70 接受建议

批注：

## Q71–Q80

**Q71 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each product category, which subcategory had the highest online sales in 2009, and what was that amount? | 2009 年每个产品品类中，哪个子品类的线上销售额最高？金额是多少？ | — | — |

- [ ] Q71 中文通过

批注：

**Q72 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Show the running cumulative total of online sales by quarter across 2007-2009. | 展示 2007—2009 年按季度累计的线上销售额。 | — | — |

- [ ] Q72 中文通过

批注：

**Q73 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which 10 products have the largest gap between their current on-hand inventory and safety stock level? | 当前库存与安全库存的差额最大的 10 款产品是哪些？ | — | — |

- [ ] Q73 中文通过

批注：

**Q74 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each store, rank the top 3 products by sales in 2009 and show each product's share of the store's total. | 按门店列出 2009 年销售额排名前 3 的产品，以及各产品占该门店销售总额的比例。 | 【与约定冲突及隐含截断】题干按门店，约定2指定全渠道；已审计keep的原SQL仍读FactOnlineSales，且最终LIMIT 50。 | 重新修订原 keep：中文主题集改用全渠道销售，返回每家门店的前3名产品及其门店销售占比，去掉全局 LIMIT 50；按既有边界并列规则处理。英文锚点继续保留原题原参考。 |

- [ ] Q74 中文通过
- [ ] Q74 接受建议

批注：

**Q75 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which customers increased their spending by more than 50% from 2008 to 2009? | 哪些客户 2009 年的消费额比 2008 年增长了 50% 以上？ | 【隐含截断】题干要求所有增长超过50%的客户，参考LIMIT 25。 | 删除参考 LIMIT 25，返回所有2009年消费额较2008年增长超过50%的客户；保留原增长阈值与排序。 |

- [ ] Q75 中文通过
- [ ] Q75 接受建议

批注：

**Q76 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each product category, what percentage of total online sales came from repeat customers (customers with 2+ orders)? | 各产品品类的线上销售额中，有多少比例来自回头客（下过至少 2 笔订单的客户）？ | 【回头客粒度歧义】参考按客户全目录累计订单数>=2认定回头客，再按品类计算占比；也可能理解为在该品类买过至少两单。 | 接受“客户在全目录累计至少2单”和“客户在该品类内至少2单”两种回头客口径；要求声明粒度，分别计算品类收入占比参考，不修改企业约定。 |

- [ ] Q76 中文通过
- [ ] Q76 接受建议

批注：

**Q77 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each month in 2009, what is the month-over-month growth rate of online sales? | 计算 2009 年各月线上销售额的环比增长率。 | — | — |

- [ ] Q77 中文通过

批注：

**Q78 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Rank promotion categories by total discount amount given in 2009, and show each one's share of all discounts. | 按 2009 年折扣金额合计给促销类别排名，并展示各类别占全部折扣金额的比例。 | — | — |

- [ ] Q78 中文通过

批注：

**Q79 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which 10 stores had the highest sales-to-quota attainment in 2009? | 2009 年销售目标达成率最高的 10 家门店是哪些？ | 预算场景修正后，按统一量化规则得到完整边界组42行；仍需T05b/T06验证。 | 已裁决：改用预算场景（ScenarioKey = 2），与 Q85 一致；全渠道实际销售额 ÷ 预算场景的目标销售额（约定第 12 条）。 |

- [ ] Q79 中文通过

批注：

**Q80 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each country, what is the average days between a customer's first and most recent purchase? | 按国家统计，客户从首次购买到最近一次购买平均相隔多少天？ | 【排除单次客户与隐含截断】参考排除首末购买同日客户并LIMIT 20；题干未说排除，单次客户跨度应可为0天。 | 纳入所有有购买记录的客户，首末购买同日的跨度记0天；按国家返回完整结果，去掉同日排除条件及 LIMIT 20。 |

- [ ] Q80 中文通过
- [ ] Q80 接受建议

批注：

## Q81–Q90

**Q81 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Compute the average customer lifetime value broken down by the year each customer first made a purchase, and include how many customers fall into each cohort. | 按客户首次购买的年份分组，计算每组平均终身消费价值，并列出客户数。 | — | — |

- [ ] Q81 中文通过

批注：

**Q82 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each manager with direct reports, show how many people they manage and the average hire tenure of their team in years. | 对每位有直属下属的经理，列出其直属下属人数和团队平均入职年限。 | 【隐含截断与年限算法】参考LIMIT 25；dateDiff('year')计算跨年边界数，不是精确服务年数。 | 删除 LIMIT 25；以2009-12-31为截止日，按入职天数差÷365.25计算每位直属下属的服务年数，再对直属下属等权求平均；不使用仅统计跨年边界的年差。 |

- [ ] Q82 中文通过
- [ ] Q82 接受建议

批注：

**Q83 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Show the year-over-year retention: of customers who first bought in 2007, how many came back in 2008, and of those how many came back again in 2009? | 看客户的逐年留存：2007 年首次购买的客户中，有多少在 2008 年回购？这些人中又有多少在 2009 年再次购买？ | 【辅助列与题意不一致】returned_2008_and_2009正确做交集，但retention_2009_pct计算所有2009回购者/2007全组，不是题干“这些人中”的条件留存。 | 参考仅保留题干请求的三项人数：2007首购人数、其中2008回购人数、再其中2009回购人数。去掉非题干必需的两个留存率辅助列，避免错误的2009比率成为必答列。 |

- [ ] Q83 中文通过
- [ ] Q83 接受建议

批注：

**Q84 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Perform ABC analysis on products for 2009: identify the 'A' products (top 80% of revenue), 'B' (next 15%), and 'C' (remaining 5%), and report how many products fall in each class. | 对 2009 年产品营收做 ABC 分析：A 类占营收前 80%，B 类占接下来的 15%，C 类占其余 5%；报告各类产品数量。 | 【ABC边界及同额排序】累积营收跨80%/95%的那款产品归前组还是后组未指定；同额产品没有稳定次序。 | 按既有金额量化规范识别同额产品，把同额组整体归类：以加入该组之前的累计营收占比判定 A（<80%）、B（80%至<95%）或 C（≥95%）。跨阈值的整组留在前一类，因此实际占比可能略超80%/95%；不按物理行序拆分并列组。 |

- [ ] Q84 中文通过
- [ ] Q84 接受建议

批注：

**Q85 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Calculate each store's 2009 quota attainment: actual sales divided by sales amount quota, and list the top and bottom 5 performers. | 计算各门店 2009 年的销售目标达成率（实际销售额÷目标销售额），列出最高和最低的各 5 家门店。 | 两路Top/Bottom边界存在并列；按G0裁决留T06冻结前处理。 | 已裁决：原题及参考口径保留。 |

- [ ] Q85 中文通过

批注：

**Q86 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Analyze the relationship between discount depth and sales volume: for each product subcategory, show the correlation between promotion discount percent and sales quantity in 2009. | 分析折扣力度与销量的关系：按产品子品类展示 2009 年促销折扣比例与销售数量的相关系数。 | 原参考暗含「样本数大于 100」「取前 20」两个问句没说的条件，且包含无折扣交易。 | 已裁决：各子品类折扣百分比与销量的相关系数；是否包含无折扣交易、最少样本数、取前几名由模型声明 |

- [ ] Q86 中文通过

批注：

**Q87 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Calculate days-of-inventory-coverage per product: current on-hand quantity divided by average daily sales quantity in the last 90 days of 2009. Show the 20 products with the lowest coverage. | 计算各产品的库存可售天数：当前库存÷2009 年最后 90 天的日均销量，列出可售天数最少的 20 款产品。 | — | — |

- [ ] Q87 中文通过

批注：

**Q88 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Identify loyal customers who made at least one purchase in every quarter of 2009, and show their total spend ranked highest to lowest (top 20). | 找出 2009 年每个季度都至少购买过一次的忠实客户，按全年消费总额从高到低列出前 20 名。 | 按统一金额量化得到完整边界26行；仍需T05b/T06验证。 | 按已有冻结前验证要求继续处理，无新增口径建议。 |

- [ ] Q88 中文通过

批注：

**Q89 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each customer, classify them as Active, At Risk, or Churned based on recency, then compute average spend and product variety (distinct products purchased) per segment. | 按距最近一次购买的时间，将每位客户分为活跃、有流失风险和已流失，再计算各组客户的平均消费额和平均购买产品种类数（去重）。 | — | — |

- [ ] Q89 中文通过

批注：

**Q90 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Compute the gross margin percentage trend by product category across 2007, 2008, and 2009 and show the year-over-year change in margin in percentage points. | 展示 2007、2008、2009 年各产品品类的毛利率趋势，并列出毛利率逐年的变化，单位为百分点。 | — | — |

- [ ] Q90 中文通过

批注：

## Q91–Q100

**Q91 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Is there a relationship between a customer's yearly income and how much they spend online? | 客户年收入与其线上消费额之间有关联吗？ | — | — |

- [ ] Q91 中文通过

批注：

**Q92 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which product brands were our most profitable last quarter? | 上季度哪些产品品牌的盈利能力最强？ | 【隐含Top-N】题干未说前10；参考LIMIT 10。 | 删除参考 LIMIT 10，返回完整品牌盈利排名；中文不补前10。 |

- [ ] Q92 中文通过
- [ ] Q92 接受建议

批注：

**Q93 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Is there evidence of price elasticity — do bigger discount percentages actually move more units across our promotions? | 促销折扣比例越大，真的能带来更多销量吗？有价格弹性的证据吗？ | 统计题；模型给了明细而不是相关系数。 | 已裁决：原题及参考口径保留。 |

- [ ] Q93 中文通过

批注：

**Q94 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which of our stores look like they're losing momentum going into year-end — sales trending down from Q3 to Q4 2009? | 哪些门店在年末显出销售走弱的迹象，即 2009 年第四季度销售额低于第三季度？ | 【隐含Top-N】题干要求Q3到Q4下降的门店，参考LIMIT 20。 | 删除参考 LIMIT 20，返回全部2009年Q4销售低于Q3且Q3有销售的门店；保留全渠道口径及原有下降判断。 |

- [ ] Q94 中文通过
- [ ] Q94 接受建议

批注：

**Q95 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| How much incremental revenue do our promotions actually drive per product category compared to what we sell at full price? | 与按原价销售相比，各产品品类的促销实际带来了多少增量营收？ | 【描述统计不能识别增量因果】参考只比较促销与原价营收及其比值，没有反事实，无法推出促销“带来”的增量。 | 保留开放式，允许促销/原价营收的描述性比较，但回答须明确“无法据此识别因果增量”；参考只作描述性证据，judge 不把营收差或比值直接当作促销造成的增量。 |

- [ ] Q95 中文通过
- [ ] Q95 接受建议

批注：

**Q96 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each yearly customer cohort, what fraction actually came back and bought again in a later year? | 按首次购买年份划分客户群体，每组有多大比例的客户在之后的年份回来购买过？ | — | — |

- [ ] Q96 中文通过

批注：

**Q97 · 已有裁决，仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which products had the biggest second-half comeback in 2009 — meaning H2 sales dramatically exceeded H1? | 2009 年哪些产品在下半年的销售反弹最大，即下半年销售额大幅超过上半年？ | 按增幅还是增加额、取几名、上半年至少多少，问句都没说。 | 已裁决：按下半年相对上半年的增幅排名（上半年下限、前 N 名由模型声明）；按下半年相对上半年的增加额排名（前 N 名由模型声明） |

- [ ] Q97 中文通过

批注：

**Q98 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Which product categories depend most heavily on a single quarter for their annual sales? | 哪些产品品类的全年销售最依赖某一个季度？ | 【年度粒度歧义】题干问全年依赖某季度，参考只筛2009；没说逐年还是最近一年。 | 接受只分析2009年度，或分别按2007、2008、2009年度分析；要求声明年份，均在各自年度内计算最大季度份额。分别建参考，不把多年的同季度合并后称为某一年的集中度。 |

- [ ] Q98 中文通过
- [ ] Q98 接受建议

批注：

**Q99 · 仅审中文**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| For each product category, how much bigger is an average weekend day compared to an average weekday? | 按产品品类比较，平均一个周末日的销售额比平均一个工作日高多少？ | — | — |

- [ ] Q99 中文通过

批注：

**Q100 · 待裁决**

| 英文原句 | 中文草稿 | 疑点与证据 | 建议／既有裁决 |
|---|---|---|---|
| Who are our true power customers — people who are both in the top 10% by order count AND top 10% by average order size? | 哪些客户既处于订单数前 10%，又处于客单价前 10%，称得上真正的高价值客户？ | 【隐含截断与分位算法】题干要求所有同时位于订单数/客单价前10%的客户，参考LIMIT 30并用近似quantile(0.9)。 | 删除 LIMIT 30；按既有量化规范处理订单数和客单价后，分别计算精确、线性插值的90%分位阈值，保留同时达到两个阈值的全部客户，包含阈值并列；不用近似分位结果作唯一真值。 |

- [ ] Q100 中文通过
- [ ] Q100 接受建议

批注：

## 批阅后的处理

我会读取你勾选的项目和批注，逐题落实，不把一题的勾选扩展到其他题。22项建议批准后仍须执行重算；新增或修改参考在G1后交T05b独立验证。T04全部中文和待决项审完之后再进入T05。

标签草稿见 [cube_100.yaml](../questions/cube_100.yaml)，分布见 [label_distribution.md](../reports/label_distribution.md)。标签以L1无可调用指标为基准；split和summary_coverage留T06。Q43接受多解的评测代价继续保留在标签和覆盖标注中。
