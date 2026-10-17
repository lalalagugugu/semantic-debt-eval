"""T05b: independent pandas recomputation of every reference answer.

Written from the question text, scoring_notes, accepted interpretations, the
frozen conventions (semantic/conventions.md) and the user rulings only. It never
reads the `sql` fields, refs/, build_refs.py or the harness selector.

Rulings applied (main repo decisions/, 2026-10-16):
  * reference-inner-join-undercount: compute the business answer; facts are
    LEFT-joined to DimProduct, missing products keep their ProductKey with a
    NULL name/category, totals and denominators come from the full fact table.
  * return-only-rows-and-purchase-events, as superseded by
    2026-10-17-one-convention-one-answer: every online row of a customer,
    return-only rows included, is a transaction (first/last purchase, new
    customers, recency, order counts); order denominators use all order numbers.
  * one-convention-one-answer: one answer per convention. New-customer window
    is [cutoff - 89 days, cutoff] (semantic layer); the empty product-group row
    is always kept.
  * grouped/nested Top-N (BOARD items 3, 4) and Q79: selection is implemented
    here (strict prefix + complete boundary on quantized keys).

Usage:
  uv run python scripts/recheck_pandas.py --eval-dir "$SEMDEBT_DATA_DIR/eval-ro-dd5853d"
  uv run python scripts/recheck_pandas.py --only Q74,Q79
Outputs go to reports/T05b/pandas/: one CSV per question/interpretation
(Qxx-k.csv) and manifest.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("SEMDEBT_DATA_DIR", ROOT.parent / "data")) / "parquet"
if not DATA.exists():
    DATA = Path("/Users/yuhuang/dev/semdebt/data/parquet")
OUT = ROOT / "reports" / "T05b" / "pandas"

TODAY = pd.Timestamp("2009-12-31")


# --------------------------------------------------------------------------
# Quantization (same policy as harness/value_units.py, reimplemented here):
# Decimal of the repr string, ROUND_HALF_EVEN; amount 2 dp; percentage /100
# then 6 dp; ratio and everything else 6 dp.
# --------------------------------------------------------------------------
def q(value, kind="other"):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        raise ValueError("selection keys must be finite")
    if isinstance(value, (np.integer,)):
        value = int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    number = Decimal(str(value))
    with localcontext() as ctx:
        ctx.prec = max(50, len(number.as_tuple().digits) + abs(number.adjusted()) + 10)
        if kind == "percentage":
            number /= Decimal(100)
        quantum = Decimal("0.01") if kind == "amount" else Decimal("0.000001")
        return number.quantize(quantum, rounding=ROUND_HALF_EVEN)


def select_top(df, group_cols, order, n):
    """Per group: strict prefix + complete boundary on quantized order keys.

    order: list of (column, kind, descending). Rows with NULL keys are outside
    the domain. Each row is one object (callers aggregate to object grain first).
    """
    cols = [c for c, _, _ in order]
    df = df.dropna(subset=cols).copy()
    keys = []
    for c, kind, desc in order:
        qc = df[c].map(lambda v, k=kind: q(v, k))
        df[f"__k_{c}"] = qc if not desc else qc.map(lambda d: -d)
        keys.append(f"__k_{c}")
    parts = []
    groups = [((), df)] if not group_cols else df.groupby(group_cols, dropna=False, sort=False)
    for _, g in groups:
        g = g.sort_values(keys, kind="mergesort")
        if len(g) <= n:
            parts.append(g)
            continue
        boundary = tuple(g.iloc[n - 1][keys])
        tup = list(zip(*[g[k] for k in keys]))
        parts.append(g[[t <= boundary for t in tup]])
    out = pd.concat(parts) if parts else df.iloc[:0]
    return out.drop(columns=keys)


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------
@lru_cache(None)
def T(name):
    df = pd.read_parquet(DATA / f"{name}.parquet")
    if "DateKey" in df.columns:
        df["DateKey"] = pd.to_datetime(df["DateKey"])
    return df


@lru_cache(None)
def prod():
    p = T("DimProduct").copy()
    sc = T("DimProductSubcategory")
    pc = T("DimProductCategory")
    p["ProductSubcategoryKey"] = p["ProductSubcategoryKey"].astype("Int64")
    p = p.merge(sc, on="ProductSubcategoryKey", how="left").merge(pc, on="ProductCategoryKey", how="left")
    return p.set_index("ProductKey")


def attach_product(df, cols=("ProductCategoryName",)):
    """LEFT join product attributes; orphan ProductKeys get NULL attributes."""
    p = prod()
    for c in cols:
        df[c] = df["ProductKey"].map(p[c])
    return df


@lru_cache(None)
def fos():
    cols = ["DateKey", "StoreKey", "ProductKey", "PromotionKey", "CustomerKey", "SalesOrderNumber",
            "SalesQuantity", "SalesAmount", "ReturnQuantity", "ReturnAmount", "DiscountAmount",
            "TotalCost", "UnitPrice"]
    df = pd.read_parquet(DATA / "FactOnlineSales.parquet", columns=cols)
    df["DateKey"] = pd.to_datetime(df["DateKey"])
    df["order"] = pd.factorize(df["SalesOrderNumber"])[0].astype(np.int32)
    df = df.drop(columns=["SalesOrderNumber"])
    df["year"] = df.DateKey.dt.year.astype(np.int16)
    df["month"] = df.DateKey.dt.month.astype(np.int8)
    df["quarter"] = df.DateKey.dt.quarter.astype(np.int8)
    return df


def buys():
    """Online rows that count as purchase events: every row, return-only rows included."""
    return fos()


@lru_cache(None)
def fs():
    cols = ["DateKey", "channelKey", "StoreKey", "ProductKey", "PromotionKey", "SalesQuantity",
            "SalesAmount", "TotalCost", "DiscountAmount", "ReturnAmount", "ReturnQuantity"]
    df = pd.read_parquet(DATA / "FactSales.parquet", columns=cols)
    df["DateKey"] = pd.to_datetime(df["DateKey"])
    df["year"] = df.DateKey.dt.year.astype(np.int16)
    df["month"] = df.DateKey.dt.month.astype(np.int8)
    df["quarter"] = df.DateKey.dt.quarter.astype(np.int8)
    return df


@lru_cache(None)
def cust():
    c = T("DimCustomer").merge(T("DimGeography"), on="GeographyKey", how="left")
    return c.set_index("CustomerKey")


@lru_cache(None)
def dates():
    return T("DimDate").set_index("DateKey")


@lru_cache(None)
def stores():
    return T("DimStore").set_index("StoreKey")


@lru_cache(None)
def current_inventory():
    """Latest snapshot per store x product (convention 11)."""
    inv = pd.read_parquet(DATA / "FactInventory.parquet",
                          columns=["DateKey", "StoreKey", "ProductKey", "OnHandQuantity", "SafetyStockQuantity"])
    inv["DateKey"] = pd.to_datetime(inv["DateKey"])
    last = inv.groupby(["StoreKey", "ProductKey"]).DateKey.transform("max")
    cur = inv[inv.DateKey == last]
    assert not cur.duplicated(["StoreKey", "ProductKey"]).any()
    return cur.reset_index(drop=True)


def first_last():
    """Per customer: first and last purchase date (active purchase algorithm)."""
    b = buys()
    return b.groupby("CustomerKey").DateKey.agg(first="min", last="max")


def pct(a, b):
    a = pd.Series(a, dtype=float) if not isinstance(a, (pd.Series, float, int, np.floating)) else a
    with np.errstate(divide="ignore", invalid="ignore"):
        r = a / b * 100.0
    if isinstance(r, pd.Series):
        return r.where(np.isfinite(r))
    return r if np.isfinite(r) else np.nan


def full_name(e, key):
    return (e.loc[key, "FirstName"] + " " + e.loc[key, "LastName"]) if key in e.index else None


def spearman(a, b):
    """Spearman rho: Pearson on average ranks (ties share the mean rank), pairwise-complete."""
    d = pd.DataFrame({"a": np.asarray(a, float), "b": np.asarray(b, float)}).dropna()
    return d.a.rank().corr(d.b.rank())


def df_(rows, columns):
    return pd.DataFrame(rows, columns=columns)


def months_between(later, earlier):
    """Calendar-month difference (convention 13 recency in months)."""
    return (later.dt.year * 12 + later.dt.month) - (earlier.dt.year * 12 + earlier.dt.month)


SEGMENTS = ("活跃", "有流失风险", "已流失")


def segment(m):
    """Convention 13 recency segments, labelled with the business terms the questions use."""
    return np.where(m <= 6, SEGMENTS[0], np.where(m <= 12, SEGMENTS[1], SEGMENTS[2]))


QS = {}          # qid -> function returning list of DataFrames (one per ref, in order)
EVENT = set()    # qids that define purchase events (informational since 2026-10-17)


def Q(qid, event=False):
    def deco(fn):
        QS[qid] = fn
        if event:
            EVENT.add(qid)
        return fn
    return deco


# --------------------------------------------------------------------------
# Q01-Q100 (vendored, Chinese-adapted)
# --------------------------------------------------------------------------
@Q("Q01")
def _():
    return [df_([[T("DimProduct").ProductKey.nunique()]], ["product_count"])]


@Q("Q02")
def _():
    return [df_([[fos().SalesAmount.sum()]], ["total_sales"])]


@Q("Q03", event=True)
def _():
    return [df_([[buys().CustomerKey.nunique()]], ["customers"])]


@Q("Q04")
def _():
    p = T("DimProduct")
    return [p.loc[p.BrandName == "Contoso", ["ProductName"]]]


@Q("Q05")
def _():
    p = prod().reset_index()
    g = p.groupby("ProductCategoryName", dropna=False).ProductKey.nunique().reset_index()
    return [g.rename(columns={"ProductKey": "product_count"})]


@Q("Q06")
def _():
    f = fos()
    return [df_([[f.loc[f.year == 2009, "SalesAmount"].sum()]], ["sales_2009"])]


@Q("Q07")
def _():
    p = T("DimProduct")[["ProductName", "UnitPrice"]]
    top = select_top(p, [], [("UnitPrice", "amount", True)], 10)
    return [top.sort_values("UnitPrice", ascending=False)]


@Q("Q08")
def _():
    e = T("DimEmployee")
    return [e.loc[e.IsSalesPerson == "Yes", ["FirstName", "LastName"]]]


@Q("Q09")
def _():
    return [df_([[T("DimProduct").UnitCost.mean()]], ["avg_unit_cost"])]


@Q("Q10")
def _():
    s = T("DimStore")
    return [df_([[int((s.Status == "On").sum())]], ["stores"])]


@Q("Q11")
def _():
    f = attach_product(fos()[["ProductKey", "SalesAmount"]].copy())
    return [f.groupby("ProductCategoryName", dropna=False).SalesAmount.sum().reset_index()]


@Q("Q12")
def _():
    f = fos()
    return [f[f.year == 2008].groupby("month").SalesAmount.sum().reset_index()]


@Q("Q13")
def _():
    # All-channel sales by store; average unit price = sales / quantity (metrics.yaml).
    g = fs().groupby("StoreKey")[["SalesAmount", "SalesQuantity"]].sum()
    return [pd.DataFrame({"StoreKey": g.index, "StoreName": g.index.map(stores().StoreName), "sales": g.SalesAmount.values,
                          "avg_unit_price": (g.SalesAmount / g.SalesQuantity.where(g.SalesQuantity != 0)).values,
                          "quantity": g.SalesQuantity.values})]


@Q("Q14")
def _():
    s = fos().groupby("CustomerKey").SalesAmount.sum()
    return [df_([[int((s > 100000).sum())]], ["customers"])]


@Q("Q15")
def _():
    f = fos()
    s = f.groupby("CustomerKey").SalesAmount.sum()
    country = s.index.map(cust().RegionCountryName)
    return [s.groupby(country, dropna=False).sum().rename_axis("country").reset_index()]


@Q("Q16")
def _():
    f = fos()
    return [f[f.year.isin([2008, 2009])].groupby("year").SalesAmount.sum().reset_index()]


@Q("Q17")
def _():
    f = fos()
    lab = f.DateKey.map(dates().IsWorkDay)
    g = f.groupby(lab).SalesAmount.sum()
    return [pd.DataFrame({"day_type": g.index, "sales": g.values, "pct": pct(g.values, g.sum())})]


@Q("Q18")
def _():
    f = fos()
    f = f[f.PromotionKey != 1]
    lab = f.PromotionKey.map(T("DimPromotion").set_index("PromotionKey").PromotionType)
    return [f.groupby(lab).DiscountAmount.sum().reset_index()]


@Q("Q19")
def _():
    f = fos()
    gender = f.CustomerKey.map(cust().Gender)
    g = f.groupby(gender).agg(s=("SalesAmount", "sum"), o=("order", "nunique"))
    return [pd.DataFrame({"gender": g.index, "aov": g.s / g.o})]


@Q("Q20")
def _():
    cur = current_inventory()
    g = cur.groupby("ProductKey")[["OnHandQuantity", "SafetyStockQuantity"]].sum().reset_index()
    g = g[g.OnHandQuantity < g.SafetyStockQuantity]
    return [pd.DataFrame({"ProductKey": g.ProductKey, "ProductName": g.ProductKey.map(prod().ProductName),
                          "OnHand": g.OnHandQuantity, "Safety": g.SafetyStockQuantity})]


@Q("Q21")
def _():
    g = current_inventory().groupby("StoreKey").OnHandQuantity.sum()
    return [pd.DataFrame({"StoreKey": g.index, "StoreName": g.index.map(stores().StoreName), "OnHand": g.values})]


@Q("Q22")
def _():
    s = fos().groupby("CustomerKey").SalesAmount.sum().reset_index()
    c = cust()
    s["FirstName"] = s.CustomerKey.map(c.FirstName)
    s["LastName"] = s.CustomerKey.map(c.LastName)
    s["country"] = s.CustomerKey.map(c.RegionCountryName)
    s["qk"] = s.SalesAmount.map(lambda v: q(v, "amount"))
    s["rank"] = s.groupby("country").qk.rank(method="min", ascending=False).astype(int)
    top = select_top(s, ["country"], [("SalesAmount", "amount", True)], 5)
    return [top[["CustomerKey", "FirstName", "LastName", "country", "SalesAmount", "rank"]]]


@Q("Q23")
def _():
    f = fos()
    g = f[f.year == 2009].groupby("month").SalesAmount.sum().reset_index()
    g["cumulative"] = g.SalesAmount.cumsum()
    return [g]


@Q("Q24")
def _():
    f = attach_product(fos()[["ProductKey", "SalesQuantity", "ReturnQuantity"]].copy())
    g = f.groupby("ProductCategoryName", dropna=False)[["SalesQuantity", "ReturnQuantity"]].sum().reset_index()
    g["return_rate_pct"] = pct(g.ReturnQuantity, g.SalesQuantity)
    return [g]


@Q("Q25")
def _():
    f = fos()
    na = f.CustomerKey.map(cust().ContinentName) == "North America"
    daily = f[na].groupby("DateKey").SalesAmount.sum()
    season = daily.index.map(dates().NorthAmericaSeason)
    g = daily.groupby(season).mean().rename_axis("season").reset_index(name="avg_daily_sales")
    return [select_top(g, [], [("avg_daily_sales", "amount", True)], 1)]


@Q("Q26", event=True)
def _():
    fl = first_last()
    f07 = fl[fl["first"].dt.year == 2007]["first"]
    g = f07.dt.quarter.value_counts().sort_index()
    return [pd.DataFrame({"quarter": g.index, "customers": g.values})]


@Q("Q27")
def _():
    p = T("DimProduct")[["ProductName", "UnitPrice", "UnitCost"]].copy()
    p["margin_pct"] = pct(p.UnitPrice - p.UnitCost, p.UnitPrice)
    top = select_top(p, [], [("margin_pct", "percentage", True)], 10)
    return [top.sort_values("margin_pct", ascending=False)]


@Q("Q28")
def _():
    f = fs()
    ch = f.channelKey.map(T("DimChannel").set_index("ChannelKey").ChannelName)
    g = f[ch.isin(["Store", "Online"])].groupby(ch)[["SalesAmount", "SalesQuantity"]].sum()
    return [pd.DataFrame({"channel": g.index, "avg_unit_price": (g.SalesAmount / g.SalesQuantity).values})]


def _daily_type_compare(f, label_col, a, b):
    daily = f.groupby("DateKey").SalesAmount.sum()
    lab = daily.index.map(dates()[label_col])
    m = daily.groupby(lab).mean()
    return (m[a] / m[b] - 1) * 100


@Q("Q29")
def _():
    return [df_([[_daily_type_compare(fos(), "IsHoliday", "Yes", "No")]], ["pct_diff"])]


@Q("Q30")
def _():
    f = fos()
    d = f[(f.year == 2009) & (f.month == 12)].groupby("DateKey").SalesAmount.sum().sort_index()
    return [pd.DataFrame({"date": d.index.date, "sales": d.values, "ma7": d.rolling(7, min_periods=1).mean().values})]


def _plan(year=None, scenarios=(1, 2)):
    sp = T("FactStrategyPlan")
    sp = sp[(sp.AccountKey == 4) & sp.ScenarioKey.isin(scenarios)]
    if year:
        sp = sp[sp.DateKey.dt.year == year]
    sp = sp.assign(category=sp.ProductCategoryKey.map(T("DimProductCategory").set_index("ProductCategoryKey").ProductCategoryName))
    return sp


@Q("Q31")
def _():
    sp = _plan(2009)
    g = sp.pivot_table(index="category", columns="ScenarioKey", values="Amount", aggfunc="sum")
    return [pd.DataFrame({"category": g.index, "actual": g[1].values, "budget": g[2].values})]


@Q("Q32", event=True)
def _():
    b = buys()
    yrs = b.groupby("CustomerKey").year.nunique()
    keys = yrs[yrs == 3].index
    ltv = fos().groupby("CustomerKey").SalesAmount.sum()
    return [df_([[len(keys), ltv.reindex(keys).sum()]], ["customers", "lifetime_value"])]


@Q("Q33", event=True)
def _():
    b = buys()[["order", "ProductKey"]].drop_duplicates()
    b = b.sort_values(["order", "ProductKey"])
    m = b.merge(b, on="order")
    m = m[m.ProductKey_x < m.ProductKey_y]
    g = m.groupby(["ProductKey_x", "ProductKey_y"]).size().sort_values(ascending=False)
    g = g.reset_index(name="orders")
    g = g[g.orders >= g.orders.iloc[min(99, len(g) - 1)]]  # top 100 pairs plus ties
    p = prod().ProductName
    return [pd.DataFrame({"product_a": g.ProductKey_x.map(p), "product_b": g.ProductKey_y.map(p), "orders": g.orders,
                          "key_a": g.ProductKey_x, "key_b": g.ProductKey_y})]


@Q("Q34")
def _():
    f = fos()
    cogs = f[f.year == 2009].groupby("ProductKey").TotalCost.sum()
    inv = pd.read_parquet(DATA / "FactInventory.parquet", columns=["DateKey", "ProductKey", "OnHandQuantity", "UnitCost"])
    inv["DateKey"] = pd.to_datetime(inv["DateKey"])
    inv = inv[inv.DateKey.dt.year == 2009]
    inv["value"] = inv.OnHandQuantity * inv.UnitCost
    per_date = inv.groupby(["ProductKey", "DateKey"]).value.sum()
    avg_inv = per_date.groupby("ProductKey").mean()
    d = pd.DataFrame({"cogs": cogs, "avg_inventory": avg_inv}).dropna(subset=["cogs"])
    d["turnover"] = d.cogs / d.avg_inventory
    d["turnover"] = d.turnover.where(np.isfinite(d.turnover))
    d.insert(0, "ProductName", d.index.map(prod().ProductName))
    d["ProductKey"] = d.index
    return [d.reset_index(drop=True)]


@Q("Q35")
def _():
    e = T("DimEmployee").set_index("EmployeeKey")
    m = e.ParentEmployeeKey.astype("Int64")
    return [pd.DataFrame({"FirstName": e.FirstName, "LastName": e.LastName, "Title": e.Title,
                          "ManagerFirstName": m.map(e.FirstName), "ManagerLastName": m.map(e.LastName)})]


@Q("Q36", event=True)
def _():
    fl = first_last()
    seg = pd.Series(segment(months_between(pd.Series(TODAY, index=fl.index), fl["last"])))
    g = seg.value_counts().reindex(SEGMENTS, fill_value=0)
    return [pd.DataFrame({"segment": g.index, "customers": g.values})]


@Q("Q37")
def _():
    g = fs().groupby("StoreKey").SalesAmount.sum()
    r = (g.rank(method="min") - 1) / (len(g) - 1)
    return [pd.DataFrame({"StoreName": g.index.map(stores().StoreName), "sales": g.values, "pct_rank": r.values * 100})]


@Q("Q38")
def _():
    sp = _plan(2009, (1, 3))
    sp = sp[sp.DateKey.dt.quarter == 4]
    g = sp.pivot_table(index="category", columns="ScenarioKey", values="Amount", aggfunc="sum")
    acc = (1 - (g[1] - g[3]).abs() / g[1]) * 100
    return [pd.DataFrame({"category": g.index, "forecast": g[3].values, "actual": g[1].values, "accuracy_pct": acc.values})]


@Q("Q39")
def _():
    p = prod().reset_index()
    p["avail"] = pd.to_datetime(p.AvailableForSaleDate)
    new = p[p.avail.dt.year.isin([2008, 2009])]
    first_new = new.groupby("ProductSubcategoryKey").avail.min()
    f = fos()
    lo, hi = f.DateKey.min(), f.DateKey.max()
    rows, rows90 = [], []
    for sk, launch in first_new.items():
        old_keys = p[(p.ProductSubcategoryKey == sk) & (p.avail < pd.Timestamp("2008-01-01"))].ProductKey
        w = min((launch - lo).days, (hi - launch).days + 1)
        if w <= 0:
            rows.append([sk, p.loc[p.ProductSubcategoryKey == sk, "ProductSubcategoryName"].iloc[0], launch.date(), None, None, None])
            continue
        sub = f[f.ProductKey.isin(old_keys)]
        name = p.loc[p.ProductSubcategoryKey == sk, "ProductSubcategoryName"].iloc[0]
        rows.append([sk, name, launch.date(), w] + _before_after(sub, launch, w))
        # Reading 2: 90 days on each side; NULL when the data does not cover the whole window.
        covered = launch - pd.Timedelta(days=90) >= lo and launch + pd.Timedelta(days=89) <= hi
        rows90.append([sk, name, launch.date(), 90] + (_before_after(sub, launch, 90) if covered else [None, None]))
    cols = ["ProductSubcategoryKey", "subcategory", "first_new_launch", "window_days", "old_daily_before", "old_daily_after"]
    return [df_(rows, cols), df_(rows90, cols)]


def _before_after(sub, launch, w):
    before = sub[(sub.DateKey >= launch - pd.Timedelta(days=w)) & (sub.DateKey < launch)].SalesAmount.sum() / w
    after = sub[(sub.DateKey >= launch) & (sub.DateKey < launch + pd.Timedelta(days=w))].SalesAmount.sum() / w
    return [before, after]


@Q("Q40")
def _():
    fx = T("FactExchangeRate")
    eur = fx[fx.CurrencyKey == 7].groupby("DateKey").EndOfDayRate.first()
    daily = fos().groupby("DateKey").SalesAmount.sum()
    j = daily.to_frame().join(eur, how="inner")
    return [df_([[(j.SalesAmount * j.EndOfDayRate).sum()]], ["sales_eur"])]


@Q("Q41")
def _():
    f = fos()
    return [df_([[f.loc[(f.year == 2009) & (f.quarter == 4), "SalesAmount"].sum()]], ["sales"])]


@Q("Q42")
def _():
    f = attach_product(fos()[["ProductKey", "year", "SalesAmount", "TotalCost"]].copy())
    c = f[f.ProductCategoryName == "Cameras and camcorders"]
    g = c.groupby("year").agg(sales=("SalesAmount", "sum"), cost=("TotalCost", "sum"))
    r1 = pd.DataFrame({"year": g.index, "sales": g.sales.values, "yoy_pct": pct(g.sales.diff(), g.sales.shift()).values})
    r2 = pd.DataFrame({"year": g.index, "gross_margin": (g.sales - g.cost).values})
    return [r1, r2]


@Q("Q43")
def _():
    f = fos()
    gm = (f.SalesAmount - f.TotalCost).groupby(f.CustomerKey).sum()
    c = cust()
    r1 = gm.groupby(gm.index.map(c.ContinentName)).sum().rename_axis("continent").reset_index(name="gross_margin")
    r2 = gm.groupby(gm.index.map(c.RegionCountryName)).sum().rename_axis("country").reset_index(name="gross_margin")
    return [r1, r2]


@Q("Q44")
def _():
    f = fos()
    y = f.groupby("year").SalesAmount.sum()
    r1 = pd.DataFrame({"year": y.index, "sales": y.values, "yoy_pct": pct(y.diff(), y.shift()).values})
    m = f.groupby(f.DateKey.dt.to_period("M")).SalesAmount.sum()
    r2 = pd.DataFrame({"month": m.index.to_timestamp().date, "sales": m.values})
    return [r1, r2]


@Q("Q45")
def _():
    g = fs().groupby("StoreKey").SalesAmount.sum()
    s = stores()
    size = g.index.map(s.SellingAreaSize)
    d = pd.DataFrame({"StoreName": g.index.map(s.StoreName), "sales": g.values, "area": size,
                      "sales_per_sqft": g.values / size})
    return [d.sort_values("sales_per_sqft", ascending=False, na_position="last")]


@Q("Q46")
def _():
    f = fos()
    gm = (f.SalesAmount - f.TotalCost).groupby(f.CustomerKey).sum()
    out = []
    for col in ("Education", "Occupation"):
        g = gm.groupby(gm.index.map(cust()[col])).sum().rename_axis(col).reset_index(name="gross_margin")
        out.append(select_top(g, [], [("gross_margin", "amount", True)], 1))
    return out


@Q("Q47")
def _():
    sla = T("FactITSLA")
    g = sla.groupby("StoreKey").DownTime.mean()
    return [pd.DataFrame({"StoreName": g.index.map(stores().StoreName), "avg_downtime": g.values})]


@Q("Q48")
def _():
    sales = fs().groupby("StoreKey").SalesAmount.sum()
    down = T("FactITSLA").groupby("StoreKey").DownTime.sum()
    d = pd.DataFrame({"sales": sales}).join(down).fillna({"DownTime": 0})
    d["grp"] = np.where(d.DownTime > 1000, "High downtime (>1000 min)", "Low downtime (<=1000 min)")
    g = d.groupby("grp").agg(avg_sales=("sales", "mean"), stores=("sales", "size")).reset_index()
    corr = d.sales.corr(d.DownTime)
    rho = spearman(d.sales, d.DownTime)  # average ranks for ties
    return [g, df_([[corr]], ["correlation"]), df_([[rho]], ["spearman"])]


@Q("Q49")
def _():
    e = T("DimEntity").set_index("EntityKey")
    sp = _plan(None, (1,))
    rev = sp.groupby("EntityKey").Amount.sum()
    parent = e.ParentEntityKey.astype("Int64")
    total = pd.Series(0.0, index=e.index)
    for ek, amt in rev.items():
        k, seen = ek, set()
        while k not in seen:
            seen.add(k)
            total[k] += amt
            pk = parent.get(k)
            if pd.isna(pk) or pk == k or pk not in e.index:
                break
            k = pk
    has = [k for k in e.index if total[k] != 0]
    return [pd.DataFrame({"EntityKey": has, "EntityName": e.loc[has, "EntityName"].values, "revenue": total[has].values})]


@Q("Q50")
def _():
    f = fs()
    g = f[f.year.isin([2008, 2009])].groupby(["StoreKey", "year"]).SalesAmount.sum().unstack()
    g = g.dropna()
    a, b = g[2008].sum(), g[2009].sum()
    return [df_([[a, b, (b / a - 1) * 100]], ["sales_2008", "sales_2009", "growth_pct"])]


@Q("Q51")
def _():
    return [df_([[T("DimStore").StoreKey.nunique()]], ["stores"])]


@Q("Q52")
def _():
    return [df_([[T("DimProduct").UnitPrice.max()]], ["max_price"])]


@Q("Q53")
def _():
    f = fos()
    return [df_([[f.loc[f.year == 2009, "order"].nunique()]], ["orders"])]


@Q("Q54")
def _():
    return [df_([[fos().ReturnAmount.sum()]], ["return_amount"])]


@Q("Q55")
def _():
    return [df_([[int((T("DimCustomer").Gender == "F").sum())]], ["customers"])]


@Q("Q56")
def _():
    return [df_([[T("DimCustomer").YearlyIncome.mean()]], ["avg_income"])]


@Q("Q57")
def _():
    return [df_([[T("DimProduct").BrandName.nunique()]], ["brands"])]


@Q("Q58")
def _():
    return [df_([[fos().SalesAmount.max()]], ["max_sale"])]


@Q("Q59")
def _():
    return [df_([[int((T("DimDate").IsHoliday == "Yes").sum())]], ["holidays"])]


@Q("Q60")
def _():
    return [df_([[int((T("DimEmployee").DepartmentName == "Production").sum())]], ["employees"])]


@Q("Q61")
def _():
    f = attach_product(fos().loc[lambda d: d.year == 2009, ["ProductKey", "SalesAmount"]].copy(), ("ProductSubcategoryName",))
    g = f.groupby("ProductSubcategoryName", dropna=False).SalesAmount.sum()
    return [g[g > 1_000_000].reset_index()]


@Q("Q62")
def _():
    f = attach_product(fos().loc[lambda d: d.year == 2008, ["ProductKey", "SalesAmount", "SalesQuantity"]].copy(), ("BrandName",))
    g = f.groupby("BrandName", dropna=False)[["SalesAmount", "SalesQuantity"]].sum()
    return [g[g.SalesQuantity >= 500].reset_index()]


@Q("Q63")
def _():
    f = fos()
    occ = f.CustomerKey.map(cust().Occupation)
    g = f.groupby(occ).agg(s=("SalesAmount", "sum"), o=("order", "nunique"))
    return [pd.DataFrame({"occupation": g.index, "aov": (g.s / g.o).values, "orders": g.o.values})]


@Q("Q64")
def _():
    f = fos()
    g = f[f.year == 2009].groupby("month").agg(s=("SalesAmount", "sum"), c=("TotalCost", "sum"))
    return [pd.DataFrame({"month": g.index, "gross_margin": (g.s - g.c).values, "margin_pct": pct(g.s - g.c, g.s).values})]


@Q("Q65")
def _():
    g = fs().groupby("StoreKey").SalesAmount.sum()
    g = g[g > 5_000_000]
    s = stores()
    e = T("DimEmployee").set_index("EmployeeKey")
    ek = g.index.map(s.EmployeeKey)
    mgr = [full_name(e, k) if pd.notna(k) else None for k in ek]
    return [pd.DataFrame({"manager": mgr, "StoreName": g.index.map(s.StoreName), "sales": g.values})]


@Q("Q66")
def _():
    f = fos()
    f = f[(f.year == 2009) & (f.PromotionKey != 1)]
    g = f.groupby("quarter").agg(d=("DiscountAmount", "sum")).reset_index()
    return [g]


@Q("Q67")
def _():
    f = attach_product(fos()[["ProductKey", "SalesAmount", "SalesQuantity"]].copy(), ("ColorName",))
    g = f.groupby("ColorName", dropna=False)[["SalesAmount", "SalesQuantity"]].sum()
    g = g[g.SalesQuantity >= 1000]
    d = pd.DataFrame({"color": g.index, "avg_price": (g.SalesAmount / g.SalesQuantity).values, "units": g.SalesQuantity.values})
    return [d.sort_values("avg_price", ascending=False)]


@Q("Q68")
def _():
    f = fos()
    f = f[f.year == 2009]
    lab = f.DateKey.map(dates().IsHoliday)
    g = f.groupby(lab).agg(orders=("order", "nunique"), revenue=("SalesAmount", "sum"))
    return [g.rename_axis("is_holiday").reset_index()]


@Q("Q69")
def _():
    f = fos()
    f = f[f.PromotionKey != 1].copy()
    f["cat"] = f.PromotionKey.map(T("DimPromotion").set_index("PromotionKey").PromotionCategory)
    f["gross"] = f.SalesAmount + f.DiscountAmount
    with np.errstate(divide="ignore", invalid="ignore"):
        f["row_rate"] = f.DiscountAmount / f.gross
    g = f.groupby("cat").agg(rev=("SalesAmount", "sum"), disc=("DiscountAmount", "sum"), gross=("gross", "sum"),
                             simple=("row_rate", "mean"))
    g = g.sort_values("rev", ascending=False)
    r1 = pd.DataFrame({"cat": g.index, "rev": g.rev.values, "disc": g.disc.values, "pct": pct(g.disc, g.gross).values})
    return [r1]


@Q("Q70")
def _():
    s = T("DimStore")
    sales = fs().groupby("StoreKey").SalesAmount.sum()
    s = s.assign(sales=s.StoreKey.map(sales).fillna(0))
    g = s.groupby("StoreType", dropna=False).agg(sales=("sales", "sum"), area=("SellingAreaSize", "mean"),
                                                  stores=("StoreKey", "nunique"))
    return [g.reset_index()]


@Q("Q71")
def _():
    f = attach_product(fos().loc[lambda d: d.year == 2009, ["ProductKey", "SalesAmount"]].copy(),
                       ("ProductCategoryName", "ProductSubcategoryName"))
    g = f.groupby(["ProductCategoryName", "ProductSubcategoryName"], dropna=False).SalesAmount.sum().reset_index()
    return [select_top(g, ["ProductCategoryName"], [("SalesAmount", "amount", True)], 1)]


@Q("Q72")
def _():
    g = fos().groupby(["year", "quarter"]).SalesAmount.sum().reset_index()
    g["cumulative"] = g.SalesAmount.cumsum()
    return [g]


@Q("Q73")
def _():
    cur = current_inventory()
    g = cur.groupby("ProductKey")[["OnHandQuantity", "SafetyStockQuantity"]].sum()
    g["gap"] = g.OnHandQuantity - g.SafetyStockQuantity
    g.insert(0, "ProductName", g.index.map(prod().ProductName))
    g = g.reset_index()
    top = select_top(g, [], [("gap", "other", True)], 10)
    return [top[["ProductName", "OnHandQuantity", "SafetyStockQuantity", "gap", "ProductKey"]].sort_values("gap", ascending=False)]


@Q("Q74")
def _():
    f = fs()
    f = f[f.year == 2009]
    store_total = f.groupby("StoreKey").SalesAmount.sum()
    g = f.groupby(["StoreKey", "ProductKey"]).SalesAmount.sum().reset_index()
    g["share_pct"] = pct(g.SalesAmount, g.StoreKey.map(store_total))
    top = select_top(g, ["StoreKey"], [("SalesAmount", "amount", True)], 3)
    return [pd.DataFrame({"StoreName": top.StoreKey.map(stores().StoreName), "ProductName": top.ProductKey.map(prod().ProductName),
                          "sales": top.SalesAmount, "share_pct": top.share_pct, "ProductKey": top.ProductKey})]


@Q("Q75")
def _():
    f = fos()
    g = f[f.year.isin([2008, 2009])].groupby(["CustomerKey", "year"]).SalesAmount.sum().unstack(fill_value=0)
    g = g[(g[2008] > 0) & (g[2009] > 1.5 * g[2008])]
    c = cust()
    return [pd.DataFrame({"FirstName": g.index.map(c.FirstName), "LastName": g.index.map(c.LastName),
                          "s2008": g[2008].values, "s2009": g[2009].values,
                          "growth_pct": ((g[2009] / g[2008] - 1) * 100).values, "CustomerKey": g.index})]


@Q("Q76", event=True)
def _():
    f = attach_product(fos()[["ProductKey", "CustomerKey", "order", "SalesAmount", "SalesQuantity"]].copy())
    b = f
    orders_all = b.groupby("CustomerKey").order.nunique()
    repeat_all = set(orders_all[orders_all >= 2].index)
    orders_cat = b.groupby(["ProductCategoryName", "CustomerKey"], dropna=False).order.nunique()
    repeat_cat = set(orders_cat[orders_cat >= 2].index)
    tot = f.groupby("ProductCategoryName", dropna=False).SalesAmount.sum()
    r1 = f[f.CustomerKey.isin(repeat_all)].groupby("ProductCategoryName", dropna=False).SalesAmount.sum()
    keys = pd.MultiIndex.from_arrays([f.ProductCategoryName, f.CustomerKey])
    r2 = f[keys.isin(list(repeat_cat))].groupby("ProductCategoryName", dropna=False).SalesAmount.sum()
    return [pd.DataFrame({"category": tot.index, "repeat_pct": pct(r1.reindex(tot.index, fill_value=0), tot).values}),
            pd.DataFrame({"category": tot.index, "repeat_pct": pct(r2.reindex(tot.index, fill_value=0), tot).values})]


@Q("Q77")
def _():
    f = fos()
    m = f[f.year.isin([2008, 2009])].groupby(["year", "month"]).SalesAmount.sum()
    prev = m.shift()
    m9, p9 = m.loc[2009], prev.loc[2009]
    return [pd.DataFrame({"month": m9.index, "sales": m9.values, "prev": p9.values, "mom_pct": pct(m9 - p9, p9).values})]


@Q("Q78")
def _():
    f = fos()
    f = f[(f.year == 2009) & (f.PromotionKey != 1)]
    cat = f.PromotionKey.map(T("DimPromotion").set_index("PromotionKey").PromotionCategory)
    g = f.groupby(cat).DiscountAmount.sum().sort_values(ascending=False)
    return [pd.DataFrame({"cat": g.index, "discount": g.values, "rank": range(1, len(g) + 1), "share_pct": pct(g, g.sum()).values})]


def _attainment():
    f = fs()
    act = f[f.year == 2009].groupby("StoreKey").SalesAmount.sum()
    qt = pd.read_parquet(DATA / "FactSalesQuota.parquet", columns=["StoreKey", "DateKey", "ScenarioKey", "SalesAmountQuota"])
    qt["DateKey"] = pd.to_datetime(qt["DateKey"])
    qt = qt[(qt.ScenarioKey == 2) & (qt.DateKey.dt.year == 2009)].groupby("StoreKey").SalesAmountQuota.sum()
    d = pd.DataFrame({"actual": act}).join(qt.rename("quota"))
    d["att_pct"] = pct(d.actual, d.quota)
    d.insert(0, "StoreName", d.index.map(stores().StoreName))
    return d.reset_index()


@Q("Q79")
def _():
    d = _attainment()
    top = select_top(d, [], [("att_pct", "percentage", True)], 10)
    return [top[["StoreName", "actual", "quota", "att_pct"]].sort_values("att_pct", ascending=False)]


@Q("Q80", event=True)
def _():
    fl = first_last()
    span = (fl["last"] - fl["first"]).dt.days
    country = fl.index.map(cust().RegionCountryName)
    g = span.groupby(country).agg(["size", "mean"])
    return [pd.DataFrame({"country": g.index, "customers": g["size"].values, "avg_days": g["mean"].values})]


@Q("Q81", event=True)
def _():
    fl = first_last()
    ltv = fos().groupby("CustomerKey").SalesAmount.sum().reindex(fl.index)
    g = ltv.groupby(fl["first"].dt.year).agg(["size", "mean", "sum"])
    return [pd.DataFrame({"cohort": g.index, "customers": g["size"].values, "avg_ltv": g["mean"].values, "total_ltv": g["sum"].values})]


@Q("Q82")
def _():
    e = T("DimEmployee").set_index("EmployeeKey")
    hire = pd.to_datetime(e.HireDate)
    tenure = (TODAY - hire).dt.days / 365.25
    par = e.ParentEmployeeKey.astype("Int64")
    g = tenure.groupby(par).agg(["size", "mean"])
    return [pd.DataFrame({"manager": [full_name(e, k) for k in g.index], "title": g.index.map(e.Title),
                          "reports": g["size"].values, "avg_tenure_years": g["mean"].values})]


@Q("Q83", event=True)
def _():
    b = buys()
    fl = first_last()
    c07 = set(fl[fl["first"].dt.year == 2007].index)
    y08 = set(b[b.year == 2008].CustomerKey)
    y09 = set(b[b.year == 2009].CustomerKey)
    c08 = c07 & y08
    c09 = c08 & y09
    return [df_([[len(c07), len(c08), len(c09)]], ["first_2007", "back_2008", "back_2009"])]


@Q("Q84")
def _():
    f = fos()
    rev = f[f.year == 2009].groupby("ProductKey").SalesAmount.sum()
    d = pd.DataFrame({"rev": rev})
    d["qk"] = d.rev.map(lambda v: q(v, "amount"))
    total = d.rev.sum()
    groups = d.groupby("qk").rev.agg(["sum", "size"]).sort_index(ascending=False)
    after = groups["sum"].cumsum() / total
    before = after - groups["sum"] / total
    out = []
    # Reading 1: a tie group goes by the cumulative share before it joins (< 80% -> A, < 95% -> B).
    # Reading 2: by the cumulative share after it joins (<= 80% -> A, <= 95% -> B).
    for cls in (np.where(before < 0.80, "A", np.where(before < 0.95, "B", "C")),
                np.where(after <= 0.80, "A", np.where(after <= 0.95, "B", "C"))):
        g = d.groupby(d.qk.map(pd.Series(cls, index=groups.index))).rev.agg(["size", "sum"]).reindex(["A", "B", "C"], fill_value=0)
        out.append(pd.DataFrame({"class": g.index, "products": g["size"].values, "revenue": g["sum"].values,
                                 "revenue_pct": pct(g["sum"], total).values}))
    return out


@Q("Q85")
def _():
    d = _attainment().dropna(subset=["att_pct"])
    top = select_top(d, [], [("att_pct", "percentage", True)], 5).assign(bucket="TOP")
    bot = select_top(d, [], [("att_pct", "percentage", False)], 5).assign(bucket="BOTTOM")
    out = pd.concat([top, bot])[["bucket", "StoreName", "actual", "quota", "att_pct"]]
    return [out.sort_values(["bucket", "att_pct"], ascending=[True, False])]


@Q("Q86")
def _():
    f = attach_product(fos().loc[lambda d: d.year == 2009, ["ProductKey", "PromotionKey", "SalesQuantity"]].copy(),
                       ("ProductSubcategoryName",))
    f["disc"] = f.PromotionKey.map(T("DimPromotion").set_index("PromotionKey").DiscountPercent)
    rows, rows_s = [], []
    for sc, g in f.groupby("ProductSubcategoryName", dropna=False):
        rows.append([sc, g.disc.corr(g.SalesQuantity), len(g)])
        rows_s.append([sc, spearman(g.disc, g.SalesQuantity), len(g)])
    return [df_(rows, ["subcategory", "corr", "n"]), df_(rows_s, ["subcategory", "spearman", "n"])]


@Q("Q87")
def _():
    cur = current_inventory().groupby("ProductKey").OnHandQuantity.sum()
    f = fos()
    last90 = f[(f.DateKey >= pd.Timestamp("2009-10-03")) & (f.DateKey <= TODAY)]
    avg = last90.groupby("ProductKey").SalesQuantity.sum() / 90.0
    d = pd.DataFrame({"onhand": cur, "avg_daily": avg}).dropna()
    d = d[d.avg_daily > 0]
    d["coverage"] = d.onhand / d.avg_daily
    d = d.rename_axis("ProductKey").reset_index()
    top = select_top(d, [], [("coverage", "other", False)], 20)
    out = pd.DataFrame({"ProductName": top.ProductKey.map(prod().ProductName), "onhand": top.onhand.astype(int),
                        "avg_daily": top.avg_daily, "coverage": top.coverage, "ProductKey": top.ProductKey})
    return [out.sort_values("coverage")]


@Q("Q88", event=True)
def _():
    b = buys()
    b9 = b[b.year == 2009]
    nq = b9.groupby("CustomerKey").quarter.nunique()
    loyal = nq[nq == 4].index
    f = fos()
    spend = f[(f.year == 2009) & f.CustomerKey.isin(loyal)].groupby("CustomerKey").SalesAmount.sum().reset_index()
    c = cust()
    spend["name"] = spend.CustomerKey.map(c.FirstName + " " + c.LastName)
    top = select_top(spend, [], [("SalesAmount", "amount", True)], 20)
    return [top[["name", "SalesAmount", "CustomerKey"]].sort_values("SalesAmount", ascending=False)]


@Q("Q89", event=True)
def _():
    fl = first_last()
    f = fos()
    spend = f.groupby("CustomerKey").SalesAmount.sum().reindex(fl.index)
    b = buys()
    variety = b.groupby("CustomerKey").ProductKey.nunique().reindex(fl.index)
    seg = pd.Series(segment(months_between(pd.Series(TODAY, index=fl.index), fl["last"])), index=fl.index)
    g = pd.DataFrame({"seg": seg, "spend": spend, "variety": variety}).groupby("seg").agg(
        customers=("spend", "size"), avg_spend=("spend", "mean"), avg_variety=("variety", "mean"))
    return [g.reset_index()]


@Q("Q90")
def _():
    f = attach_product(fos()[["ProductKey", "year", "SalesAmount", "TotalCost"]].copy())
    g = f.groupby(["ProductCategoryName", "year"], dropna=False)[["SalesAmount", "TotalCost"]].sum()
    m = pct(g.SalesAmount - g.TotalCost, g.SalesAmount).unstack()
    return [pd.DataFrame({"category": m.index, "m2007": m[2007].values, "m2008": m[2008].values, "m2009": m[2009].values,
                          "d2008": (m[2008] - m[2007]).values, "d2009": (m[2009] - m[2008]).values})]


@Q("Q91")
def _():
    spend = fos().groupby("CustomerKey").SalesAmount.sum()
    inc = spend.index.map(cust().YearlyIncome)
    d = pd.DataFrame({"s": spend.values, "i": inc}).dropna()
    return [df_([[d.s.corr(d.i), len(d)]], ["corr", "n"]), df_([[spearman(d.s, d.i), len(d)]], ["spearman", "n"])]


@Q("Q92")
def _():
    f = fos()
    f = attach_product(f.loc[(f.year == 2009) & (f.quarter == 4), ["ProductKey", "SalesAmount", "TotalCost"]].copy(), ("BrandName",))
    g = f.groupby("BrandName", dropna=False)[["SalesAmount", "TotalCost"]].sum()
    g["profit"] = g.SalesAmount - g.TotalCost
    g["margin_pct"] = pct(g.profit, g.SalesAmount)
    g = g.sort_values("margin_pct", ascending=False)  # profitability = gross margin rate
    return [pd.DataFrame({"brand": g.index, "revenue": g.SalesAmount.values, "profit": g.profit.values, "margin_pct": g.margin_pct.values})]


@Q("Q93")
def _():
    f = fos()
    disc = f.PromotionKey.map(T("DimPromotion").set_index("PromotionKey").DiscountPercent)
    g = f.groupby("PromotionKey").SalesQuantity.sum()
    dp = g.index.map(T("DimPromotion").set_index("PromotionKey").DiscountPercent)
    promo_corr = pd.Series(dp, index=g.index).corr(g)
    row_corr = disc.corr(f.SalesQuantity)
    return [df_([[promo_corr, row_corr, len(g)]], ["promo_level_corr", "row_level_corr", "n_promotions"])]


@Q("Q94")
def _():
    f = fs()
    f = f[(f.year == 2009) & f.quarter.isin([3, 4])]
    g = f.groupby(["StoreKey", "quarter"]).SalesAmount.sum().unstack(fill_value=0)
    g = g[g[4] < g[3]]
    d = pd.DataFrame({"StoreName": g.index.map(stores().StoreName), "q3": g[3].values, "q4": g[4].values,
                      "change_pct": pct(g[4] - g[3], g[3]).values})
    return [d.sort_values("change_pct")]


@Q("Q95")
def _():
    # Promotional vs full-price lines: average sales per line, and the difference.
    f = attach_product(fos()[["ProductKey", "PromotionKey", "SalesAmount"]].copy())
    f["promo"] = f.PromotionKey != 1
    g = f.groupby(["ProductCategoryName", "promo"], dropna=False).SalesAmount.mean().unstack()
    return [pd.DataFrame({"category": g.index, "promo_avg": g[True].values, "full_avg": g[False].values,
                          "diff": (g[True] - g[False]).values})]


@Q("Q96", event=True)
def _():
    b = buys()
    fl = first_last()
    fy = fl["first"].dt.year
    last_year = b.groupby("CustomerKey").year.max()
    came_back = last_year > fy
    g = came_back.groupby(fy).agg(["size", "sum"])
    return [pd.DataFrame({"cohort": g.index, "customers": g["size"].values, "returned": g["sum"].values,
                          "pct": pct(g["sum"], g["size"]).values})]


@Q("Q97")
def _():
    f = fos()
    f = f[f.year == 2009]
    g = f.groupby(["ProductKey", f.DateKey.dt.month > 6]).SalesAmount.sum().unstack(fill_value=0)
    g.columns = ["h1", "h2"]
    g["growth_pct"] = pct(g.h2 - g.h1, g.h1)
    g["inc"] = g.h2 - g.h1
    name = g.index.map(prod().ProductName)
    r1 = pd.DataFrame({"ProductName": name, "h1": g.h1.values, "h2": g.h2.values, "growth_pct": g.growth_pct.values,
                       "ProductKey": g.index}).dropna(subset=["growth_pct"]).sort_values("growth_pct", ascending=False).head(50)
    r2 = pd.DataFrame({"ProductKey": g.index, "ProductName": name, "h1": g.h1.values, "h2": g.h2.values, "inc": g.inc.values})
    r2 = select_top(r2, [], [("inc", "amount", True)], 15).sort_values("inc", ascending=False)
    return [r1, r2]


@Q("Q98")
def _():
    f = attach_product(fos()[["ProductKey", "year", "quarter", "SalesAmount"]].copy())
    g = f.groupby(["ProductCategoryName", "year", "quarter"], dropna=False).SalesAmount.sum().reset_index()
    g["share_pct"] = pct(g.SalesAmount, g.groupby(["ProductCategoryName", "year"], dropna=False).SalesAmount.transform("sum"))
    r1 = select_top(g[g.year == 2009], ["ProductCategoryName"], [("share_pct", "percentage", True)], 1)
    r1 = r1[["ProductCategoryName", "share_pct", "quarter"]].sort_values("share_pct", ascending=False)
    r2 = select_top(g, ["ProductCategoryName", "year"], [("share_pct", "percentage", True)], 1)
    r2 = r2[["ProductCategoryName", "year", "share_pct", "quarter"]].sort_values(["year", "share_pct"], ascending=[True, False])
    return [r1, r2]


@Q("Q99")
def _():
    f = attach_product(fos()[["ProductKey", "DateKey", "SalesAmount"]].copy())
    d = f.groupby(["ProductCategoryName", "DateKey"], dropna=False).SalesAmount.sum().reset_index()
    d["we"] = d.DateKey.map(dates().IsWorkDay) == "WeekEnd"
    g = d.groupby(["ProductCategoryName", "we"], dropna=False).SalesAmount.mean().unstack()
    return [pd.DataFrame({"category": g.index, "weekend_avg": g[True].values, "weekday_avg": g[False].values,
                          "diff_pct": pct(g[True] - g[False], g[False]).values})]


@Q("Q100", event=True)
def _():
    f = fos()
    b = buys()
    orders = b.groupby("CustomerKey").order.nunique()
    sales = f.groupby("CustomerKey").SalesAmount.sum().reindex(orders.index)
    aov = sales / orders
    oq = orders.map(lambda v: float(q(v, "count")))
    aq = aov.map(lambda v: float(q(v, "amount")))
    t_o = np.quantile(oq.values, 0.9, method="linear")
    t_a = np.quantile(aq.values, 0.9, method="linear")
    sel = (oq >= t_o) & (aq >= t_a)
    c = cust()
    k = orders.index[sel]
    return [pd.DataFrame({"name": k.map(c.FirstName + " " + c.LastName), "orders": orders[sel].values,
                          "aov": aov[sel].values, "sales": sales[sel].values, "CustomerKey": k})]


# --------------------------------------------------------------------------
# Q101-Q122 (new; second-round approved wording, eval main dd5853d)
# --------------------------------------------------------------------------
@Q("Q101")
def _():
    f = fos()
    return [df_([[f.loc[(f.year == 2009) & (f.quarter == 4), "SalesAmount"].sum()]], ["gmv"])]


@Q("Q102")
def _():
    f = attach_product(fos().loc[lambda d: d.year == 2009, ["ProductKey", "SalesAmount", "ReturnAmount"]].copy())
    g = (f.SalesAmount - f.ReturnAmount).groupby(f.ProductCategoryName, dropna=False).sum()
    return [g.rename_axis("category").reset_index(name="net_sales")]


@Q("Q103")
def _():
    f = fos()
    f = f[f.year == 2009]
    orders = f.groupby("order").SalesAmount.sum()
    big = orders[orders > 1000]
    return [df_([[len(big), pct(big.sum(), f.SalesAmount.sum())]], ["orders_over_1000", "sales_share_pct"])]


@Q("Q104")
def _():
    f = attach_product(fos().loc[lambda d: d.year.isin([2008, 2009]), ["ProductKey", "year", "SalesAmount", "TotalCost"]].copy())
    f["gp"] = f.SalesAmount - f.TotalCost
    g = f.groupby(["ProductCategoryName", "year"], dropna=False)[["SalesAmount", "gp"]].sum().unstack(fill_value=0)
    drev = g["SalesAmount"][2009] - g["SalesAmount"][2008]
    dgp = g["gp"][2009] - g["gp"][2008]
    sel = (drev > 0) & (dgp < 0)
    return [pd.DataFrame({"category": g.index[sel], "revenue_change": drev[sel].values, "gross_profit_change": dgp[sel].values})]


def _store_keys_in_city(city):
    s = T("DimStore").merge(T("DimGeography"), on="GeographyKey", how="left")
    return s.loc[s.CityName == city, "StoreKey"]


@Q("Q105")
def _():
    f = fs()
    sk = T("DimStore").set_index("StoreName").StoreKey["Contoso Seattle No.2 Store"]
    return [df_([[f.loc[(f.StoreKey == sk) & (f.year == 2009), "SalesAmount"].sum()]], ["sales_2009"])]


@Q("Q106")
def _():
    f = fs()
    f = f[f.StoreKey.isin(_store_keys_in_city("Miami"))]
    a, b = (f.loc[f.year == y, "SalesAmount"].sum() for y in (2008, 2009))
    return [df_([[pct(b - a, a)]], ["growth_pct"])]


@Q("Q107")
def _():
    f = fs()
    f = f[(f.year == 2009) & f.StoreKey.isin(_store_keys_in_city("New York"))]
    net = (f.SalesAmount - f.ReturnAmount).groupby(f.StoreKey).sum()
    sk = T("DimStore").set_index("StoreName").StoreKey["Contoso New York No.2 Store"]
    return [df_([[pct(net.get(sk, 0.0), net.sum())]], ["share_pct"])]


@Q("Q108")
def _():
    f = fos()
    f = f[f.year == 2009]
    country = f.CustomerKey.map(cust().RegionCountryName)
    g = f.groupby(country, dropna=False).agg(revenue=("SalesAmount", "sum"), orders=("order", "nunique"))
    return [g.rename_axis("country").reset_index()]


@Q("Q109")
def _():
    f = fos()
    d = dates()
    out = {}
    for y in (2008, 2009):
        days = d[d.index.year == y]
        daily = f[f.year == y].groupby("DateKey").SalesAmount.sum().reindex(days.index, fill_value=0)
        out[y] = daily.groupby(days.index.quarter).mean()
    rows = [[qtr, pct(out[2009][qtr] - out[2008][qtr], out[2008][qtr])] for qtr in (1, 2, 3, 4)]
    return [df_(rows, ["quarter", "growth_pct"])]


@Q("Q110")
def _():
    f = fs()
    ch = f.channelKey.map(T("DimChannel").set_index("ChannelKey").ChannelName)
    share = {}
    for y in (2008, 2009):
        m = f.year == y
        share[y] = pct(f.loc[m & (ch == "Online"), "SalesAmount"].sum(), f.loc[m, "SalesAmount"].sum())
    return [df_([[share[2008], share[2009], share[2009] - share[2008]]], ["share_2008_pct", "share_2009_pct", "change_pp"])]


@lru_cache(None)
def _quota_budget_2009():
    qt = pd.read_parquet(DATA / "FactSalesQuota.parquet", columns=["StoreKey", "DateKey", "ScenarioKey", "SalesAmountQuota"])
    qt["DateKey"] = pd.to_datetime(qt["DateKey"])
    qt = qt[(qt.ScenarioKey == 2) & (qt.DateKey.dt.year == 2009)]
    return qt.groupby(["StoreKey", qt.DateKey.dt.month.rename("month")]).SalesAmountQuota.sum().unstack(fill_value=0.0)


def _actual_by_month_2009():
    f = fs()
    return f[f.year == 2009].groupby(["StoreKey", "month"]).SalesAmount.sum().unstack(fill_value=0.0)


def _nz_pct(a, b):
    return pct(a, b.where(b != 0))


@Q("Q111")
def _():
    qm = _quota_budget_2009()
    am = _actual_by_month_2009()
    keys = qm.index.union(am.index)
    qm = qm.reindex(index=keys, columns=range(1, 13), fill_value=0.0)
    am = am.reindex(index=keys, columns=range(1, 13), fill_value=0.0)
    ytd_a = am.loc[:, 1:9].sum(axis=1)
    return [pd.DataFrame({"StoreName": keys.map(stores().StoreName),
                          "ytd_pct": _nz_pct(ytd_a, qm.loc[:, 1:9].sum(axis=1)).values,
                          "annual_pct": _nz_pct(ytd_a, qm.sum(axis=1)).values})]


STRETCH = 1.2


@Q("Q112")
def _():
    quota = _quota_budget_2009().sum(axis=1)
    actual = _actual_by_month_2009().sum(axis=1)
    s = T("DimStore").set_index("StoreKey")
    d = pd.DataFrame({"quota": quota}).join(actual.rename("actual")).fillna({"actual": 0.0})
    d = d[d.quota > 0]
    line = STRETCH * d.quota
    d["missed"] = d.actual < line
    d["gap"] = (line - d.actual).where(d.missed)
    d["mgr"] = d.index.map(s.EmployeeKey)
    g = d.groupby("mgr", dropna=False).agg(stores=("missed", "sum"), shortfall=("gap", "sum"))
    g.loc[g.stores == 0, "shortfall"] = np.nan
    e = T("DimEmployee").set_index("EmployeeKey")
    names = [full_name(e, int(k)) if pd.notna(k) else None for k in g.index]
    return [pd.DataFrame({"EmployeeKey": g.index, "manager": names, "missed_stores": g.stores.astype(int).values,
                          "shortfall": g.shortfall.values})]


@Q("Q113")
def _():
    annual = _quota_budget_2009().sum(axis=1)
    annual = annual[annual > 0]
    am = _actual_by_month_2009().reindex(index=annual.index, columns=range(1, 13), fill_value=0.0)
    below = am.lt(annual / 12, axis=0)
    rows = []
    for sk, r in below.iterrows():
        run = []
        for m in list(range(1, 13)) + [13]:
            if m <= 12 and r[m]:
                run.append(m)
                continue
            if len(run) >= 3:
                rows.append([stores().StoreName[sk], run[0], run[-1], len(run)])
            run = []
    return [df_(rows, ["StoreName", "start_month", "end_month", "months"])]


MONTH_ENDS = pd.date_range("2007-01-31", "2007-06-30", freq="ME")


def _in_window(s, T_):
    """New-customer window [T - 89 days, T], cutoff day included (semantic layer)."""
    return (s >= T_ - pd.Timedelta(days=89)) & (s <= T_)


@Q("Q114", event=True)
def _():
    first = first_last()["first"]
    return [pd.DataFrame({"month_end": MONTH_ENDS.date,
                          "new_customers": [int(_in_window(first, t).sum()) for t in MONTH_ENDS]})]


@Q("Q115", event=True)
def _():
    b = buys()
    t0, t1 = pd.Timestamp("2008-12-31"), TODAY
    last0 = b[b.DateKey <= t0].groupby("CustomerKey").DateKey.max()
    last1 = b.groupby("CustomerKey").DateKey.max().reindex(last0.index)
    s0 = segment(months_between(pd.Series(t0, index=last0.index), last0))
    s1 = segment(months_between(pd.Series(t1, index=last1.index), last1))
    m = pd.crosstab(pd.Series(s0, name="from"), pd.Series(s1, name="to"))
    states = list(SEGMENTS)
    m = m.reindex(index=states, columns=states, fill_value=0)
    rows = [[a, c, int(m.loc[a, c])] for a in states for c in states]
    return [df_(rows, ["state_2008", "state_2009", "customers"])]


@Q("Q116", event=True)
def _():
    b = buys()
    first = b.groupby("CustomerKey").DateKey.min()
    # Days 1..7 after the first purchase day; customers need all 7 days observed by TODAY.
    keys = first[first + pd.Timedelta(days=7) <= TODAY].index
    day = (b.DateKey - b.CustomerKey.map(first)).dt.days
    rep = set(b.loc[(day >= 1) & (day <= 7), "CustomerKey"])
    flag = pd.Series(keys.isin(list(rep)), index=keys)
    cohort = first.reindex(keys).dt.to_period("M").dt.to_timestamp()
    g = flag.groupby(cohort).agg(["size", "sum"])
    return [pd.DataFrame({"first_month": g.index.date, "repurchase_pct": pct(g["sum"], g["size"]).values})]


@Q("Q117")
def _():
    f = fs()
    f = attach_product(f.loc[f.year.isin([2008, 2009]), ["StoreKey", "ProductKey", "year", "SalesAmount"]].copy())
    st = f.groupby(["StoreKey", "year"]).SalesAmount.sum().unstack().dropna()  # same store: sales both years
    st = st[st[2009] < st[2008]]
    st["decline_pct"] = pct(st[2008] - st[2009], st[2008])
    st = st.rename_axis("StoreKey").reset_index()
    top_stores = select_top(st, [], [("decline_pct", "percentage", True)], 3)
    c = f[f.StoreKey.isin(top_stores.StoreKey)].groupby(["StoreKey", "ProductCategoryName", "year"], dropna=False).SalesAmount.sum().unstack(fill_value=0)
    c = c.reset_index()
    c["cat_decline"] = c[2008] - c[2009]
    sd = top_stores.set_index("StoreKey")
    c["share_pct"] = pct(c.cat_decline, c.StoreKey.map(sd[2008] - sd[2009]))
    worst = select_top(c, ["StoreKey"], [("cat_decline", "amount", True)], 1)
    out = pd.DataFrame({"StoreKey": worst.StoreKey, "StoreName": worst.StoreKey.map(stores().StoreName),
                        "store_decline_pct": worst.StoreKey.map(sd.decline_pct), "category": worst.ProductCategoryName,
                        "category_decline": worst.cat_decline, "share_pct": worst.share_pct})
    return [out.sort_values(["store_decline_pct", "category_decline"], ascending=False)]


@Q("Q118")
def _():
    f = fos()
    s8 = f[f.year == 2008].groupby("ProductKey").SalesAmount.sum()
    qv = s8.map(lambda v: float(q(v, "amount")))
    thr = np.quantile(qv.values, 0.9, method="linear")
    members = qv.index[qv >= thr]
    f9 = f[f.year == 2009]
    m = f9.loc[f9.ProductKey.isin(members), "SalesAmount"].sum()
    return [df_([[m, pct(m, f9.SalesAmount.sum())]], ["top_decile_sales_2009", "share_pct"])]


@Q("Q119")
def _():
    f = fs()
    f = f[f.year == 2009]
    company = f.groupby("ProductKey").SalesAmount.sum()
    cq = company.map(lambda v: q(v, "amount"))
    comp_rank = cq.rank(method="min", ascending=False).astype(int)
    g = f.groupby(["StoreKey", "ProductKey"]).SalesAmount.sum().reset_index()
    top = select_top(g, ["StoreKey"], [("SalesAmount", "amount", True)], 1)
    base = pd.DataFrame({"StoreKey": top.StoreKey, "StoreName": top.StoreKey.map(stores().StoreName),
                         "ProductKey": top.ProductKey, "ProductName": top.ProductKey.map(prod().ProductName),
                         "store_sales": top.SalesAmount})
    return [base.assign(company_rank=top.ProductKey.map(comp_rank))]


@Q("Q120", event=True)
def _():
    b = buys()
    buyers = b.loc[b.year == 2009, "CustomerKey"].unique()
    f = fos()
    spend = f[f.year == 2009].groupby("CustomerKey").SalesAmount.sum().reindex(buyers, fill_value=0.0)
    c = cust()
    d = pd.DataFrame({"spend": spend, "income": spend.index.map(c.YearlyIncome), "occ": spend.index.map(c.Occupation)})
    d = d.dropna(subset=["income"])
    rows = [["全体", None, len(d), d.income.corr(d.spend)]]
    rows += [["职业内", o, len(x), x.income.corr(x.spend)] for o, x in d.groupby("occ", dropna=False)]
    return [df_(rows, ["scope", "occupation", "customers", "corr"])]


@Q("Q121")
def _():
    f = attach_product(fos().loc[lambda d: d.year == 2009, ["ProductKey", "month", "SalesAmount"]].copy())
    m = f.groupby(["ProductCategoryName", "month"], dropna=False).SalesAmount.sum().unstack(fill_value=0.0)
    m = m.reindex(columns=range(1, 13), fill_value=0.0)
    mean = m.mean(axis=1)
    out = []
    for ddof in (0, 1):
        cv = m.std(axis=1, ddof=ddof) / mean.where(mean != 0)
        out.append(pd.DataFrame({"category": m.index, "monthly_mean": mean.values, "cv": cv.values}))
    return out


@Q("Q122", event=True)
def _():
    # Top-10 Contoso product pairs by co-occurring 2009 orders (complete boundary), with lift
    # over all 2009 online orders.
    f = fos()
    f9 = f[f.year == 2009]
    n_orders = f9["order"].nunique()
    rows = f9.loc[f9.ProductKey.map(prod().BrandName) == "Contoso", ["order", "ProductKey"]].drop_duplicates()
    cnt = rows.groupby("ProductKey").size()
    m = rows.merge(rows, on="order")
    m = m[m.ProductKey_x < m.ProductKey_y]
    co = m.groupby(["ProductKey_x", "ProductKey_y"]).size().rename("co").reset_index()
    top = select_top(co, [], [("co", "count", True)], 10)
    ca, cb = top.ProductKey_x.map(cnt), top.ProductKey_y.map(cnt)
    p = prod().ProductName
    return [pd.DataFrame({"product_a": top.ProductKey_x, "name_a": top.ProductKey_x.map(p),
                          "product_b": top.ProductKey_y, "name_b": top.ProductKey_y.map(p),
                          "co_orders": top.co, "lift": top.co * n_orders / (ca * cb)})]


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------
def write(df, path):
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == float:
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else repr(float(v)))
    df.to_csv(path, index=False)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--eval-dir", default=os.environ.get("SEMDEBT_EVAL_RO", ""),
                    help="read-only checkout of the question bank whose wording these computations follow")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    only = [s.strip() for s in args.only.split(",") if s.strip()]
    ids = only or sorted(QS, key=lambda s: int(s[1:]))
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() and only else {}
    sha = None
    if args.eval_dir:
        import subprocess
        sha = subprocess.run(["git", "-C", args.eval_dir, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        if only:
            # Partial rerun: the other questions still follow the full run's bank commit.
            manifest.setdefault("_reruns", []).append({"eval_dir": args.eval_dir, "eval_commit": sha, "questions": only})
        else:
            manifest["_source"] = {"eval_dir": args.eval_dir, "eval_commit": sha}
    for qid in ids:
        t0 = time.time()
        for old in out.glob(f"{qid}-*.csv"):
            old.unlink()
        res = QS[qid]()
        entry = {"event_sensitive": qid in EVENT, "files": []}
        if sha:
            entry["eval_commit"] = sha
        for i, df in enumerate(res, 1):
            p = out / f"{qid}-{i}.csv"
            write(df, p)
            entry["files"].append({"ref": i, "mode": None, "path": p.name, "rows": len(df)})
        entry["seconds"] = round(time.time() - t0, 1)
        manifest[qid] = entry
        print(qid, entry, flush=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=False))


if __name__ == "__main__":
    sys.exit(main())
