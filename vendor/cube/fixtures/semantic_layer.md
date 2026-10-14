# Retail Semantic Layer

Analyst guide to the Contoso retail dataset. Use this as authoritative business-semantic context when writing SQL. The raw DDL below supplies column types; this doc supplies *what the columns mean* and *which ones to use for which question*.

## Fact tables — pick the right one

| Question contains | Use table | Reason |
|---|---|---|
| "online", unqualified "sales"/"orders"/"returns"/"discount"/"revenue" | `retail.FactOnlineSales` | **DEFAULT for any sales question.** Online-channel only. |
| "all channels", "in-store", "across channels", "store vs online" | `retail.FactSales` | Multi-channel (in-store + online + catalog + reseller). |
| Current inventory, stock levels, on-hand, safety stock | `retail.FactInventory` | **SNAPSHOT data** — see caveat below. |
| Budget vs actual, forecast, plan, scenario comparison | `retail.FactStrategyPlan` | Uses `ScenarioKey` (1=Actual, 2=Budget, 3=Forecast) and `AccountKey` (filter for the relevant account). |
| IT outages, downtime, SLA | `retail.FactITSLA` | Joins to `DimMachine` and `DimOutage`. |
| Exchange rates, FX | `retail.FactExchangeRate` | **Note:** `CurrencyKey` here is the TARGET currency key. `FactOnlineSales` is all USD (`CurrencyKey=1`). |

### Sales-table convention (critical)

Unqualified questions like *"show total sales"*, *"sales by category"*, *"quarterly sales"*, *"return rate"*, *"customer purchases"* default to **`FactOnlineSales`**, not `FactSales`. `FactSales` is reserved for explicit all-channel / in-store / cross-channel comparisons.

## Snapshot caveat — FactInventory

`FactInventory` contains daily snapshots per (product, store). Summing `OnHandQuantity` across dates is meaningless.

For "current inventory", "products below safety stock", "stock levels":
```sql
WITH latest AS (
  SELECT StoreKey, ProductKey, MAX(DateKey) AS max_date
  FROM retail.FactInventory
  GROUP BY StoreKey, ProductKey
)
SELECT ...
FROM retail.FactInventory i
JOIN latest ON i.StoreKey = latest.StoreKey
           AND i.ProductKey = latest.ProductKey
           AND i.DateKey = latest.max_date
```

## String-boolean quirks

The dataset uses string enums where you'd expect booleans. Always filter on the string value.

| Column | Values | Use |
|---|---|---|
| `DimEmployee.IsSalesPerson` | `'Yes'` / `'No'` | Filter to `'Yes'` for salespeople. |
| `DimDate.IsWorkDay` | `'WorkDay'` / `'WeekEnd'` | For weekday/weekend splits. |
| `DimDate.IsHoliday` | `'Yes'` / `'No'` | For holiday vs non-holiday. |
| `DimCustomer.Gender` | `'M'` / `'F'` | Single-character. |
| `DimCustomer.MaritalStatus` | `'M'` / `'S'` | M=Married, S=Single. |

## Implicit defaults

| Foreign key / value | Meaning |
|---|---|
| `PromotionKey = 1` | **"No Discount"** — exclude for "discount amount by promotion" questions. |
| `CurrencyKey = 1` | USD (base currency in `FactOnlineSales`). |
| `ScenarioKey = 1` in FactStrategyPlan | Actual |
| `ScenarioKey = 2` in FactStrategyPlan | Budget |
| `ScenarioKey = 3` in FactStrategyPlan | Forecast |
| `AccountKey = 50` in FactStrategyPlan | Sales Amount account. |

## Hierarchies

- **Product**: `DimProduct.ProductSubcategoryKey` → `DimProductSubcategory.ProductCategoryKey` → `DimProductCategory.ProductCategoryName`
- **Employee**: self-join on `DimEmployee.ParentEmployeeKey` (manager → direct report)
- **Entity**: recursive self-join on `DimEntity.ParentEntityKey` (organizational roll-up; terminate when ParentEntityKey IS NULL)
- **Account**: self-join on `DimAccount.ParentAccountKey`
- **Geography**: `DimGeography.CityName` → `StateProvinceName` → `RegionCountryName` → `ContinentName`

## Joining to geography

For "sales by region / country / continent":
- Default: **customer geography** — `FactOnlineSales.CustomerKey` → `DimCustomer.GeographyKey` → `DimGeography`
- Only use **store geography** (`FactOnlineSales.StoreKey` → `DimStore.GeographyKey`) when the question says "store location" explicitly.

## Key calculated metrics

### Catalog price and margin (from DimProduct)
- **Unit price** (list price): `DimProduct.UnitPrice`. Use for *"most expensive"*, *"top products by price"*.
- **Unit cost**: `DimProduct.UnitCost`.
- **Profit margin %** (catalog): `(UnitPrice - UnitCost) * 100.0 / nullif(UnitPrice, 0)`.
- Never derive unit price from `sum(SalesAmount)/sum(SalesQuantity)` — that's avg-realized price and differs from list.

