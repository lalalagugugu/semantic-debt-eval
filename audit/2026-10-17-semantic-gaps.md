# 约定与L1未写清的口径：只列缺口，待用户拍板

17项逐条列明涉及题号、至少两种解读和实算结果。本表不修改冻结语义层、不新增默认，也不因敏感性试算增添可接受参考。开放问法与缺少企业默认分别标注；不能把所有开放分析题都变成必须只有一种方法。已明文规定的交易事件、空品类、营业状态、库存粒度、折扣率不列为可自由选择的口径。

Q42/Q43/Q44/Q46/Q48/Q49等不同维度、观察层级或分析形式属于问法／展示空间，43份盘点已单列；这里聚焦参考计算依赖的未传达默认与有实质差异的含混词。

| 缺口 | 题 | 理解数 | 结果 | 说明 |
|---|---|---:|---|---|
| G01 全渠道交易单位与平均订单金额 | Q13、Q28 | 2 | 不能比较：全渠道没有订单号 | 约定2规定门店走FactSales，约定8客单价需要订单号，但全渠道汇总表没有订单号；未定义交易笔是否指聚合行 |
| G02 平均停机的分母 | Q47 | 2 | 不同 | L1定义停机总时长、故障次数，未定义机器平均是按事件平均还是先按机器累计后平均 |
| G03 预测准确度指标 | Q38 | 2 | 不同 | 场景和收入科目已定，但未定义准确度究竟报告绝对百分比误差还是其互补准确率 |
| G04 新老产品观察窗口 | Q39 | 2 | 不同 | L1描述上市日期，未定义新品的业务年限及上市前后观察窗口；以下只比较两种示例窗口，不私定默认 |
| G05 缺少当日收盘汇率的日期 | Q40 | 2 | 不同 | 约定6定义本币美元，但假设换汇的问题未给汇率缺失日处理；精确日匹配只是当前judge部分示例，不能私自当全期答案 |
| G06 回头客订单累计范围 | Q76 | 2 | 不同 | 题面给出至少两笔订单，但未指定按客户全目录累计，还是在当前品类内累计；L1没有回头客指标 |
| G07 ABC跨阈值同额组归属 | Q84 | 2 | 不同 | 题面保留80/15/5参数，但L1未定义跨过阈值的整个同额产品组归前一类还是后一类；两算法均不拆同额组 |
| G08 前10%的阈值算法 | Q100 | 2 | 相同 | 题库已有精确线性插值裁决，但约定及L1未传达该算法；审计另一种按ceil(N/10)名次取阈值且含并列的解读，不修改现有参考 |
| G09 前10%的阈值算法 | Q118 | 2 | 相同 | 题库已有精确线性插值裁决，但约定及L1未传达该算法；审计另一种按ceil(N/10)名次取阈值且含并列的解读，不修改现有参考 |
| G10 反弹幅度与大幅阈值 | Q97 | 2 | 不同 | 毛利／销售额定义不解决反弹按金额还是比例及大幅下限；现有两份只作judge示例 |
| G11 全年指哪一年或逐年 | Q98 | 2 | 不同 | 当前问题未点名年份；用户明确允许该问法多解，L1今天并未唯一规定这句全年是单年还是每年 |
| G12 降幅是相对比率还是绝对减少额 | Q117 | 2 | 不同 | L1定义同比增长率，但题面只写降幅最大，没有把这个词唯一映射到比率或金额；两种排序都保持题目同店与年份 |
| G13 盈利能力的排序指标 | Q92 | 2 | 不同 | L1同时定义毛利额和毛利率，但未唯一解释盈利能力；这是开放judge问法，不私定只认一个 |
| G14 公司排名的并列编号 | Q119 | 2 | 相同 | L1未定义竞赛排名1/1/3还是稠密排名1/1/2；不是改并列成员的全局量化规则 |
| G15 变异系数标准差分母 | Q121 | 2 | 不同 | L1没有变异系数指标，未指定12个月按总体还是样本；不能由参考作者新增企业定义 |
| G16 促销增量的基准与因果含义 | Q95 | 2 | 不同 | 约定10规定促销筛选，却未定义增量反事实基准；两个描述性差值都不是因果识别，不能据此擅定增量口径 |
| G17 未点名的相关性方法 | Q48、Q86、Q91 | 2 | 不同 | L1未指定未点名相关性默认Pearson还是Spearman；Q120已在题面点名Pearson，不属于此缺口。以下以Q91相同客户域实测 |

