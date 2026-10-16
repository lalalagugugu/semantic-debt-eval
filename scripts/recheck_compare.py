"""T05b step 2: compare the pandas recomputation with refs/ (run only after T05
finalizes the references).

For every question reference it takes the effective rules (ref.rules replaces
the question rules wholesale), loads the reference CSV and every pandas
candidate for that reference (both purchase-event algorithms when they differ),
and checks result-set equality with the scorer tolerance:
max(0.005*|ref|, atol(kind)), atol = percentage 0.01 / ratio 1e-4 / amount 0.01 /
count and other 0. Identity strings compare exactly after strip. Columns are
mapped by value multiset (the pandas column order is not assumed to equal the
reference); percentage columns also try the fraction<->percent equivalence.

Usage: uv run python scripts/recheck_compare.py [--only Q74,Q79]
Writes reports/T05b/compare.json and prints one line per reference.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
PANDAS = ROOT / "reports" / "T05b" / "pandas"
ATOL = {"percentage": 0.01, "ratio": 1e-4, "amount": 0.01}


def load_questions():
    out = {}
    for f in ("questions/cube_100.yaml", "questions/new.yaml"):
        for qd in yaml.safe_load((ROOT / f).read_text())["questions"]:
            refs = []
            for r in qd["refs"]:
                refs.append({"path": r["result_path"], "interpretation": r["interpretation"],
                             "rules": r.get("rules") or qd["rules"]})
            out[qd["id"]] = {"refs": refs, "scoring": qd["scoring"]}
    return out


def numeric(s):
    return pd.to_numeric(s.replace({"": np.nan, "\\N": np.nan}), errors="coerce")


def close(a, b, kind):
    """Elementwise scorer tolerance; NULL equals NULL only."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    both_nan = np.isnan(a) & np.isnan(b)
    tol = np.maximum(0.005 * np.abs(b), ATOL.get(kind, 0.0))
    with np.errstate(invalid="ignore"):
        ok = np.abs(a - b) <= tol
    return both_nan | (ok & ~np.isnan(a) & ~np.isnan(b))


def col_variants(mine, kind):
    """Candidate encodings of a pandas column for one reference column."""
    num = numeric(mine.astype(str))
    if num.notna().sum() == mine.replace("", np.nan).notna().sum() and num.notna().any():
        vs = [("num", num)]
        if kind == "percentage":
            vs += [("num/100", num / 100), ("num*100", num * 100)]
        return vs
    return [("str", mine.fillna("").astype(str).str.strip())]


def compare_frames(ref, mine, rules):
    kinds = rules["value_kinds"]
    if ref.shape[1] != len(kinds):
        return {"ok": False, "why": f"ref has {ref.shape[1]} columns, rules declare {len(kinds)}"}
    if len(ref) != len(mine):
        return {"ok": False, "why": f"row count ref={len(ref)} pandas={len(mine)}"}
    if len(ref) == 0:
        return {"ok": True, "mapping": []}
    # Candidate columns per reference column, judged on sorted value multisets.
    options = []
    for j, kind in enumerate(kinds):
        rcol = ref.iloc[:, j]
        rnum = numeric(rcol)
        is_num = rnum.notna().sum() == rcol.replace("", np.nan).notna().sum() and rnum.notna().any()
        cands = []
        for c in mine.columns:
            for tag, v in col_variants(mine[c], kind):
                if is_num and tag.startswith("num"):
                    if close(np.sort(v.values.astype(float)), np.sort(rnum.values.astype(float)), kind).all():
                        cands.append((c, tag, v))
                elif not is_num and tag == "str":
                    if sorted(v) == sorted(rcol.fillna("").astype(str).str.strip()):
                        cands.append((c, tag, v))
        if not cands:
            return {"ok": False, "why": f"no pandas column matches ref column {j} ({ref.columns[j]}, {kind})",
                    "ref_head": ref.iloc[:5, j].tolist()}
        options.append(cands)
    for combo in itertools.islice(itertools.product(*options), 2000):
        if len({c for c, _, _ in combo}) != len(combo):
            continue
        res = match_rows(ref, combo, kinds)
        if res["ok"]:
            res["mapping"] = [f"{ref.columns[j]}<-{c}({t})" for j, (c, t, _) in enumerate(combo)]
            if rules.get("ordered"):
                res["order_note"] = "ordered=true: row order not checked here; see selection/output_order"
            return res
    return {"ok": False, "why": "every column matches as a multiset but rows do not align"}


def match_rows(ref, combo, kinds):
    str_idx = [j for j, (_, t, _) in enumerate(combo) if t == "str"]
    num_idx = [j for j, (_, t, _) in enumerate(combo) if t != "str"]
    r = pd.DataFrame({j: (ref.iloc[:, j].fillna("").astype(str).str.strip() if j in str_idx else numeric(ref.iloc[:, j]))
                      for j in range(len(combo))})
    m = pd.DataFrame({j: combo[j][2].reset_index(drop=True) for j in range(len(combo))})
    keys = str_idx + num_idx
    r = r.sort_values(keys, na_position="last").reset_index(drop=True)
    m = m.sort_values(keys, na_position="last").reset_index(drop=True)
    bad = np.zeros(len(r), bool)
    for j in str_idx:
        bad |= (r[j].values != m[j].values)
    for j in num_idx:
        bad |= ~close(m[j].values, r[j].values, kinds[j])
    if not bad.any():
        return {"ok": True}
    return {"ok": False, "why": f"{int(bad.sum())} rows differ after alignment",
            "ref_rows": r[bad].head(5).astype(str).values.tolist(), "pandas_rows": m[bad].head(5).astype(str).values.tolist()}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args(argv)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    qs = load_questions()
    manifest = json.loads((PANDAS / "manifest.json").read_text())
    report = {}
    for qid, qd in qs.items():
        if only and qid not in only:
            continue
        entries = []
        for i, ref in enumerate(qd["refs"], 1):
            refdf = pd.read_csv(ROOT / ref["path"], dtype=str, keep_default_na=False)
            files = [f for f in manifest.get(qid, {}).get("files", []) if f["ref"] == i]
            results = {}
            for f in files:
                mine = pd.read_csv(PANDAS / f["path"], dtype=str, keep_default_na=False)
                results[f["mode"] or "-"] = compare_frames(refdf, mine, ref["rules"])
            ok = any(r["ok"] for r in results.values())
            entries.append({"ref": ref["path"], "interpretation": ref["interpretation"], "match": ok, "by_mode": results})
            print(f"{qid}-{i} [{qd['scoring']}] {'MATCH' if ok else 'DIFF '} "
                  + "; ".join(f"{k}: {'ok' if v['ok'] else v['why']}" for k, v in results.items()))
        report[qid] = entries
    out = ROOT / "reports" / "T05b" / "compare.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
