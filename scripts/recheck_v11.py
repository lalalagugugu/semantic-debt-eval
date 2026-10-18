"""T05b: independent pandas recomputation of the references bank PR #19 changes or adds (eval-v1.1).

Builds on scripts/recheck_pandas.py (same data access, conventions and rulings) and
applies the eval-v1.1 presentation rulings, written from the main repo decisions
only, never from the bank's sql fields, refs/, MANIFEST or build_refs.py:

  * decisions/2026-10-18-ux-conventions-and-annotation-disputes.md
      section 1: change questions give absolute change and percentage; ranking
      questions give a rank column; rates give their base (denominator);
      section 3: Q38 gets an overall forecast-accuracy reference;
      section 5: placeholder or missing names -> the key is the identifier;
      section 8: borderline questions get no extra column.
  * decisions/2026-10-18-names-required-by-system-prompt.md section 3-2:
      class 5 long tables, class 7 periods (quarter as Q1-Q4, month as month
      number with a year column), class 10 empty-set totals as 0.

Rank columns are competition ranks (1, 1, 3) on the scorer-quantized ranking key.
Where the rulings leave a choice open (which base, which sign), this script writes
every candidate as an extra column; the comparator maps reference columns by value
multiset, so extra columns never cause a match by themselves.

Usage:
  uv run python scripts/recheck_v11.py --eval-dir "$SEMDEBT_DATA_DIR/eval-ro-6234d29"
Outputs go to reports/T05b/pandas-v11/ (Qxx-k.csv + manifest.json), k = bank ref position.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recheck_pandas as rp  # noqa: E402
from recheck_pandas import T, attach_product, dates, fos, fs, pct, prod, q, stores  # noqa: E402

OUT = rp.ROOT / "reports" / "T05b" / "pandas-v11"
V = {}


def V11(qid):
    def deco(fn):
        V[qid] = fn
        return fn
    return deco


def base(qid):
    return [d.reset_index(drop=True) for d in rp.QS[qid]()]


def crank(s, kind, desc=True, groups=None):
    """Competition rank on the quantized key; NULL keys get no rank."""
    key = s.map(lambda v: np.nan if pd.isna(v) else float(q(v, kind)))
    if groups is None:
        r = key.rank(method="min", ascending=not desc)
    else:
        r = key.groupby(groups, dropna=False).rank(method="min", ascending=not desc)
    return r.astype("Int64")


def qlabel(s):
    return "Q" + s.astype(int).astype(str)


@V11("Q07")
def _():
    d = base("Q07")[0]
    return [d.assign(rank=crank(d.UnitPrice, "amount"))]


@V11("Q17")
def _():
    d = base("Q17")[0]
    return [d.assign(total=d.sales.sum())]


@V11("Q22")
def _():
    return base("Q22")


@V11("Q26")
def _():
    d = base("Q26")[0]
    return [d.assign(quarter=qlabel(d.quarter))]


@V11("Q27")
def _():
    d = base("Q27")[0]
    return [d.assign(rank=crank(d.margin_pct, "percentage"))]


@V11("Q29")
def _():
    f = fos()
    daily = f.groupby("DateKey").SalesAmount.sum()
    m = daily.groupby(daily.index.map(dates().IsHoliday)).mean()
    return [rp.df_([[(m["Yes"] / m["No"] - 1) * 100, m["Yes"] - m["No"]]], ["pct_diff", "abs_diff"])]


@V11("Q31")
def _():
    sp = rp._plan(2009)
    names = T("DimScenario").set_index("ScenarioKey").ScenarioName
    g = sp.groupby(["category", "ScenarioKey"]).Amount.sum().reset_index()
    return [pd.DataFrame({"category": g.category, "scenario": g.ScenarioKey.map(names), "amount": g.Amount})]


@V11("Q33")
def _():
    d = base("Q33")[0]
    return [d.assign(rank=crank(d.orders, "count"))]


@V11("Q38")
def _():
    by_cat = base("Q38")[0]
    sp = rp._plan(2009, (1, 3))
    sp = sp[sp.DateKey.dt.quarter == 4]
    a = sp.loc[sp.ScenarioKey == 1, "Amount"].sum()
    f = sp.loc[sp.ScenarioKey == 3, "Amount"].sum()
    total = rp.df_([[f, a, (1 - abs(a - f) / a) * 100]], ["forecast", "actual", "accuracy_pct"])
    return [by_cat, total]


@V11("Q42")
def _():
    r1, r2 = base("Q42")
    return [r1.assign(yoy_amount=r1.sales.diff()), r2]


@V11("Q44")
def _():
    r1, _ = base("Q44")
    f = fos()
    m = f.groupby(["year", "month"]).SalesAmount.sum().reset_index()
    return [r1.assign(yoy_amount=r1.sales.diff()),
            pd.DataFrame({"month": m.month.astype(int), "sales": m.SalesAmount, "year": m.year.astype(int)})]


@V11("Q45")
def _():
    d = base("Q45")[0]
    return [d.assign(rank=crank(d.sales_per_sqft, "amount"))]


@V11("Q64")
def _():
    d = base("Q64")[0]
    f = fos()
    rev = f[f.year == 2009].groupby("month").SalesAmount.sum()
    return [d.assign(revenue=d.month.map(rev).values)]


@V11("Q65")
def _():
    g = fs().groupby("StoreKey").SalesAmount.sum()
    g = g[g > 5_000_000]
    d = base("Q65")[0]
    return [d.assign(EmployeeKey=g.index.map(stores().EmployeeKey).astype(float).values)]


@V11("Q66")
def _():
    d = base("Q66")[0]
    return [d.assign(quarter=qlabel(d.quarter))]


@V11("Q67")
def _():
    d = base("Q67")[0]
    return [d.assign(rank=crank(d.avg_price, "amount"))]


@V11("Q69")
def _():
    f = fos()
    f = f[f.PromotionKey != 1].copy()
    cat = f.PromotionKey.map(T("DimPromotion").set_index("PromotionKey").PromotionCategory)
    gross = (f.SalesAmount + f.DiscountAmount).groupby(cat).sum()
    d = base("Q69")[0]
    return [d.assign(gross=d.cat.map(gross).values)]


@V11("Q72")
def _():
    d = base("Q72")[0]
    return [d.assign(quarter=qlabel(d.quarter))]


@V11("Q73")
def _():
    d = base("Q73")[0]
    return [d.assign(rank=crank(d.gap, "other"))]


@V11("Q74")
def _():
    f = fs()
    f = f[f.year == 2009]
    store_total = f.groupby("StoreKey").SalesAmount.sum()
    g = f.groupby(["StoreKey", "ProductKey"]).SalesAmount.sum().reset_index()
    g["share_pct"] = pct(g.SalesAmount, g.StoreKey.map(store_total))
    g["rank"] = crank(g.SalesAmount, "amount", groups=g.StoreKey)
    top = rp.select_top(g, ["StoreKey"], [("SalesAmount", "amount", True)], 3)
    return [pd.DataFrame({"StoreName": top.StoreKey.map(stores().StoreName), "ProductName": top.ProductKey.map(prod().ProductName),
                          "sales": top.SalesAmount, "share_pct": top.share_pct, "ProductKey": top.ProductKey,
                          "store_total": top.StoreKey.map(store_total), "rank": top["rank"]})]


@V11("Q75")
def _():
    return base("Q75")


@V11("Q76")
def _():
    f = attach_product(fos()[["ProductKey", "CustomerKey", "order", "SalesAmount"]].copy())
    orders_all = f.groupby("CustomerKey").order.nunique()
    repeat_all = set(orders_all[orders_all >= 2].index)
    orders_cat = f.groupby(["ProductCategoryName", "CustomerKey"], dropna=False).order.nunique()
    repeat_cat = set(orders_cat[orders_cat >= 2].index)
    tot = f.groupby("ProductCategoryName", dropna=False).SalesAmount.sum()
    r1 = f[f.CustomerKey.isin(repeat_all)].groupby("ProductCategoryName", dropna=False).SalesAmount.sum().reindex(tot.index, fill_value=0)
    keys = pd.MultiIndex.from_arrays([f.ProductCategoryName, f.CustomerKey])
    r2 = f[keys.isin(list(repeat_cat))].groupby("ProductCategoryName", dropna=False).SalesAmount.sum().reindex(tot.index, fill_value=0)
    return [pd.DataFrame({"category": tot.index, "repeat_pct": pct(r, tot).values, "repeat_sales": r.values, "total": tot.values})
            for r in (r1, r2)]


@V11("Q77")
def _():
    d = base("Q77")[0]
    return [d.assign(mom_amount=d.sales - d.prev)]


@V11("Q78")
def _():
    d = base("Q78")[0]
    return [d.assign(total=d.discount.sum())]


@V11("Q79")
def _():
    d = base("Q79")[0]
    return [d.assign(rank=crank(d.att_pct, "percentage"))]


@V11("Q83")
def _():
    n = base("Q83")[0].iloc[0]
    return [rp.df_([[2007, 2007, n.first_2007], [2007, 2008, n.back_2008], [2007, 2009, n.back_2009]],
                   ["cohort_year", "year", "customers"])]


@V11("Q84")
def _():
    out = []
    for d in base("Q84"):
        out.append(d.assign(total=d.revenue.sum()))
    return out


@V11("Q85")
def _():
    d = base("Q85")[0]
    d["bucket"] = d.bucket.map({"TOP": "最高", "BOTTOM": "最低"})
    top = d.bucket == "最高"
    r = pd.Series(pd.NA, index=d.index, dtype="Int64")
    r[top] = crank(d.loc[top, "att_pct"], "percentage", desc=True)
    r[~top] = crank(d.loc[~top, "att_pct"], "percentage", desc=False)
    return [d.assign(rank=r)]


@V11("Q87")
def _():
    d = base("Q87")[0]
    return [d.assign(rank=crank(d.coverage, "other", desc=False))]


@V11("Q88")
def _():
    d = base("Q88")[0]
    return [d.assign(rank=crank(d.SalesAmount, "amount"))]


@V11("Q90")
def _():
    f = attach_product(fos()[["ProductKey", "year", "SalesAmount", "TotalCost"]].copy())
    g = f.groupby(["ProductCategoryName", "year"], dropna=False)[["SalesAmount", "TotalCost"]].sum().reset_index()
    g["margin_pct"] = pct(g.SalesAmount - g.TotalCost, g.SalesAmount)
    g = g.sort_values(["ProductCategoryName", "year"])
    g["change_pp"] = g.groupby("ProductCategoryName", dropna=False).margin_pct.diff()
    return [pd.DataFrame({"category": g.ProductCategoryName, "year": g.year.astype(int), "margin_pct": g.margin_pct,
                          "change_pp": g.change_pp, "revenue": g.SalesAmount})]


@V11("Q92")
def _():
    d = base("Q92")[0]
    return [d.assign(rank=crank(d.margin_pct, "percentage"))]


@V11("Q95")
def _():
    d = base("Q95")[0]
    return [d.assign(diff_pct=pct(d["diff"], d.full_avg))]


@V11("Q97")
def _():
    r1, r2 = base("Q97")
    r1 = r1.assign(inc=r1.h2 - r1.h1, rank=crank(r1.growth_pct, "percentage"))
    r2 = r2.assign(growth_pct=pct(r2.inc, r2.h1), rank=crank(r2.inc, "amount"))
    return [r1, r2]


@V11("Q98")
def _():
    r1, r2 = base("Q98")
    f = attach_product(fos()[["ProductKey", "year", "SalesAmount"]].copy())
    # NaN never equals NaN as a dict key: look the empty category up under a sentinel.
    f["cat"] = f.ProductCategoryName.fillna("\0")
    cy = f.groupby(["cat", "year"]).SalesAmount.sum()
    r1 = r1.assign(quarter=qlabel(r1.quarter),
                   annual=[cy.get((c, 2009), np.nan) for c in r1.ProductCategoryName.fillna("\0")],
                   rank=crank(r1.share_pct, "percentage"))
    r2 = r2.assign(quarter=qlabel(r2.quarter),
                   annual=[cy.get((c, y), np.nan) for c, y in zip(r2.ProductCategoryName.fillna("\0"), r2.year)],
                   rank=crank(r2.share_pct, "percentage", groups=r2.year))
    return [r1, r2]


@V11("Q100")
def _():
    return base("Q100")


@V11("Q103")
def _():
    f = fos()
    f = f[f.year == 2009]
    orders = f.groupby("order").SalesAmount.sum()
    big = orders[orders > 1000]
    total = f.SalesAmount.sum()
    return [rp.df_([[len(big), pct(big.sum(), total), big.sum(), total]], ["orders_over_1000", "sales_share_pct", "big_sales", "total"])]


@V11("Q104")
def _():
    f = attach_product(fos().loc[lambda d: d.year.isin([2008, 2009]), ["ProductKey", "year", "SalesAmount", "TotalCost"]].copy())
    f["gp"] = f.SalesAmount - f.TotalCost
    g = f.groupby(["ProductCategoryName", "year"], dropna=False)[["SalesAmount", "gp"]].sum().unstack(fill_value=0)
    drev = g["SalesAmount"][2009] - g["SalesAmount"][2008]
    dgp = g["gp"][2009] - g["gp"][2008]
    sel = (drev > 0) & (dgp < 0)
    return [pd.DataFrame({"category": g.index[sel], "revenue_change": drev[sel].values, "gross_profit_change": dgp[sel].values,
                          "revenue_change_pct": pct(drev, g["SalesAmount"][2008])[sel].values,
                          "gross_profit_change_pct": pct(dgp, g["gp"][2008])[sel].values,
                          "gross_profit_change_pct_abs": pct(dgp, g["gp"][2008].abs())[sel].values})]


@V11("Q106")
def _():
    f = fs()
    f = f[f.StoreKey.isin(rp._store_keys_in_city("Miami"))]
    a, b = (f.loc[f.year == y, "SalesAmount"].sum() for y in (2008, 2009))
    return [rp.df_([[pct(b - a, a), b - a]], ["growth_pct", "growth_amount"])]


@V11("Q107")
def _():
    f = fs()
    f = f[(f.year == 2009) & f.StoreKey.isin(rp._store_keys_in_city("New York"))]
    net = (f.SalesAmount - f.ReturnAmount).groupby(f.StoreKey).sum()
    sk = T("DimStore").set_index("StoreName").StoreKey["Contoso New York No.2 Store"]
    return [rp.df_([[pct(net.get(sk, 0.0), net.sum()), net.get(sk, 0.0), net.sum()]], ["share_pct", "store_net", "city_net"])]


@V11("Q109")
def _():
    f = fos()
    d = dates()
    out = {}
    for y in (2008, 2009):
        days = d[d.index.year == y]
        daily = f[f.year == y].groupby("DateKey").SalesAmount.sum().reindex(days.index, fill_value=0)
        out[y] = daily.groupby(days.index.quarter).mean()
    rows = [[f"Q{k}", pct(out[2009][k] - out[2008][k], out[2008][k]), out[2009][k] - out[2008][k]] for k in (1, 2, 3, 4)]
    return [rp.df_(rows, ["quarter", "growth_pct", "diff"])]


@V11("Q110")
def _():
    f = fs()
    ch = f.channelKey.map(T("DimChannel").set_index("ChannelKey").ChannelName)
    rows, prev = [], None
    for y in (2008, 2009):
        m = f.year == y
        tot = f.loc[m, "SalesAmount"].sum()
        s = pct(f.loc[m & (ch == "Online"), "SalesAmount"].sum(), tot)
        rows.append([y, s, np.nan if prev is None else s - prev, tot])
        prev = s
    return [rp.df_(rows, ["year", "share_pct", "change_pp", "total"])]


@V11("Q111")
def _():
    qm = rp._quota_budget_2009()
    am = rp._actual_by_month_2009()
    keys = qm.index.union(am.index)
    qm = qm.reindex(index=keys, columns=range(1, 13), fill_value=0.0)
    am = am.reindex(index=keys, columns=range(1, 13), fill_value=0.0)
    ytd_a = am.loc[:, 1:9].sum(axis=1)
    ytd_q = qm.loc[:, 1:9].sum(axis=1)
    ann_q = qm.sum(axis=1)
    return [pd.DataFrame({"StoreName": keys.map(stores().StoreName),
                          "ytd_pct": rp._nz_pct(ytd_a, ytd_q).values, "annual_pct": rp._nz_pct(ytd_a, ann_q).values,
                          "ytd_actual": ytd_a.values, "ytd_quota": ytd_q.values, "annual_quota": ann_q.values,
                          "ytd_quota_nz": ytd_q.where(ytd_q != 0).values, "annual_quota_nz": ann_q.where(ann_q != 0).values})]


@V11("Q112")
def _():
    d = base("Q112")[0]
    return [d.assign(shortfall=d.shortfall.fillna(0.0))]


@V11("Q116")
def _():
    b = rp.buys()
    first = b.groupby("CustomerKey").DateKey.min()
    keys = first[first + pd.Timedelta(days=7) <= rp.TODAY].index
    day = (b.DateKey - b.CustomerKey.map(first)).dt.days
    rep = set(b.loc[(day >= 1) & (day <= 7), "CustomerKey"])
    flag = pd.Series(keys.isin(list(rep)), index=keys)
    fk = first.reindex(keys)
    g = flag.groupby([fk.dt.year.rename("year"), fk.dt.month.rename("month")]).agg(["size", "sum"]).reset_index()
    return [pd.DataFrame({"month": g.month, "repurchase_pct": pct(g["sum"], g["size"]).values, "cohort": g["size"], "year": g.year})]


@V11("Q117")
def _():
    f = fs()
    f = attach_product(f.loc[f.year.isin([2008, 2009]), ["StoreKey", "ProductKey", "year", "SalesAmount"]].copy())
    st = f.groupby(["StoreKey", "year"]).SalesAmount.sum().unstack().dropna()
    st = st[st[2009] < st[2008]]
    st["decline_pct"] = pct(st[2008] - st[2009], st[2008])
    st["store_rank"] = crank(st.decline_pct, "percentage")
    st = st.rename_axis("StoreKey").reset_index()
    top_stores = rp.select_top(st, [], [("decline_pct", "percentage", True)], 3)
    c = f[f.StoreKey.isin(top_stores.StoreKey)].groupby(["StoreKey", "ProductCategoryName", "year"], dropna=False).SalesAmount.sum().unstack(fill_value=0)
    c = c.reset_index()
    c["cat_decline"] = c[2008] - c[2009]
    sd = top_stores.set_index("StoreKey")
    c["share_pct"] = pct(c.cat_decline, c.StoreKey.map(sd[2008] - sd[2009]))
    c["cat_decline_pct"] = pct(c.cat_decline, c[2008].where(c[2008] != 0))
    c["cat_rank"] = crank(c.cat_decline, "amount", groups=c.StoreKey)
    worst = rp.select_top(c, ["StoreKey"], [("cat_decline", "amount", True)], 1)
    out = pd.DataFrame({"StoreKey": worst.StoreKey, "StoreName": worst.StoreKey.map(stores().StoreName),
                        "store_decline_pct": worst.StoreKey.map(sd.decline_pct), "category": worst.ProductCategoryName,
                        "category_decline": worst.cat_decline, "share_pct": worst.share_pct,
                        "store_decline": worst.StoreKey.map(sd[2008] - sd[2009]), "category_decline_pct": worst.cat_decline_pct,
                        "store_rank": worst.StoreKey.map(sd.store_rank), "category_rank": worst.cat_rank})
    return [out.sort_values(["store_decline_pct", "category_decline"], ascending=False)]


@V11("Q118")
def _():
    d = base("Q118")[0]
    f = fos()
    return [d.assign(total_2009=f.loc[f.year == 2009, "SalesAmount"].sum())]


@V11("Q122")
def _():
    d = base("Q122")[0]
    return [d.assign(rank=crank(d.co_orders, "count"))]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--eval-dir", required=True, help="read-only checkout of the bank PR whose wording these follow")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    only = [s.strip() for s in args.only.split(",") if s.strip()]
    ids = only or sorted(V, key=lambda s: int(s[1:]))
    sha = subprocess.run(["git", "-C", args.eval_dir, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    mpath = out / "manifest.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() and only else {}
    manifest["_source"] = {"eval_dir": args.eval_dir, "eval_commit": sha, "script": "scripts/recheck_v11.py"}
    for qid in ids:
        t0 = time.time()
        for old in out.glob(f"{qid}-*.csv"):
            old.unlink()
        entry = {"files": []}
        for i, d in enumerate(V[qid](), 1):
            p = out / f"{qid}-{i}.csv"
            rp.write(d, p)
            entry["files"].append({"ref": i, "mode": None, "path": p.name, "rows": len(d)})
        entry["seconds"] = round(time.time() - t0, 1)
        manifest[qid] = entry
        print(qid, entry, flush=True)
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