## G01 全渠道交易单位与平均订单金额

涉及：Q13、Q28。状态：待用户裁决；不新增或替换参考。

已有定义边界：约定2规定门店走FactSales，约定8客单价需要订单号，但全渠道汇总表没有订单号；未定义交易笔是否指聚合行。

| 解读 | 实算证据 |
|---|---|
| 交易=全渠道事实汇总行；参考当前avg(SalesAmount)/count() | {"stores": 306, "records": 3406089} |
| 交易=真实订单，按订单金额计算均值 | {"computable": false, "reason": "FactSales没有订单号，不能从汇总行还原订单；不能伪造等价结果"} |

## G02 平均停机的分母

涉及：Q47。状态：待用户裁决；不新增或替换参考。

已有定义边界：L1定义停机总时长、故障次数，未定义机器平均是按事件平均还是先按机器累计后平均。

| 解读 | 实算证据 |
|---|---|
| 每次故障的平均停机时长 | {"rows": 299, "sha256": "39388012962276ecb748f611aa53767f671bcaab71ee2ff653aeeb6aa2a45647"} |
| 每机器累计停机时长的平均 | {"rows": 299, "sha256": "000b2d73f7535fb3ead320e22fd797c88077924eef2c46d2ec654051554fe8bf"} |

## G03 预测准确度指标

涉及：Q38。状态：问法歧义现有参考保留；是否补统一默认待用户拍板。

已有定义边界：场景和收入科目已定，但未定义准确度究竟报告绝对百分比误差还是其互补准确率。

| 解读 | 实算证据 |
|---|---|
| 原参考解读 | {"reference": "refs/cube/Q38-1.csv", "columns": [{"name": "ProductCategoryName", "type": "String"}, {"name": "actual", "type": "Float64"}, {"name": "forecast", "type": "Float64"}, {"name": "error_pct", "type": "Nullable(Float64)"}], "rows": 8, "sha256": "d9b1200b1f8100d7b6885fd7c7ad285c99848a15690713107ac61d15882d9715"} |
| 准确率=100%-绝对百分比误差；题面未点名误差率或准确率，保留互补解读 | {"reference": "refs/cube/Q38-2.csv", "columns": [{"name": "ProductCategoryName", "type": "String"}, {"name": "actual", "type": "Float64"}, {"name": "forecast", "type": "Float64"}, {"name": "accuracy_pct", "type": "Nullable(Float64)"}], "rows": 8, "sha256": "c0c8514bd7183fa3b2b5219945de5709b0ad9393ecf8ee666a6ccf46ef349fbb"} |

## G04 新老产品观察窗口

涉及：Q39。状态：待用户裁决；不新增或替换参考。

已有定义边界：L1描述上市日期，未定义新品的业务年限及上市前后观察窗口；以下只比较两种示例窗口，不私定默认。

| 解读 | 实算证据 |
|---|---|
| 按当前示例，以数据边界内最长对称窗口比较旧产品日均销售 | {"rows": 30, "sha256": "6b7375dbab17d841b32b6fe40691516d2439cc08bbc2eb9bd019415af5716098"} |
| 同一上市日期／老产品定义，比较上市前后各90日 | {"rows": 30, "sha256": "d1ebf86af9926bc9af3f792a6ba6b386b27cfabffe6be8f20b179d5f0b13457f"} |

## G05 缺少当日收盘汇率的日期

涉及：Q40。状态：待用户裁决；不新增或替换参考。

已有定义边界：约定6定义本币美元，但假设换汇的问题未给汇率缺失日处理；精确日匹配只是当前judge部分示例，不能私自当全期答案。

| 解读 | 实算证据 |
|---|---|
| 只按当日确有EUR汇率的日期匹配 | {"sales_eur": 53934387.92781146, "covered_days": 31} |
| 缺报价日沿用之前最近一次EUR收盘价（仅敏感性试算，未批准） | {"sales_eur": 1935245135.5097272, "covered_days": 1096} |

## G06 回头客订单累计范围

