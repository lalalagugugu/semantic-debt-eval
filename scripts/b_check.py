"""T05b cross-vendor spot check of low-discrimination criterion B
(main decisions/2026-10-16-low-discrimination-criteria.md, sections 1 and 4).

For each question it computes two results with pandas, independently of T06:
- before: the question's own convention (the recheck_pandas.py implementation
  that matched the finalized references, 751a29f);
- after: the key convention swapped for the common wrong reading the ruling
  names. Group 1 (first order): "new / returning / first-year = bought in the
  window", ignoring the first purchase. Group 2 (degenerate calendar): holiday
  and weekend swapped.
It records whether the two results are identical (criterion B hit).

Usage: uv run python scripts/b_check.py
Writes reports/T05b/b-check/<Qxx>-before.csv, <Qxx>-after.csv and summary.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recheck_pandas as rp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "T05b" / "b-check"

# Questions T06 flagged under criterion B, and the unflagged first-order sample.
FLAGGED = ["Q17", "Q29", "Q59", "Q68", "Q99", "Q76", "Q83"]
SAMPLE = ["Q26", "Q81", "Q96", "Q114", "Q116"]

AFTER = {}


def after(qid, group, swap):
    def deco(fn):
        AFTER[qid] = {"fn": fn, "group": group, "swap": swap}
        return fn
    return deco


def _swap_day_flag(d, col):
    """Group 2: read the weekend flag as the holiday flag and vice versa."""
    if col == "IsHoliday":
        return d.IsWorkDay.map({"WeekEnd": "Yes", "WorkDay": "No"})
    return d.IsHoliday.map({"Yes": "WeekEnd", "No": "WorkDay"})


def _dates_swapped(col):
    return rp.dates().assign(**{col: _swap_day_flag(rp.dates(), col)})


# ---------------- group 2: holiday <-> weekend ----------------

@after("Q17", 2, "周末 → 节假日")
def _():
    f = rp.fos()
    lab = f.DateKey.map(_dates_swapped("IsWorkDay").IsWorkDay)
    g = f.groupby(lab).SalesAmount.sum()
    return pd.DataFrame({"day_type": g.index, "sales": g.values, "pct": rp.pct(g.values, g.sum())})


@after("Q29", 2, "节假日 → 周末")
def _():
    daily = rp.fos().groupby("DateKey").SalesAmount.sum()
    lab = daily.index.map(_dates_swapped("IsHoliday").IsHoliday)
    m = daily.groupby(lab).mean()
    return rp.df_([[(m["Yes"] / m["No"] - 1) * 100]], ["pct_diff"])


@after("Q59", 2, "节假日 → 周末")
def _():
    d = rp.T("DimDate")
    return rp.df_([[int((d.IsWorkDay == "WeekEnd").sum())]], ["holidays"])


@after("Q68", 2, "节假日 → 周末")
def _():
    f = rp.fos()
    f = f[f.year == 2009]
    lab = f.DateKey.map(_dates_swapped("IsHoliday").IsHoliday)
    g = f.groupby(lab).agg(orders=("order", "nunique"), revenue=("SalesAmount", "sum"))
    return g.rename_axis("is_holiday").reset_index()


@after("Q99", 2, "周末 → 节假日")
def _():
    f = rp.attach_product(rp.fos()[["ProductKey", "DateKey", "SalesAmount"]].copy())
    d = f.groupby(["ProductCategoryName", "DateKey"], dropna=False).SalesAmount.sum().reset_index()
    d["we"] = d.DateKey.map(rp.dates().IsHoliday) == "Yes"
    g = d.groupby(["ProductCategoryName", "we"], dropna=False).SalesAmount.mean().unstack()
    return pd.DataFrame({"category": g.index, "weekend_avg": g[True].values, "weekday_avg": g[False].values,
                         "diff_pct": rp.pct(g[True] - g[False], g[False]).values})


# ---------------- group 1: first order ignored ----------------

@after("Q76", 1, "回头客 → 有购买的客户")
def _():
    f = rp.attach_product(rp.fos()[["ProductKey", "CustomerKey", "SalesAmount"]].copy())
    tot = f.groupby("ProductCategoryName", dropna=False).SalesAmount.sum()
    buyers = f[f.CustomerKey.notna()].groupby("ProductCategoryName", dropna=False).SalesAmount.sum()
    return pd.DataFrame({"category": tot.index, "repeat_pct": rp.pct(buyers.reindex(tot.index, fill_value=0), tot).values})


@after("Q83", 1, "2007 年首次购买 → 2007 年有购买")
def _():
    b = rp.buys()
    c07 = set(b[b.year == 2007].CustomerKey)
    c08 = c07 & set(b[b.year == 2008].CustomerKey)
    c09 = c08 & set(b[b.year == 2009].CustomerKey)
    return rp.df_([[len(c07), len(c08), len(c09)]], ["first_2007", "back_2008", "back_2009"])


@after("Q26", 1, "季度内首次购买 → 季度内有购买")
def _():
    b = rp.buys()
    b07 = b[b.year == 2007]
    g = b07.groupby("quarter").CustomerKey.nunique()
    return pd.DataFrame({"quarter": g.index, "customers": g.values})


@after("Q81", 1, "首次购买年份 → 有购买的年份（客户计入每个有购买的年份）")
def _():
    b = rp.buys()
    ltv = rp.fos().groupby("CustomerKey").SalesAmount.sum()
    cy = b[["CustomerKey", "year"]].drop_duplicates()
    cy["ltv"] = cy.CustomerKey.map(ltv)
    g = cy.groupby("year").ltv.agg(["size", "mean", "sum"])
    return pd.DataFrame({"cohort": g.index, "customers": g["size"].values, "avg_ltv": g["mean"].values,
                         "total_ltv": g["sum"].values})


@after("Q96", 1, "首次购买年份 → 有购买的年份")
def _():
    b = rp.buys()
    cy = b[["CustomerKey", "year"]].drop_duplicates()
    last_year = b.groupby("CustomerKey").year.max()
    came_back = cy.CustomerKey.map(last_year) > cy.year
    g = came_back.groupby(cy.year).agg(["size", "sum"])
    return pd.DataFrame({"cohort": g.index, "customers": g["size"].values, "returned": g["sum"].values,
                         "pct": rp.pct(g["sum"], g["size"]).values})


@after("Q114", 1, "窗口内首次购买 → 窗口内有购买")
def _():
    b = rp.buys()
    return pd.DataFrame({"month_end": rp.MONTH_ENDS.date,
                         "new_customers": [int(b.loc[rp._in_window(b.DateKey, t), "CustomerKey"].nunique())
                                           for t in rp.MONTH_ENDS]})


@after("Q116", 1, "首购月份 → 有购买的月份（以该月第一次购买为起点）")
def _():
    b = rp.buys()
    b = b.assign(month=b.DateKey.dt.to_period("M").dt.to_timestamp())
    start = b.groupby(["CustomerKey", "month"]).DateKey.min().rename("start").reset_index()
    start = start[start.start + pd.Timedelta(days=7) <= rp.TODAY]
    days = b[["CustomerKey", "DateKey"]].drop_duplicates()
    j = start.merge(days, on="CustomerKey")
    gap = (j.DateKey - j.start).dt.days
    rep = j[(gap >= 1) & (gap <= 7)][["CustomerKey", "month"]].drop_duplicates().assign(rep=True)
    s = start.merge(rep, on=["CustomerKey", "month"], how="left")
    s["rep"] = s.rep.notna()
    g = s.groupby("month").rep.agg(["size", "sum"])
    return pd.DataFrame({"first_month": g.index.date, "repurchase_pct": rp.pct(g["sum"], g["size"]).values})


def same(a, b):
    """Identical result sets: same shape, strings equal, numbers within 1e-9 relative."""
    if a.shape != b.shape:
        return False
    a = a.reset_index(drop=True)
    b = b.reset_index(drop=True)
    for ca, cb in zip(a.columns, b.columns):
        x, y = a[ca], b[cb]
        xn, yn = pd.to_numeric(x, errors="coerce"), pd.to_numeric(y, errors="coerce")
        if xn.notna().all() and yn.notna().all():
            if not np.allclose(xn.astype(float), yn.astype(float), rtol=1e-9, atol=1e-9, equal_nan=True):
                return False
        elif not (x.astype(object).where(x.notna(), "").astype(str).values
                  == y.astype(object).where(y.notna(), "").astype(str).values).all():
            return False
    return True


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for qid in FLAGGED + SAMPLE:
        before = rp.QS[qid]()
        a = AFTER[qid]
        aft = a["fn"]()
        # Questions with several refs: the B swap is checked against every before reading.
        hits = [same(bf, aft) for bf in before]
        for k, bf in enumerate(before, 1):
            bf.to_csv(OUT / f"{qid}-before-{k}.csv", index=False)
        aft.to_csv(OUT / f"{qid}-after.csv", index=False)
        summary[qid] = {"set": "flagged" if qid in FLAGGED else "sample", "group": a["group"], "swap": a["swap"],
                        "before_files": [f"{qid}-before-{k}.csv" for k in range(1, len(before) + 1)],
                        "after_file": f"{qid}-after.csv", "unchanged": hits, "b_hit": any(hits)}
        print(qid, summary[qid]["set"], "group", a["group"], "unchanged:", hits)
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
