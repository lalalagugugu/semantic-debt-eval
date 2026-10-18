"""Read scorer corpora (T13 export format, harness/scorer_corpus.py on PR #105) and run
the T05b checker over them.

Own decoder for the documented line format, so the checker never imports harness code:
typed cells {"$date"}, {"$datetime"}, {"$decimal"}, {"$float": nan|inf|-inf}; candidate is
a row set, "CANNOT_ANSWER" or {"exec_error": text}. Judge cases and cases without
references are skipped (pending in the harness, not scorer outputs).

    uv run python -m scorer_check.corpus run "$SEMDEBT_DATA_DIR/scorer-corpus/t13.jsonl" --out results.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
import time
from decimal import Decimal
from pathlib import Path

from .checker import CANNOT_ANSWER, ExecError, RulesError, score

_FLOATS = {"nan": math.nan, "inf": math.inf, "-inf": -math.inf}
_TAGS = {"$date": dt.date.fromisoformat, "$datetime": dt.datetime.fromisoformat,
         "$decimal": Decimal, "$float": _FLOATS.__getitem__}


def decode_value(v):
    if isinstance(v, dict):
        if len(v) != 1 or next(iter(v)) not in _TAGS:
            raise ValueError(f"not a typed value: {v!r}")
        (tag, text), = v.items()
        return _TAGS[tag](text)
    if isinstance(v, list):
        return [decode_value(x) for x in v]
    return v


def encode_value(v):
    if isinstance(v, dict):
        return v  # already typed
    if isinstance(v, float) and not math.isfinite(v):
        return {"$float": "nan" if math.isnan(v) else ("inf" if v > 0 else "-inf")}
    if isinstance(v, dt.datetime):
        return {"$datetime": v.isoformat()}
    if isinstance(v, dt.date):
        return {"$date": v.isoformat()}
    if isinstance(v, Decimal):
        return {"$decimal": str(v)}
    if isinstance(v, (list, tuple)):
        return [encode_value(x) for x in v]
    return v


def decode_candidate(c):
    if isinstance(c, dict):
        return ExecError(c["exec_error"])
    if isinstance(c, str):
        if c != CANNOT_ANSWER:
            raise ValueError(f"unexpected string candidate {c!r}")
        return c
    return decode_value(c)


def iter_cases(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                c = json.loads(line)
                c["candidate"] = decode_candidate(c["candidate"])
                c["refs"] = decode_value(c["refs"]) if c.get("refs") is not None else None
                yield c


def run_case(c):
    if c.get("judge") or c.get("refs") is None:
        return {"outcome": "skipped", "reason": "judge" if c.get("judge") else "no_refs", "seconds": 0.0}
    vt = c.get("value_types")
    if vt is not None and vt != [r.get("value_types") for r in c["rules"]]:
        return {"outcome": "error", "reason": "value_types differ from rules", "seconds": 0.0}
    t0 = time.perf_counter()
    try:
        r = score(c["candidate"], c["refs"], c["rules"])
        out = {"outcome": r.outcome, "reason": r.reason, "matched_ref": r.matched_ref}
    except (RulesError, TypeError, ValueError) as e:
        out = {"outcome": "error", "reason": f"{type(e).__name__}: {e}"}
    out["seconds"] = round(time.perf_counter() - t0, 4)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("corpus", nargs="+")
    r.add_argument("--out", required=True)
    r.add_argument("--only", default="", help="case_id substring filter")
    args = ap.parse_args(argv)
    results = []
    for path in args.corpus:
        for c in iter_cases(path):
            if args.only and args.only not in c["case_id"]:
                continue
            res = run_case(c)
            res["case_id"] = c["case_id"]
            exp = c.get("expected")
            if exp:
                ok = res["outcome"] == exp["outcome"] and (exp.get("reason") is None or res.get("reason") == exp["reason"]
                                                         or exp["outcome"] == "error")
                res["expected"] = exp
                res["as_expected"] = ok
                if not ok:
                    print("MISMATCH", c["case_id"], res, file=sys.stderr)
            results.append(res)
    Path(args.out).write_text("".join(json.dumps(x, ensure_ascii=False, default=str) + "\n" for x in results))
    counts = {}
    for x in results:
        counts[x["outcome"]] = counts.get(x["outcome"], 0) + 1
    print("cases", len(results), counts)
    checked = [x for x in results if "as_expected" in x]
    if checked:
        print("with expectations:", len(checked), "as expected:", sum(x["as_expected"] for x in checked))
    print("slowest 10:")
    for x in sorted(results, key=lambda x: -x["seconds"])[:10]:
        print(f"  {x['seconds']:8.3f}s  {x['case_id']}  {x['outcome']} {x.get('reason') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