涉及：Q76。状态：问法歧义现有参考保留；是否补统一默认待用户拍板。

已有定义边界：题面给出至少两笔订单，但未指定按客户全目录累计，还是在当前品类内累计；L1没有回头客指标。

| 解读 | 实算证据 |
|---|---|
| 客户全目录累计至少两笔线上订单，须声明粒度；购买事件=全部行（含纯退货行） | {"reference": "refs/cube/Q76-1.csv", "columns": [{"name": "category", "type": "Nullable(String)"}, {"name": "pct_repeat_customer_sales", "type": "Nullable(Float64)"}], "rows": 9, "sha256": "ca1e7be2bf5a9c0affe228cdabd87d806fe95d695e0d639f18f2625dcf0766b8"} |
| 在该品类内至少两笔线上订单的回头客，须声明粒度；购买事件=全部行 | {"reference": "refs/cube/Q76-2.csv", "columns": [{"name": "category", "type": "Nullable(String)"}, {"name": "pct_repeat_customer_sales", "type": "Nullable(Float64)"}], "rows": 9, "sha256": "7a85da13b81db918ead0e4e7a8cff9cd2d975ba9b389d3fcc5c0bdaa355966d0"} |

## G07 ABC跨阈值同额组归属

涉及：Q84。状态：待用户裁决；不新增或替换参考。

已有定义边界：题面保留80/15/5参数，但L1未定义跨过阈值的整个同额产品组归前一类还是后一类；两算法均不拆同额组。

| 解读 | 实算证据 |
|---|---|
| 同额组开始前累计额决定类别（当前参考） | {"class_product_counts": {"A": 1132, "B": 666, "C": 706}} |
| 加入同额组后累计额决定类别 | {"class_product_counts": {"A": 1131, "B": 666, "C": 707}} |

## G08 前10%的阈值算法

涉及：Q100。状态：待用户裁决；不新增或替换参考。

已有定义边界：题库已有精确线性插值裁决，但约定及L1未传达该算法；审计另一种按ceil(N/10)名次取阈值且含并列的解读，不修改现有参考。

| 解读 | 实算证据 |
|---|---|
| (N-1)*0.9精确线性插值P90，含阈值并列 | {"thresholds": ["129.0000000", "651.334"], "members": 108, "membership_sha256": "693174ad3280cc5f2906aeb0b240fd5910a0f655769f964382d6b4bb4e5cf333"} |
| 前ceil(N/10)的第N名值为阈值，含并列 | {"thresholds": ["129.000000", "651.35"], "members": 108, "membership_sha256": "693174ad3280cc5f2906aeb0b240fd5910a0f655769f964382d6b4bb4e5cf333"} |

## G09 前10%的阈值算法

涉及：Q118。状态：待用户裁决；不新增或替换参考。

已有定义边界：题库已有精确线性插值裁决，但约定及L1未传达该算法；审计另一种按ceil(N/10)名次取阈值且含并列的解读，不修改现有参考。

| 解读 | 实算证据 |
|---|---|
| (N-1)*0.9精确线性插值P90，含阈值并列 | {"thresholds": ["901871.842"], "members": 225, "membership_sha256": "45173ba21836bb29aea6f8c62cc4269f59e217be5050ca128b74215516313263"} |
| 前ceil(N/10)的第N名值为阈值，含并列 | {"thresholds": ["902946.76"], "members": 225, "membership_sha256": "45173ba21836bb29aea6f8c62cc4269f59e217be5050ca128b74215516313263"} |

## G10 反弹幅度与大幅阈值

涉及：Q97。状态：问法歧义现有参考保留；是否补统一默认待用户拍板。

已有定义边界：毛利／销售额定义不解决反弹按金额还是比例及大幅下限；现有两份只作judge示例。

