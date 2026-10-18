# 外部100题逐参考rules审阅表

状态：自动推断结果供用户过目；不是人工批准或T05b独立重算结论。

逐参考rules整份覆盖题级rules；没有ref.rules时沿用题级。下表每列依次为列名、查询返回类型、量纲；[整数守卫]仅标记count且返回整数类型的列。other不享受额外atol，不因数值外观猜单位。

量纲策略SHA256：`7413327151dc85b9ff08233a191ce238dfe6722058b0c1fa71c0649facc540db`。并列使用Decimal ROUND_HALF_EVEN，amount两位、percentage先除100再六位、ratio/其他数值六位。

Q101–Q122已按批准稿落实第二轮正式SQL，显式声明量纲并重新计算；这不是T05b独立pandas核验或eval-v1冻结结论。

| 题号／参考 | ordered | 选择约束 | 列名／返回类型／推断量纲 |
|---|---|---|---|
| Q01/1 | false | 参考行集 | `count()` / `UInt64` / **count** [整数守卫] |
| Q02/1 | false | 参考行集 | `sum(SalesAmount)` / `Float64` / **amount** |
| Q03/1 | false | 参考行集 | `countDistinct(CustomerKey)` / `UInt64` / **count** [整数守卫] |
| Q04/1 | false | 参考行集 | `ProductName` / `String` / **other** |
| Q05/1 | false | 参考行集 | `ProductCategoryName` / `String` / **other**<br>`product_count` / `UInt64` / **count** [整数守卫] |
| Q06/1 | false | 参考行集 | `sum(SalesAmount)` / `Float64` / **amount** |
| Q07/1 | true | Top-10，键[1] | `ProductName` / `String` / **other**<br>`UnitPrice` / `Nullable(Float64)` / **amount** |
| Q08/1 | false | 参考行集 | `FirstName` / `String` / **other**<br>`LastName` / `String` / **other** |
| Q09/1 | false | 参考行集 | `avg(UnitCost)` / `Nullable(Float64)` / **amount** |
| Q10/1 | false | 参考行集 | `store_count` / `UInt64` / **count** [整数守卫] |
| Q11/1 | false | 参考行集 | `ProductCategoryName` / `Nullable(String)` / **other**<br>`total_sales` / `Float64` / **amount** |
| Q12/1 | false | 参考行集 | `month` / `UInt8` / **other**<br>`monthly_sales` / `Float64` / **amount** |
| Q13/1 | false | 参考行集 | `s.StoreKey` / `Int32` / **other**<br>`StoreName` / `String` / **other**<br>`total_sales` / `Float64` / **amount**<br>`average_unit_price` / `Nullable(Float64)` / **amount**<br>`sales_quantity` / `Int64` / **count** [整数守卫] |
| Q14/1 | false | 参考行集 | `customers` / `UInt64` / **count** [整数守卫] |
| Q15/1 | false | 参考行集 | `RegionCountryName` / `String` / **other**<br>`total_sales` / `Float64` / **amount** |
| Q16/1 | false | 参考行集 | `year` / `UInt16` / **other**<br>`total_sales` / `Float64` / **amount** |
| Q17/1 | false | 参考行集 | `IsWorkDay` / `String` / **other**<br>`sales` / `Float64` / **amount**<br>`percentage` / `Nullable(Float64)` / **percentage** |
| Q18/1 | false | 参考行集 | `PromotionType` / `Nullable(String)` / **other**<br>`total_discount` / `Float64` / **amount** |
| Q19/1 | false | 参考行集 | `Gender` / `Nullable(String)` / **other**<br>`avg_order_amount` / `Float64` / **amount** |
| Q20/1 | false | 参考行集 | `ProductKey` / `Int32` / **other**<br>`ProductName` / `Nullable(String)` / **other**<br>`on_hand_units` / `Int64` / **count** [整数守卫]<br>`safety_stock_units` / `Int64` / **count** [整数守卫] |
| Q21/1 | false | 参考行集 | `s.StoreKey` / `Int32` / **other**<br>`StoreName` / `String` / **other**<br>`current_on_hand_quantity` / `Int64` / **other** |
| Q22/1 | false | 1步骤分组选择 | `c.CustomerKey` / `Int32` / **other**<br>`FirstName` / `String` / **other**<br>`LastName` / `String` / **other**<br>`RegionCountryName` / `String` / **other**<br>`total_spent` / `Float64` / **amount**<br>`rn` / `UInt64` / **other** |
| Q23/1 | false | 参考行集 | `month` / `UInt8` / **other**<br>`monthly_sales` / `Float64` / **amount**<br>`cumulative_sales` / `Float64` / **amount** |
| Q24/1 | false | 参考行集 | `ProductCategoryName` / `Nullable(String)` / **other**<br>`total_returns` / `Int64` / **count** [整数守卫]<br>`total_sales` / `Int64` / **count** [整数守卫]<br>`return_rate_pct` / `Nullable(Float64)` / **percentage** |
| Q25/1 | true | Top-1，键[1] | `NorthAmericaSeason` / `String` / **other**<br>`avg_daily_sales` / `Float64` / **amount** |
| Q26/1 | false | 参考行集 | `quarter` / `UInt8` / **other**<br>`new_customers` / `UInt64` / **count** [整数守卫] |
| Q27/1 | true | Top-10，键[3] | `ProductName` / `String` / **other**<br>`UnitPrice` / `Nullable(Float64)` / **amount**<br>`UnitCost` / `Nullable(Float64)` / **amount**<br>`margin_pct` / `Nullable(Float64)` / **percentage** |
| Q28/1 | false | 参考行集 | `ChannelName` / `String` / **other**<br>`average_unit_price` / `Nullable(Float64)` / **amount** |
| Q29/1 | false | 参考行集 | `pct_difference` / `Float64` / **percentage** |
| Q30/1 | false | 参考行集 | `DateKey` / `Date` / **other**<br>`daily_sales` / `Float64` / **amount**<br>`moving_avg_7d` / `Float64` / **other** |
| Q31/1 | false | 参考行集 | `ProductCategoryName` / `String` / **other**<br>`actual` / `Float64` / **other**<br>`budget` / `Float64` / **amount** |
| Q32/1 | false | 参考行集 | `customer_count` / `UInt64` / **count** [整数守卫]<br>`total_ltv` / `Float64` / **amount** |
| Q33/1 | true | 参考行集 | `product1_key` / `Int32` / **other**<br>`product2_key` / `Int32` / **other**<br>`product1` / `Nullable(String)` / **other**<br>`product2` / `Nullable(String)` / **other**<br>`co_order_count` / `UInt64` / **count** [整数守卫] |
| Q34/1 | false | 参考行集 | `ProductName` / `Nullable(String)` / **other**<br>`total_cogs` / `Float64` / **amount**<br>`avg_inventory` / `Float64` / **other**<br>`turnover_ratio` / `Nullable(Float64)` / **ratio**<br>`ProductKey` / `Int32` / **other** |
| Q35/1 | false | 参考行集 | `FirstName` / `String` / **other**<br>`LastName` / `String` / **other**<br>`Title` / `Nullable(String)` / **other**<br>`manager_first` / `String` / **other**<br>`manager_last` / `String` / **other** |
| Q36/1 | false | 参考行集 | `segment` / `String` / **other**<br>`customers` / `UInt64` / **count** [整数守卫] |
| Q37/1 | false | 参考行集 | `StoreName` / `String` / **other**<br>`total_sales` / `Float64` / **amount**<br>`percentile` / `Float64` / **percentage** |
| Q38/1 | false | 参考行集 | `ProductCategoryName` / `String` / **other**<br>`actual` / `Float64` / **other**<br>`forecast` / `Float64` / **other**<br>`accuracy_pct` / `Nullable(Float64)` / **percentage** |
| Q39/1 | false | 参考行集 | `subcategory_key` / `Nullable(Int32)` / **other**<br>`ProductSubcategoryName` / `String` / **other**<br>`introduction_date` / `Nullable(Date)` / **other**<br>`window_days` / `Nullable(Int64)` / **other**<br>`before_daily_sales` / `Nullable(Float64)` / **amount**<br>`after_daily_sales` / `Nullable(Float64)` / **amount** |
| Q39/2 | false | 参考行集 | `subcategory_key` / `Nullable(Int32)` / **other**<br>`ProductSubcategoryName` / `String` / **other**<br>`introduction_date` / `Nullable(Date)` / **other**<br>`window_days` / `Int64` / **other**<br>`before_daily_sales` / `Float64` / **amount**<br>`after_daily_sales` / `Float64` / **amount** |
| Q40/1 | false | 参考行集 | `sales_eur` / `Float64` / **amount** |
| Q41/1 | false | 参考行集 | `sum(SalesAmount)` / `Float64` / **amount** |
| Q42/1 | false | 参考行集 | `year` / `UInt16` / **other**<br>`sales` / `Float64` / **amount**<br>`yoy_change` / `Float64` / **other** |
| Q42/2 | false | 参考行集 | `year` / `UInt16` / **other**<br>`gross_margin` / `Float64` / **amount** |
| Q43/1 | false | 参考行集 | `region` / `String` / **other**<br>`gross_margin` / `Float64` / **amount** |
| Q43/2 | false | 参考行集 | `region` / `String` / **other**<br>`gross_margin` / `Float64` / **amount** |
| Q44/1 | false | 参考行集 | `year` / `UInt16` / **other**<br>`sales` / `Float64` / **amount**<br>`growth_pct` / `Nullable(Float64)` / **percentage** |
| Q44/2 | false | 参考行集 | `month` / `Date` / **other**<br>`sales` / `Float64` / **amount** |
| Q45/1 | true | 参考行集 | `StoreName` / `String` / **other**<br>`total_sales` / `Float64` / **amount**<br>`SellingAreaSize` / `Nullable(Float64)` / **other**<br>`sales_per_sqft` / `Nullable(Float64)` / **amount** |
| Q46/1 | true | Top-1，键[1] | `segment` / `Nullable(String)` / **other**<br>`profit` / `Float64` / **amount** |
| Q46/2 | true | Top-1，键[1] | `segment` / `Nullable(String)` / **other**<br>`profit` / `Float64` / **amount** |
| Q47/1 | false | 参考行集 | `StoreName` / `String` / **other**<br>`avg_downtime_minutes` / `Nullable(Float64)` / **other** |
| Q48/1 | false | 参考行集 | `downtime_group` / `String` / **other**<br>`avg_sales` / `Float64` / **amount**<br>`store_count` / `UInt64` / **count** [整数守卫] |
| Q48/2 | false | 参考行集 | `correlation` / `Float64` / **ratio** |
| Q48/3 | false | 参考行集 | `correlation` / `Nullable(Float64)` / **ratio** |
| Q49/1 | false | 参考行集 | `e.EntityKey` / `Int32` / **other**<br>`EntityName` / `String` / **other**<br>`total_amount` / `Float64` / **amount** |
| Q50/1 | false | 参考行集 | `sales_2009` / `Float64` / **amount**<br>`sales_2008` / `Float64` / **amount**<br>`growth_pct` / `Float64` / **percentage**<br>`growth_amount` / `Float64` / **amount** |
| Q51/1 | false | 参考行集 | `total_stores` / `UInt64` / **count** [整数守卫] |
| Q52/1 | false | 参考行集 | `max_unit_price` / `Nullable(Float64)` / **amount** |
| Q53/1 | false | 参考行集 | `total_orders` / `UInt64` / **count** [整数守卫] |
| Q54/1 | false | 参考行集 | `total_return_amount` / `Float64` / **amount** |
| Q55/1 | false | 参考行集 | `female_customers` / `UInt64` / **count** [整数守卫] |
| Q56/1 | false | 参考行集 | `avg_yearly_income` / `Nullable(Float64)` / **amount** |
| Q57/1 | false | 参考行集 | `total_brands` / `UInt64` / **count** [整数守卫] |
| Q58/1 | false | 参考行集 | `max_line_sales_amount` / `Float64` / **amount** |
| Q59/1 | false | 参考行集 | `holiday_days` / `UInt64` / **count** [整数守卫] |
| Q60/1 | false | 参考行集 | `production_employees` / `UInt64` / **count** [整数守卫] |
| Q61/1 | false | 参考行集 | `ProductSubcategoryName` / `Nullable(String)` / **other**<br>`total_sales` / `Float64` / **amount** |
| Q62/1 | false | 参考行集 | `BrandName` / `Nullable(String)` / **other**<br>`revenue` / `Float64` / **amount**<br>`units` / `Int64` / **count** [整数守卫] |
| Q63/1 | false | 参考行集 | `Occupation` / `Nullable(String)` / **other**<br>`avg_order_value` / `Nullable(Float64)` / **other**<br>`orders` / `UInt64` / **count** [整数守卫] |
| Q64/1 | false | 参考行集 | `month` / `UInt8` / **other**<br>`gross_margin` / `Float64` / **amount**<br>`margin_pct` / `Nullable(Float64)` / **percentage** |
| Q65/1 | false | 参考行集 | `manager_name` / `Nullable(String)` / **other**<br>`StoreName` / `String` / **other**<br>`total_sales` / `Float64` / **amount** |
| Q66/1 | false | 参考行集 | `quarter` / `UInt8` / **other**<br>`total_discount` / `Float64` / **amount** |
| Q67/1 | true | 参考行集 | `ColorName` / `Nullable(String)` / **other**<br>`avg_realized_price` / `Nullable(Float64)` / **amount**<br>`units` / `Int64` / **count** [整数守卫] |
| Q68/1 | false | 参考行集 | `IsHoliday` / `String` / **other**<br>`orders` / `UInt64` / **count** [整数守卫]<br>`revenue` / `Float64` / **amount** |
| Q69/1 | true | 参考行集 | `PromotionCategory` / `Nullable(String)` / **other**<br>`revenue` / `Float64` / **amount**<br>`total_discount` / `Float64` / **amount**<br>`avg_discount_pct` / `Nullable(Float64)` / **percentage** |
| Q70/1 | false | 参考行集 | `StoreType` / `Nullable(String)` / **other**<br>`revenue` / `Float64` / **amount**<br>`avg_area` / `Nullable(Float64)` / **other**<br>`stores` / `UInt64` / **count** [整数守卫] |
| Q71/1 | false | 1步骤分组选择 | `category` / `Nullable(String)` / **other**<br>`subcategory` / `Nullable(String)` / **other**<br>`sales_amount` / `Float64` / **amount** |
| Q72/1 | false | 参考行集 | `year` / `UInt16` / **other**<br>`quarter` / `UInt8` / **other**<br>`quarterly_sales` / `Float64` / **amount**<br>`cumulative_sales` / `Float64` / **amount** |
| Q73/1 | true | Top-10，键[3] | `ProductName` / `Nullable(String)` / **other**<br>`total_on_hand` / `Int64` / **other**<br>`total_safety` / `Int64` / **other**<br>`gap` / `Int64` / **other** |
| Q74/1 | false | 1步骤分组选择 | `StoreName` / `String` / **other**<br>`ProductName` / `Nullable(String)` / **other**<br>`product_sales` / `Float64` / **amount**<br>`pct_of_store` / `Nullable(Float64)` / **percentage**<br>`ProductKey` / `Int32` / **other** |
| Q75/1 | false | 参考行集 | `FirstName` / `String` / **other**<br>`LastName` / `String` / **other**<br>`spend_2008` / `Float64` / **amount**<br>`spend_2009` / `Float64` / **amount**<br>`pct_growth` / `Nullable(Float64)` / **percentage** |
| Q76/1 | false | 参考行集 | `category` / `Nullable(String)` / **other**<br>`pct_repeat_customer_sales` / `Nullable(Float64)` / **percentage** |
| Q76/2 | false | 参考行集 | `category` / `Nullable(String)` / **other**<br>`pct_repeat_customer_sales` / `Nullable(Float64)` / **percentage** |
| Q77/1 | false | 参考行集 | `month` / `UInt8` / **other**<br>`sales` / `Float64` / **amount**<br>`prev_month_sales` / `Float64` / **amount**<br>`mom_growth_pct` / `Nullable(Float64)` / **percentage** |
| Q78/1 | true | 参考行集 | `category` / `Nullable(String)` / **other**<br>`discount_total` / `Float64` / **amount**<br>`rnk` / `UInt64` / **other**<br>`pct_of_total` / `Nullable(Float64)` / **percentage** |
| Q79/1 | true | Top-10，键[3] | `StoreName` / `String` / **other**<br>`actual_sales` / `Float64` / **amount**<br>`quota` / `Nullable(Float64)` / **amount**<br>`attainment_pct` / `Nullable(Float64)` / **percentage** |
| Q80/1 | false | 参考行集 | `country` / `String` / **other**<br>`n_customers` / `UInt64` / **count** [整数守卫]<br>`avg_active_days` / `Float64` / **other** |
| Q81/1 | false | 参考行集 | `cohort_year` / `UInt16` / **other**<br>`customers_in_cohort` / `UInt64` / **count** [整数守卫]<br>`avg_ltv` / `Float64` / **amount**<br>`total_ltv` / `Float64` / **amount** |
| Q82/1 | false | 参考行集 | `manager_name` / `String` / **other**<br>`Title` / `Nullable(String)` / **other**<br>`direct_reports` / `UInt64` / **count** [整数守卫]<br>`avg_team_tenure_years` / `Nullable(Float64)` / **other** |
| Q83/1 | false | 参考行集 | `cohort_size_2007` / `UInt64` / **count** [整数守卫]<br>`returned_2008` / `UInt64` / **count** [整数守卫]<br>`returned_2008_and_2009` / `UInt64` / **count** [整数守卫] |
| Q84/1 | false | 参考行集 | `abc_class` / `String` / **other**<br>`product_count` / `UInt64` / **count** [整数守卫]<br>`revenue` / `Float64` / **amount**<br>`pct_of_revenue` / `Float64` / **percentage** |
| Q84/2 | false | 参考行集 | `abc_class` / `String` / **other**<br>`product_count` / `UInt64` / **count** [整数守卫]<br>`revenue` / `Float64` / **amount**<br>`pct_of_revenue` / `Float64` / **percentage** |
| Q85/1 | true | 2步骤分组选择 | `bucket` / `String` / **other**<br>`StoreName` / `String` / **other**<br>`actual_amt` / `Float64` / **amount**<br>`quota_amt` / `Nullable(Float64)` / **amount**<br>`attainment_pct` / `Nullable(Float64)` / **percentage** |
| Q86/1 | false | 参考行集 | `ProductSubcategoryName` / `Nullable(String)` / **other**<br>`corr_discount_vs_qty` / `Nullable(Float64)` / **ratio**<br>`observations` / `UInt64` / **count** [整数守卫] |
| Q86/2 | false | 参考行集 | `ProductSubcategoryName` / `Nullable(String)` / **other**<br>`corr_discount_vs_qty` / `Nullable(Float64)` / **ratio**<br>`observations` / `UInt64` / **count** [整数守卫] |
| Q87/1 | true | Top-20，键[3] | `ProductName` / `Nullable(String)` / **other**<br>`on_hand` / `Int64` / **other**<br>`avg_daily_qty` / `Float64` / **other**<br>`days_of_coverage` / `Float64` / **other**<br>`ProductKey` / `Int32` / **other** |
| Q88/1 | true | Top-20，键[1] | `customer_name` / `String` / **other**<br>`total_spend_2009` / `Float64` / **amount** |
| Q89/1 | false | 参考行集 | `segment` / `String` / **other**<br>`customers` / `UInt64` / **count** [整数守卫]<br>`avg_spend` / `Float64` / **amount**<br>`avg_distinct_products` / `Float64` / **other** |
| Q90/1 | false | 参考行集 | `category` / `Nullable(String)` / **other**<br>`margin_2007_pct` / `Nullable(Float64)` / **percentage**<br>`margin_2008_pct` / `Nullable(Float64)` / **percentage**<br>`margin_2009_pct` / `Nullable(Float64)` / **percentage**<br>`delta_08_07_pp` / `Nullable(Float64)` / **percentage**<br>`delta_09_08_pp` / `Nullable(Float64)` / **percentage** |
| Q91/1 | false | 参考行集 | `income_spend_correlation` / `Nullable(Float64)` / **ratio**<br>`customers_analyzed` / `UInt64` / **count** [整数守卫] |
| Q91/2 | false | 参考行集 | `income_spend_correlation` / `Nullable(Float64)` / **ratio**<br>`customers_analyzed` / `UInt64` / **count** [整数守卫] |
| Q92/1 | true | 参考行集 | `BrandName` / `Nullable(String)` / **other**<br>`revenue` / `Float64` / **amount**<br>`gross_margin_dollars` / `Float64` / **amount**<br>`gross_margin_pct` / `Nullable(Float64)` / **percentage** |
| Q93/1 | false | 参考行集 | `discount_qty_correlation` / `Nullable(Float64)` / **ratio**<br>`discount_revenue_correlation` / `Nullable(Float64)` / **ratio**<br>`promos_analyzed` / `UInt64` / **count** [整数守卫] |
| Q94/1 | true | 参考行集 | `StoreName` / `String` / **other**<br>`q3_sales` / `Float64` / **amount**<br>`q4_sales` / `Float64` / **amount**<br>`qoq_pct_change` / `Nullable(Float64)` / **percentage** |
| Q95/1 | false | 参考行集 | `ProductCategoryName` / `Nullable(String)` / **other**<br>`promo_average_sales` / `Float64` / **amount**<br>`full_price_average_sales` / `Float64` / **amount**<br>`incremental_average_sales` / `Float64` / **amount** |
| Q96/1 | false | 参考行集 | `cohort_year` / `UInt16` / **other**<br>`cohort_size` / `UInt64` / **count** [整数守卫]<br>`returning_customers` / `UInt64` / **count** [整数守卫]<br>`retention_pct` / `Float64` / **percentage** |
| Q97/1 | true | 参考行集 | `ProductName` / `Nullable(String)` / **other**<br>`h1_sales` / `Float64` / **amount**<br>`h2_sales` / `Float64` / **amount**<br>`h2_vs_h1_pct` / `Nullable(Float64)` / **percentage**<br>`ProductKey` / `Int32` / **other** |
| Q97/2 | true | 参考行集 | `ProductKey` / `Int32` / **other**<br>`ProductName` / `Nullable(String)` / **other**<br>`h1_sales` / `Float64` / **amount**<br>`h2_sales` / `Float64` / **amount**<br>`sales_increase` / `Float64` / **amount** |
| Q98/1 | true | 1步骤分组选择 | `ProductCategoryName` / `Nullable(String)` / **other**<br>`peak_quarter_share_pct` / `Float64` / **percentage**<br>`peak_quarter` / `UInt8` / **other** |
| Q98/2 | true | 1步骤分组选择 | `ProductCategoryName` / `Nullable(String)` / **other**<br>`year` / `UInt16` / **other**<br>`peak_quarter_share_pct` / `Float64` / **percentage**<br>`peak_quarter` / `UInt8` / **other** |
| Q99/1 | false | 参考行集 | `ProductCategoryName` / `Nullable(String)` / **other**<br>`avg_weekend_day_sales` / `Float64` / **amount**<br>`avg_weekday_sales` / `Float64` / **amount**<br>`weekend_lift_pct` / `Nullable(Float64)` / **percentage**<br>`weekend_difference_amount` / `Float64` / **amount** |
| Q100/1 | false | 参考行集 | `customer_name` / `String` / **other**<br>`orders` / `UInt64` / **count** [整数守卫]<br>`avg_order_amount` / `Float64` / **amount**<br>`lifetime_value` / `Float64` / **amount** |

合计：100题、113份参考；ordered=true共21份；分组选择6份参考；整数计数守卫43列。

Q33/Q45/Q97等judge题的示例截断不自动成为题干固定N；维持已批准的声明口径与非封闭示例，不将示例LIMIT伪装成新增的题意限制。

类型来源：直接查询列取引擎返回元数据；Q74等后处理保留对应投影类型。Q84的abc_groups会生成新输出列，表中类型沿用T04已批准的正式后处理schema，不是原始聚合域的列类型；T05b须同时独立核对这一输出schema。

冻结前仍需：用户审阅本表；T05b独立核对返回类型、量纲、排序、完整边界及已披露的参考修复。Q79以当前参考推导的边界成员集合及规则版本为准；2026-10-16 T05b差异裁决已确认独立成员集合一致并放行，旧306成员仅为历史工件，不是现行门禁。