### Sales-derived metrics
- **Gross margin $**: `sum(SalesAmount) - sum(TotalCost)` on the sales fact.
- **Gross margin %**: `(sum(SalesAmount) - sum(TotalCost)) / nullif(sum(SalesAmount), 0)`.
- **Return rate**: `sum(ReturnQuantity) / nullif(sum(SalesQuantity), 0)` — express as percentage in presentation.
- **Average order value**: `sum(SalesAmount) / nullif(countDistinct(SalesOrderNumber), 0)`.

### Customer cohort / recency
Dataset's latest date is **2009-12-31**. Compute against that date, not `today()`.

- **First purchase date (cohort)**: `(SELECT MIN(DateKey) FROM retail.FactOnlineSales WHERE CustomerKey = c.CustomerKey)`
- **Years active**: `(SELECT count(distinct toYear(DateKey)) FROM retail.FactOnlineSales WHERE CustomerKey = c.CustomerKey)` — 1, 2, or 3.
- **Months since last purchase**: `dateDiff('month', (SELECT MAX(DateKey) FROM retail.FactOnlineSales WHERE CustomerKey = c.CustomerKey), toDate('2009-12-31'))`
- **Recency segment**:
  - `<= 6` months → `'Active'`
  - `7..12` months → `'At Risk'`
  - `> 12` months → `'Churned'`

### Same-store YoY growth
For "same-store sales growth" or "comparable-store sales": compute ONE scalar % change, restricted to stores that had sales in BOTH compared years.

```sql
WITH cy AS (SELECT toYear(MAX(DateKey)) FROM retail.FactSales),  -- typically 2009
     py AS (cy - 1),
     same_stores AS (
       SELECT StoreKey FROM retail.FactSales WHERE toYear(DateKey) = cy
       INTERSECT
       SELECT StoreKey FROM retail.FactSales WHERE toYear(DateKey) = py
     )
SELECT (
  sumIf(SalesAmount, toYear(DateKey) = cy AND StoreKey IN same_stores)
  - sumIf(SalesAmount, toYear(DateKey) = py AND StoreKey IN same_stores)
) * 100.0 / nullif(sumIf(SalesAmount, toYear(DateKey) = py AND StoreKey IN same_stores), 0)
FROM retail.FactSales
```

### Inventory turnover
Standard retail formula: `COGS / average inventory value` over the period.
- COGS = `sum(TotalCost)` from the sales fact joined by (DateKey, ProductKey, StoreKey).
- Avg inventory value = `avg(OnHandQuantity * UnitCost)` on `FactInventory` joined to `DimProduct.UnitCost`.
- Higher turnover = faster-moving stock.

## Agent steering rules (critical — these cause failure if ignored)

1. **"Total X"** with no grouping → return **a single row** aggregate. Do NOT add `GROUP BY year` unless the question says "by year".
2. **"How many unique customers"** → return a SINGLE scalar via `countDistinct(CustomerKey)`. Never group by year; customer counts across years don't sum (customers overlap).
3. **"Top N"** → `ORDER BY <metric> DESC LIMIT N`.
4. **Per-customer / per-product / per-store** questions → `GROUP BY <entity>Key` + name columns only. Do **NOT** segment by geography or demographics unless the question explicitly asks for segments.
5. **"Most expensive" / "top by price"** → use `DimProduct.UnitPrice` (catalog), never derive from sales.
6. **"Current inventory / stock levels"** → use MAX(DateKey) pattern, never `sum(OnHandQuantity)` across dates.
7. **"Last quarter" / "previous quarter"** → interpret as **Q4 2009** (the dataset's final quarter). Do NOT use `today()` or `ORDER BY DESC LIMIT 1`.
8. **"First purchase" / "new customer cohort"** → use `MIN(DateKey) per CustomerKey`, not `count per quarter` of all customers.
9. **"Classify as Active/AtRisk/Churned"** → use the recency-segment formula above (monthly, not yearly).
10. **"Weekend vs weekday percentage"** → compute the split as a percentage column, not just raw amounts.
11. **"Holidays vs regular days"** → compute **average daily sales** per bucket (day_total = sum per day, then avg across days), not average per transaction.
12. **"By region / country / continent"** for sales → customer geography by default (see Joining to geography above).
13. **"Profit margin"** on products → catalog margin from `DimProduct.UnitPrice`/`UnitCost`, not sales-avg.

## Time dimension helpers

- `DimDate.CalendarYear`, `CalendarMonth`, `CalendarQuarter`, `CalendarMonthLabel` ("January"…), `CalendarQuarterLabel` ("Q1"…)
- `DimDate.IsWorkDay` ("WorkDay"/"WeekEnd"), `IsHoliday` ("Yes"/"No")
- `DimDate.NorthAmericaSeason` (Winter/Spring/Summer/Fall/Back to School/etc.) for season-based splits

## Notes on specific tables

- `DimPromotion.PromotionName` + `PromotionCategory` — for "discount by promotion type", group by category.
- `DimStore.SellingAreaSize` — square footage.
- `DimStore.StoreType` — "Store" vs other categories.
- `DimSalesTerritory.SalesTerritoryCountry` / `SalesTerritoryRegion`.
- `FactITSLA.DownTime` in minutes.
- `DimMachine.MachineType` / `MachineClass` / `Status`.