| 解读 | 实算证据 |
|---|---|
| 示例：原参考解读 | {"reference": "refs/cube/Q97-1.csv", "columns": [{"name": "ProductName", "type": "Nullable(String)"}, {"name": "h1_sales", "type": "Float64"}, {"name": "h2_sales", "type": "Float64"}, {"name": "h2_vs_h1_pct", "type": "Nullable(Float64)"}, {"name": "ProductKey", "type": "Int32"}], "rows": 15, "sha256": "df60733f5567609dc00878bd7820a2c5096df29a162ad5c893ae81f858c4fa5f"} |
| 示例：按H2较H1的增加额排序，取前15名，不设H1下限 | {"reference": "refs/cube/Q97-2.csv", "columns": [{"name": "ProductKey", "type": "Int32"}, {"name": "ProductName", "type": "Nullable(String)"}, {"name": "h1_sales", "type": "Float64"}, {"name": "h2_sales", "type": "Float64"}, {"name": "sales_increase", "type": "Float64"}], "rows": 15, "sha256": "08b80d1de3e60e48da0ef92d9205458b3b65c94fb18be5ccc1de0e2c83294e26"} |

## G11 全年指哪一年或逐年

涉及：Q98。状态：问法歧义现有参考保留；是否补统一默认待用户拍板。

已有定义边界：当前问题未点名年份；用户明确允许该问法多解，L1今天并未唯一规定这句全年是单年还是每年。

| 解读 | 实算证据 |
|---|---|
| 仅分析2009年度，须声明年份 | {"reference": "refs/cube/Q98-1.csv", "columns": [{"name": "ProductCategoryName", "type": "Nullable(String)"}, {"name": "peak_quarter_share_pct", "type": "Float64"}, {"name": "peak_quarter", "type": "UInt8"}], "rows": 9, "sha256": "52fed2ec5ef3795944a6da6b5e89b36e671987ab1cdb94bf6521f76e6b675b61"} |
| 分别按2007、2008、2009年度分析，各年内计算季度份额，须声明年份 | {"reference": "refs/cube/Q98-2.csv", "columns": [{"name": "ProductCategoryName", "type": "Nullable(String)"}, {"name": "year", "type": "UInt16"}, {"name": "peak_quarter_share_pct", "type": "Float64"}, {"name": "peak_quarter", "type": "UInt8"}], "rows": 27, "sha256": "750f50a08a26aa3c13bd063e78970cbe109264b61c6205856217a711989799f3"} |

## G12 降幅是相对比率还是绝对减少额

涉及：Q117。状态：待用户裁决；不新增或替换参考。

已有定义边界：L1定义同比增长率，但题面只写降幅最大，没有把这个词唯一映射到比率或金额；两种排序都保持题目同店与年份。

| 解读 | 实算证据 |
|---|---|
| 按相对降幅选择3店（当前参考） | {"store_keys": [46, 71, 45]} |
| 按销售减少金额选择3店 | {"store_keys": [200, 308, 309]} |

## G13 盈利能力的排序指标

涉及：Q92。状态：开放问法保留；是否需要企业默认待用户审阅。

已有定义边界：L1同时定义毛利额和毛利率，但未唯一解释盈利能力；这是开放judge问法，不私定只认一个。

| 解读 | 实算证据 |
|---|---|
| 按毛利额排序（当前示例） | {"brands": ["Contoso", "Fabrikam", "Litware", "Adventure Works", "Proseware", "Wide World Importers", "The Phone Company", "A. Datum", "Southridge Video", "Northwind Traders", "Tailspin Toys"]} |
| 按毛利率排序 | {"brands": ["A. Datum", "Fabrikam", "Wide World Importers", "Adventure Works", "Proseware", "Contoso", "Litware", "The Phone Company", "Northwind Traders", "Southridge Video", "Tailspin Toys"]} |

## G14 公司排名的并列编号

涉及：Q119。状态：问法歧义现有参考保留；是否补统一默认待用户拍板。

已有定义边界：L1未定义竞赛排名1/1/3还是稠密排名1/1/2；不是改并列成员的全局量化规则。

| 解读 | 实算证据 |
|---|---|
| 声明竞赛排名1、1、3 | {"reference": "refs/new/Q119-1.csv", "columns": [{"name": "StoreKey", "type": "Int32"}, {"name": "StoreName", "type": "String"}, {"name": "ProductKey", "type": "Int32"}, {"name": "ProductName", "type": "Nullable(String)"}, {"name": "product_sales", "type": "Float64"}, {"name": "global_rank", "type": "UInt64"}], "rows": 310, "sha256": "bab21f5c3bc8c4e90dad155eca65a551f3d6276b6027558200f7476b8569eca2"} |
| 声明稠密排名1、1、2 | {"reference": "refs/new/Q119-2.csv", "columns": [{"name": "StoreKey", "type": "Int32"}, {"name": "StoreName", "type": "String"}, {"name": "ProductKey", "type": "Int32"}, {"name": "ProductName", "type": "Nullable(String)"}, {"name": "product_sales", "type": "Float64"}, {"name": "global_rank", "type": "UInt64"}], "rows": 310, "sha256": "bab21f5c3bc8c4e90dad155eca65a551f3d6276b6027558200f7476b8569eca2"} |

