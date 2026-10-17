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

Questions and refs are read from a read-only checkout of the finalized bank
(git worktree of origin/main), never from the shared $SEMDEBT_EVAL_DIR workspace.

One convention, one answer (main decisions/2026-10-17-one-convention-one-
answer.md): the empty product-group row is part of the answer, so its presence
or absence is a difference; purchase events use every row, so a ref tagged
"购买事件=SalesQuantity>0" has no pandas counterpart and is reported as such.

Usage: uv run python scripts/recheck_compare.py --eval-dir "$SEMDEBT_DATA_DIR/eval-ro-<sha>" [--only Q74,Q79]
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


# Ranked lists the pandas side truncates (judge examples without a fixed N):
# compare the reference against the same-length pandas prefix.
TRUNCATED = {"Q33", "Q97"}
# Interpretation suffix of the (withdrawn) "no empty product-attribute group" variant refs.
NULL_GROUP_VARIANT = "按产品属性分组时不展示空属性组"
EVENT_TAG = "购买事件="


def event_mode(interp):
    """Pandas mode a ref's purchase-event tag selects (None = either / untagged)."""
    if EVENT_TAG not in interp or "结果相同" in interp.split(EVENT_TAG)[1].split("；")[0]:
        return None
    tag = interp.split(EVENT_TAG)[1]
    return "qty_pos" if tag.startswith("SalesQuantity>0") else "all" if tag.startswith("全部行") else None


def load_questions(eval_root=ROOT):
    out = {}
    for f in ("questions/cube_100.yaml", "questions/new.yaml"):
        for qd in yaml.safe_load((Path(eval_root) / f).read_text())["questions"]:
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
    import subprocess
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--eval-dir", required=True, help="read-only checkout of the finalized question bank")
    args = ap.parse_args(argv)
    eval_root = Path(args.eval_dir)
    sha = subprocess.run(["git", "-C", str(eval_root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    qs = load_questions(eval_root)
    manifest = json.loads((PANDAS / "manifest.json").read_text())
    report = {"_source": {"eval_dir": str(eval_root), "eval_commit": sha,
                          "pandas_source": manifest.get("_source")}}
    for qid, qd in qs.items():
        if only and qid not in only:
            continue
        entries = []
        for i, ref in enumerate(qd["refs"], 1):
            # The reference CSVs write NULL as \N; the pandas CSVs write it as an empty field.
            refdf = pd.read_csv(eval_root / ref["path"], dtype=str, keep_default_na=False).replace("\\N", "")
            allfiles = manifest.get(qid, {}).get("files", [])
            files = [f for f in allfiles if f["ref"] == i]
            interp = ref["interpretation"]
            base = None
            if not files and NULL_GROUP_VARIANT in interp:
                # Withdrawn "no empty group row" variant, if still present: compare the base
                # output, which keeps the row; a missing row now counts as a difference.
                stem = interp.split(NULL_GROUP_VARIANT)[0].rstrip("；")
                base = next(k for k, r in enumerate(qd["refs"], 1) if r["interpretation"] == stem)
                files = [f for f in allfiles if f["ref"] == base]
            if not files and EVENT_TAG in interp:
                # The bank splits purchase-event algorithms into separate refs; the pandas side
                # keeps both modes under one ref. Find the ref with the same interpretation stem.
                stem = interp.split("；" + EVENT_TAG)[0]
                base = next(k for k, r in enumerate(qd["refs"], 1)
                            if r["interpretation"].split("；" + EVENT_TAG)[0] == stem
                            and any(f["ref"] == k for f in allfiles))
                files = [f for f in allfiles if f["ref"] == base]
            results = {}
            if event_mode(interp) == "qty_pos":
                files = []
                results["-"] = {"ok": False, "why": "SalesQuantity>0 ref: pandas computes purchase events on every row only (2026-10-17)"}
            for f in files:
                mine = pd.read_csv(PANDAS / f["path"], dtype=str, keep_default_na=False)
                if qid in TRUNCATED and len(mine) > len(refdf):
                    mine = mine.head(len(refdf))
                results[f["mode"] or "-"] = compare_frames(refdf, mine, ref["rules"])
            ok = any(r["ok"] for r in results.values())
            if not results:
                results["-"] = {"ok": False, "why": "no pandas output for this reference"}
            entries.append({"ref": ref["path"], "interpretation": ref["interpretation"], "match": ok,
                            "pandas_ref": base or i, "by_mode": results})
            print(f"{qid}-{i} [{qd['scoring']}] {'MATCH' if ok else 'DIFF '} "
                  + "; ".join(f"{k}: {('ok ' + v.get('note', '')).strip() if v['ok'] else v['why']}" for k, v in results.items()))
        report[qid] = entries
    out = ROOT / "reports" / "T05b" / "compare.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
