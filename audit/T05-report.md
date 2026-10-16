# T05第二轮正式SQL与参考交付

题库分支codex/t05-finalize从已合并题库#10后的main491ef16开始；主仓库分支codex/t05-closeout-main从含已合并#36的main95575fd开始，随后同步最新main14d749e；四份评分相关源码逐字未变。没有复用T05-work，没有覆盖原工作区未提交文件。

已批准的22道第二轮中文题干保持原样，正式SQL及全部参考从头计算。现行122题148份参考：外部100题119份、新题22题29份。原始第一轮报告与题意/参考清单另存在audit/reviews/；不继承第一轮复算结论。

7/122题为分组或嵌套Top-N：Q22、Q71、Q74、Q85、Q98、Q117、Q119。全局量化规范不变。Q79另存原始公开域306个边界成员和量纲策略SHA，冻结条件是T05b独立pandas成员多重集相同。

待办10的20题24份参考逐份执行INNER与LEFT，不只看静态路径。字面LEFT有21份不同、3份相同；Q73按事实产品键纠正粒度后Top-10相同，因此按正确对象粒度为20份不同、4份无输出影响。20份差异包含Q42-1差分列6位量化尾差，不能宣称均为业务金额损失。修复缺维记录保留事实键、缺名NULL、未分类单列；Q33每订单先去重产品后配对，已离线不限时验证。详见T05-inner-left.*。

购买事件全122题扫描，18题21份原参考实际双算法执行；9题结果不同，新增9份参考（Q26、Q33、Q36、Q76、Q80、Q89、Q115、Q116、Q122）。Q116两个窗口的正销量结果相同共用一份新增参考。Q122分母始终全部378070个订单号，不过滤2044个纯退货订单。金额累计及冻结订单数定义保持原口径。详见T05-purchase-events.*。

新题金额及统计含义：Q110分子分母均来自FactSales，Online按DimChannel；Q112逐店缺口再汇总经理；Q113保留真实空结果；Q118按全局固定金额精度精确P90并包含边界同分；Q119先完整公司产品域排名再各店选第一；Q121全年12个月零补齐且均值0输出NULL；Q122全部产品对含零共购。

复现（先设置SEMDEBT_MAIN_DIR、SEMDEBT_DATA_DIR）：

```bash
uv run --locked python scripts/build_refs.py --refresh-rules
uv run --locked python scripts/build_refs.py --check
uv run --locked python scripts/validate_t04.py
uv run --locked python scripts/validate_t05.py
uv run --locked python scripts/validate_rules.py
uv run --locked python scripts/check_t05_domains.py
uv run --locked python scripts/snapshot_q79_boundary.py --check
```

SQL串行使用chdb-eval，单线程、离线参考不限时；不打开主chdb，不调用付费模型，不增加依赖，不修改冻结语义层和评分精度。完整600条复验另见rules-final-impact.*，按仅契约／仅参考／联合分轴记录，不把参考修复归为契约影响。

执行记录：第二轮Q112首次类型预检缺EmployeeKey别名，修正后26份类型预检通过；只读脚本导入路径及元数据归档格式错误已修正。购买双解落地首次误用notes字段中止、未写题目；随后的旧139份误启动重算被手动中止，构建器尚未提交任何输出。修正为既有scoring_notes后，正式148份全部重算。失败未当作空结果。首轮600条在Q21的约60万行数值敏感性投影出现平方级耗时，手动中止于已执行121条，原始候选保留在数据目录rules-backfill/20261016T054816Z；该未完成轮次不作为结论。runner改为调用同一评分核心取得判定和原因，省去未写入报告的敏感性投影，合成矩阵与正式score_detailed逐项对照通过后从头重跑600条。第二轮未完成运行同样在Q21正式列排列枚举耗时，已中止并保留121条执行；最终runner另用NULL匹配必要条件做等价早拒绝，避免对不可能匹配的整集重复枚举，未改评分标准。未改生产评分器、精度或容差。主仓库离线测试曾因漏设EVAL_DIR、同步新T11后又漏设DATA_DIR而失败；补充布局检查首次同样漏设DATA_DIR，补全后重跑，补全环境并明确排除主chdb集成测试后通过；最终检查结果见T05-finalization.md。

Codex SQL交付完成；跨厂商T05b及T06尚未完成，未打eval-v1。英文锚点参考接线仍由Claude Code在T11执行。

## 英文原始参考规则交接

最新T11报告交Codex的6道结构差异原始参考，加上本轮Q21/Q34保留产品键新增的两道，共8道（EN13、14、20、21、34、74、83、87）。已用T11实际保存的原始payload验证SQL／文件哈希和返回类型，推断量纲并通过规则自比，完整逐参考字典在audit/anchor-original-rules-review.md。未修改T11接线，不把原始错误参考加入中文可接受答案；原始SQL、渠道、连接保持外部原样。T11仍须接入字典并验证完整边界，EN97保持judge。