## G15 变异系数标准差分母

涉及：Q121。状态：问法歧义现有参考保留；是否补统一默认待用户拍板。

已有定义边界：L1没有变异系数指标，未指定12个月按总体还是样本；不能由参考作者新增企业定义。

| 解读 | 实算证据 |
|---|---|
| 声明总体标准差（除以12） | {"reference": "refs/new/Q121-1.csv", "columns": [{"name": "category", "type": "Nullable(String)"}, {"name": "monthly_sales_amount", "type": "Float64"}, {"name": "coefficient_ratio", "type": "Nullable(Float64)"}], "rows": 9, "sha256": "3c91e8a9b271824c64ca0cd1dba631acbb92e979050dd5f128499272852ed290"} |
| 声明样本标准差（除以11） | {"reference": "refs/new/Q121-2.csv", "columns": [{"name": "category", "type": "Nullable(String)"}, {"name": "monthly_sales_amount", "type": "Float64"}, {"name": "coefficient_ratio", "type": "Nullable(Float64)"}], "rows": 9, "sha256": "fa3a35c5227d0dfd2c84a94f8654df98eb02381d8ef312f1fcad0e0c5ec02f85"} |

## G16 促销增量的基准与因果含义

涉及：Q95。状态：待用户裁决；不新增或替换参考。

已有定义边界：约定10规定促销筛选，却未定义增量反事实基准；两个描述性差值都不是因果识别，不能据此擅定增量口径。

| 解读 | 实算证据 |
|---|---|
| 促销收入合计减原价收入合计（仅敏感性示例） | {"rows": 9, "sha256": "2f1ca8c51ccb5412582dc86665c07bf346089599bef35256c2bb0e87d8d371c5"} |
| 促销行均收入减原价行均收入（仅敏感性示例） | {"rows": 9, "sha256": "459457a6f60793890a3ddbfc307d29c8f7fb5f126b1c7ad47771142231b936f7"} |

## G17 未点名的相关性方法

涉及：Q48、Q86、Q91。状态：开放judge允许声明方法；不把Q91的差异伪称为Q48/Q86已执行同一试算。

已有定义边界：L1未指定未点名相关性默认Pearson还是Spearman；Q120已在题面点名Pearson，不属于此缺口。以下以Q91相同客户域实测。

| 解读 | 实算证据 |
|---|---|
| Pearson线性相关 | {"evidence_question": "Q91", "value": 0.7349257619515496} |
| Spearman秩相关 | {"evidence_question": "Q91", "value": 0.49634598109460387} |

逐题补充实算（最终筛选）：
- Q48：306个观察，Pearson=0.7096406904249098，Spearman=0.09782619508051292，不同。
- Q91：18869个观察，Pearson=0.7349257619515496，Spearman=0.49634598109460387，不同。
- Q86：31个子品类全部Pearson与Spearman不同；样本下限不设／>100分别保留31／31组，当前结果相同。100仅为已声明judge示例参数，不设企业默认。

初次支持文件只实测Q91，没有把结果外推；补充2026-10-17-correlation-gap-final.json现已分别实测Q48/Q86/Q91。Q120题面明确Pearson，不属该缺口。

结果相同不等于定义已经明确：Q119两种排名当前CSV完全相同；Q100/Q118两种前10%算法当前成员相同，但阈值算法和未来适用解释仍须用户决定是否补文档。Q13/Q28的真实订单解读因缺数据无法计算，不能报告相同或不同。

缺口通过audit_semantic_gaps.py实算，只用数据和参考，不读取模型输出。支持JSON记录完整可重现签名、行数、阈值和已有参考路径；相关性补充按频数计算精确并列中秩，经展开小样本对照验证。
