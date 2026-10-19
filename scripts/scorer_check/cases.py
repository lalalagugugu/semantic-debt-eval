"""Shared stress and spec-coverage cases for scorer spec v2 (section 7, items 2 and 4).

Each case is one corpus line (same layout as the T13 corpus, harness/scorer_corpus.py)
plus "expected": {"outcome", "reason"} and "spec": the clause it exercises. Written by
T05b from the spec text, independent of either scorer implementation.

    uv run python -m scorer_check.cases --out "$SEMDEBT_DATA_DIR/scorer-corpus/t05b-cases.jsonl"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
from decimal import Decimal
from pathlib import Path

from .corpus import encode_value

CASES = []


def rules(kinds, types, required, ordered=False, top_n=None, ties=(), **extra):
    r = {"ordered": ordered, "top_n": top_n, "tie_columns": list(ties), "value_kinds": list(kinds),
         "value_types": list(types), "required_columns": list(required)}
    r.update(extra)
    return r


def case(cid, spec, candidate, refs, rules_list, outcome, reason=None, note=""):
    if isinstance(rules_list, dict):
        rules_list = [rules_list]
    CASES.append({"case_id": f"t05b/{cid}", "source": "t05b", "spec": spec, "note": note,
                  "candidate": candidate, "refs": refs, "rules": rules_list,
                  "value_types": [r["value_types"] for r in rules_list],
                  "expected": {"outcome": outcome, "reason": reason}})


def blocks_for(ranks, groups=None):
    """rankings.blocks from competition ranks (optionally per group)."""
    groups = groups or [[] for _ in ranks]
    out = {}
    for g, r in zip(groups, ranks):
        out.setdefault((tuple(g), r), 0)
        out[(tuple(g), r)] += 1
    res = []
    for g in sorted({k[0] for k in out}):
        rs = sorted(r for (gg, r) in out if gg == g)
        for d, r in enumerate(rs, 1):
            res.append({"group": list(g), "rank": r, "dense": d, "size": out[(g, r)]})
    return res


# ---------------------------------------------------------------------------
# 0. Outcomes that are not row sets (spec 1)
# ---------------------------------------------------------------------------
R1 = rules(["count"], ["UInt64"], [0])
case("outcome/refused", "1.2", "CANNOT_ANSWER", [[[5]]], R1, "refused")
case("outcome/exec_error", "1.2", {"exec_error": "Code: 47. Unknown identifier"}, [[[5]]], R1, "exec_error")
case("outcome/empty-vs-rows", "1.2, 6.6", [], [[[5]]], R1, "wrong", "row_count")

# ---------------------------------------------------------------------------
# 1. Column mapping (spec 4) and extra columns
# ---------------------------------------------------------------------------
R2 = rules(["other", "amount"], ["String", "Float64"], [0, 1])
ref2 = [["Audio", 100.0], ["TV", 250.5]]
case("cols/extra-column-ok", "4.1", [["TV", 250.5, "x"], ["Audio", 100.0, "y"]], [ref2], R2, "correct")
case("cols/reordered-ok", "4.1", [[250.5, "TV"], [100.0, "Audio"]], [ref2], R2, "correct")
case("cols/missing-required", "4.2, 6.6", [["TV"], ["Audio"]], [ref2], R2, "wrong", "missing_columns")
case("cols/non-required-ignored", "4.2",
     [["TV"], ["Audio"]], [ref2], rules(["other", "amount"], ["String", "Float64"], [0]), "correct")
case("cols/one-column-for-two-required", "4.2",
     [["a"], ["b"]], [[["a", "a"], ["b", "b"]]], rules(["other", "other"], ["String", "String"], [0, 1]),
     "wrong", "values", "two required columns cannot both map to one candidate column; the merged pair would be 'a a'")

# ---------------------------------------------------------------------------
# 2. Numbers (spec 3.3, 11.1)
# ---------------------------------------------------------------------------
Ramt = rules(["amount"], ["Float64"], [0])
case("num/rel-within", "3.3", [[100.4]], [[[100.0]]], Ramt, "correct")
case("num/rel-outside", "3.3", [[100.6]], [[[100.0]]], Ramt, "wrong", "values")
case("num/asym-cand-low-ok", "11.1", [[100.0]], [[[100.502]]], rules(["other"], ["Float64"], [0]), "correct",
     note="|100-100.502|=0.502 <= 0.005*100.502")
case("num/asym-swapped-wrong", "11.1", [[100.502]], [[[100.0]]], rules(["other"], ["Float64"], [0]), "wrong", "values",
     note="0.502 > 0.005*100")
case("num/amount-atol", "3.3", [[0.009]], [[[0.0]]], Ramt, "correct")
case("num/amount-atol-out", "3.3", [[0.011]], [[[0.0]]], Ramt, "wrong", "values")
Rpct = rules(["percentage"], ["Float64"], [0])
case("num/pct-fraction-x100", "3.3 (x100)", [[0.1316]], [[[13.16]]], Rpct, "correct")
case("num/pct-percent-div100", "3.3 (/100)", [[13.16]], [[[0.1316]]], rules(["ratio"], ["Float64"], [0]), "correct")
case("num/pct-wrong", "3.3", [[0.1416]], [[[13.16]]], Rpct, "wrong", "values")
case("num/pct-zero-ref-atol", "3.3", [[0.009]], [[[0.0]]], Rpct, "correct", note="percent units: atol 0.0001 as fraction = 0.01")
case("num/pct-zero-ref-no-x100", "3.3", [[0.5]], [[[0.0]]], Rpct, "wrong", "values", note="zero reference: no 100x guess")
Rcnt = rules(["count"], ["UInt64"], [0])
case("num/count-exact", "3.3", [[100]], [[[100]]], Rcnt, "correct")
case("num/amount-no-x100", "12.1 (negative)", [[1234.0]], [[[12.34]]], Ramt, "wrong", "values", note="amount: no x100 / 100")
case("num/amount-no-div100", "12.1 (negative)", [[0.1234]], [[[12.34]]], Ramt, "wrong", "values")
case("num/other-float-x100", "12.1 (other, non-integer type)", [[0.1316]], [[[13.16]]], rules(["other"], ["Float64"], [0]), "correct")
case("num/other-float-div100", "12.1 (other, non-integer type)", [[13.16]], [[[0.1316]]], rules(["other"], ["Nullable(Float64)"], [0]), "correct")
case("num/count-float-no-x100", "12.1 (negative)", [[10000.0]], [[[100.0]]], rules(["count"], ["Float64"], [0]), "wrong", "values")
case("num/int-other-exact", "12.2", [[2009]], [[[2008]]], rules(["other"], ["UInt16"], [0]), "wrong", "values",
     note="integer reference type: exact, although within 0.5%")
case("num/int-amount-exact", "12.2", [[100001]], [[[100000]]], rules(["amount"], ["Int64"], [0]), "wrong", "values")
case("num/int-other-float-equal", "12.2", [[2008.0]], [[[2008]]], rules(["other"], ["UInt16"], [0]), "correct")
case("num/int-other-no-x100", "12.1, 12.2", [[1300]], [[[13]]], rules(["other"], ["Int32"], [0]), "wrong", "values")
case("num/long-table-years-shifted", "12.2", [["Audio", 2008, 48.6], ["Audio", 2009, 53.2], ["Audio", 2007, 51.0]],
     [[["Audio", 2007, 48.6], ["Audio", 2008, 53.2], ["Audio", 2009, 51.0]]],
     rules(["other", "other", "percentage"], ["String", "UInt16", "Float64"], [0, 1, 2]), "wrong", "values")
case("num/count-exact-float-equal", "3.3", [[100.0]], [[[100]]], Rcnt, "correct")
case("num/count-exact-off", "3.3", [[100.4]], [[[100]]], Rcnt, "wrong", "values", note="integer count: exact, no 0.5%")
case("num/count-exact-no-x100", "3.3", [[10000]], [[[100]]], Rcnt, "wrong", "values")
case("num/count-nullable-lowcard-int", "3.3", [[101]], [[[100]]],
     rules(["count"], ["Nullable(LowCardinality(UInt32))"], [0]), "wrong", "values")
case("num/count-float-type-tolerance", "3.3", [[100.4]], [[[100.0]]], rules(["count"], ["Float64"], [0]), "correct",
     note="count with a non-integer type falls back to the tolerance rule")
case("num/fast-path-lossless", "6.2 (clarification 5)", [[0.0000002]], [[[0.0000001]]], rules(["other"], ["Float64"], [0]),
     "wrong", "values", note="quantizing to 6 places would make both 0.000000; the tolerance rule (atol 0 for other) says unequal")
case("num/nan-never-equal", "3.3", [[{"$float": "nan"}]], [[[{"$float": "nan"}]]], Ramt, "wrong", "values")
case("num/inf-never-equal", "3.3", [[{"$float": "inf"}]], [[[{"$float": "inf"}]]], Ramt, "wrong", "values")
case("num/null-vs-zero", "3.2", [[None]], [[[0.0]]], Ramt, "wrong", "values")
case("num/zero-vs-null", "3.2", [[0.0]], [[[None]]], rules(["amount"], ["Nullable(Float64)"], [0]), "wrong", "values")
case("num/null-vs-null", "3.2", [[None]], [[[None]]], rules(["amount"], ["Nullable(Float64)"], [0]), "correct")
case("num/decimal-ok", "3.3", [[{"$decimal": "12.30"}]], [[[12.3]]], Ramt, "correct")
case("num/formatted-string", "5.8", [["1,234.50"]], [[[1234.5]]], Ramt, "wrong", "values")
case("num/percent-string", "5.8", [["13.16%"]], [[[13.16]]], Rpct, "wrong", "values")
case("num/wan-units", "5.8", [[12.345]], [[[123450.0]]], Ramt, "wrong", "values", note="amount in units of 10,000")
case("num/decline-negative", "5.8", [[-500.0]], [[[500.0]]], Ramt, "wrong", "values")

# ---------------------------------------------------------------------------
# 3. Strings and NULL (3.1, 3.2)
# ---------------------------------------------------------------------------
Rs = rules(["other"], ["String"], [0])
case("str/strip-ok", "3.1", [["  Audio "]], [[["Audio"]]], Rs, "correct")
case("str/case-sensitive", "3.1", [["audio"]], [[["Audio"]]], Rs, "wrong", "values")
case("str/translated-label", "5.8", [["音频"]], [[["Audio"]]], Rs, "wrong", "values")
case("str/null-vs-empty", "3.2", [[None]], [[["x"]]], Rs, "wrong", "values")
case("str/nan-string-vs-null", "3.2", [["NaN"]], [[[None]]],
     rules(["other"], ["Nullable(Float64)"], [0]), "wrong", "values", note="numeric column: no empty-label relief")

# ---------------------------------------------------------------------------
# 4. Identifiers (3.4)
# ---------------------------------------------------------------------------
Rid = rules(["other", "amount"], ["Int32", "Float64"], [0, 1], identifier_columns=[0])
case("id/int-vs-string", "3.4 (cand string)", [["10000", 5.0]], [[[10000, 5.0]]], Rid, "correct")
Rid_s = rules(["other", "amount"], ["String", "Float64"], [0, 1], identifier_columns=[0])
case("id/string-vs-int", "3.4 (ref string)", [[10000, 5.0]], [[["10000", 5.0]]], Rid_s, "correct")
case("id/leading-zero", "3.4", [["010000", 5.0]], [[[10000, 5.0]]], Rid, "wrong", "values")
case("id/decimal-point", "3.4", [["10000.0", 5.0]], [[[10000, 5.0]]], Rid, "wrong", "values")
case("id/no-tolerance", "3.4", [[10001, 5.0]], [[[10000, 5.0]]], Rid, "wrong", "values", note="within 0.5% but codes are exact")
case("id/no-percent", "3.4", [[100, 5.0]], [[[1, 5.0]]], Rid, "wrong", "values")
case("id/whitespace", "3.4", [[" 10000 ", 5.0]], [[[10000, 5.0]]], Rid, "correct")

# ---------------------------------------------------------------------------
# 5. Dates (3.5), both directions
# ---------------------------------------------------------------------------
Rd = rules(["other", "amount"], ["Date", "Float64"], [0, 1])
refd = [["2009-12-01", 5.0]]
case("date/cand-date-obj", "3.5", [[{"$date": "2009-12-01"}, 5.0]], [refd], Rd, "correct")
case("date/cand-midnight-obj", "3.5", [[{"$datetime": "2009-12-01T00:00:00"}, 5.0]], [refd], Rd, "correct")
case("date/cand-midnight-str", "3.5", [["2009-12-01 00:00:00", 5.0]], [refd], Rd, "correct")
case("date/ref-obj-cand-str", "3.5 (reverse)", [["2009-12-01", 5.0]], [[[{"$date": "2009-12-01"}, 5.0]]], Rd, "correct")
case("date/ref-midnight-cand-date", "3.5 (reverse)", [[{"$date": "2009-12-01"}, 5.0]],
     [[[{"$datetime": "2009-12-01T00:00:00"}, 5.0]]], rules(["other", "amount"], ["DateTime", "Float64"], [0, 1]), "correct")
case("date/non-midnight", "3.5", [[{"$datetime": "2009-12-01T08:00:00"}, 5.0]], [refd], Rd, "wrong", "values")
case("date/tz-aware", "3.5", [[{"$datetime": "2009-12-01T00:00:00+00:00"}, 5.0]], [refd], Rd, "wrong", "values")
case("date/period-month", "3.5, 5.8", [["2009-12", 5.0]], [refd], Rd, "wrong", "values")
case("date/quarter-label", "3.5, 5.8", [["2009-Q1", 5.0]], [[["Q1", 5.0]]],
     rules(["other", "amount"], ["String", "Float64"], [0, 1]), "wrong", "values")
case("date/quarter-number", "5.8", [[1, 5.0]], [[["Q1", 5.0]]],
     rules(["other", "amount"], ["String", "Float64"], [0, 1]), "wrong", "values")
case("date/iso-T-string", "12.10", [["2009-12-01T00:00:00", 5.0]], [refd], Rd, "correct")
case("date/zero-fraction", "12.10", [["2009-12-01 00:00:00.000", 5.0]], [refd], Rd, "correct")
case("date/T-zero-fraction", "12.10", [["2009-12-01T00:00:00.000000", 5.0]], [refd], Rd, "correct")
case("date/nonzero-fraction", "12.10 (negative)", [["2009-12-01 00:00:00.500", 5.0]], [refd], Rd, "wrong", "values")
case("date/in-identifier", "12.10", [["2009-12-01 00:00:00", 5.0]], [refd],
     rules(["other", "amount"], ["Date", "Float64"], [0, 1], identifier_columns=[0]), "correct")

# ---------------------------------------------------------------------------
# 6. Reference-side empty labels (3.6), positive and both negatives
# ---------------------------------------------------------------------------
Re = rules(["other", "amount"], ["Nullable(String)", "Float64"], [0, 1])
refe = [[None, 10.0], ["Audio", 20.0]]
case("empty/ref-null-cand-label", "3.6", [["Unknown", 10.0], ["Audio", 20.0]], [refe], Re, "correct")
case("empty/ref-null-cand-null", "3.6, 3.2", [[None, 10.0], ["Audio", 20.0]], [refe], Re, "correct")
case("empty/ref-empty-str-cand-label", "3.6", [["(blank)", 10.0], ["Audio", 20.0]],
     [[["", 10.0], ["Audio", 20.0]]], Re, "correct")
case("empty/cand-uses-other-label", "3.6", [["Audio", 10.0], ["Audio", 20.0]], [refe], Re, "wrong", "values")
case("empty/reverse-not-relaxed", "3.6 (reverse)", [[None, 10.0], [None, 20.0]], [refe], Re, "wrong", "values",
     note="reference has a real label, candidate blank")
case("empty/ref-empty-cand-null", "12.9", [[None, 10.0], ["Audio", 20.0]], [[["", 10.0], ["Audio", 20.0]]], Re, "correct")
case("empty/date-col-not-relaxed", "12.9 (negative)", [["unknown", 1.0]], [[[None, 1.0]]],
     rules(["other", "amount"], ["Nullable(Date)", "Float64"], [0, 1]), "wrong", "values")
case("empty/identifier-not-relaxed", "12.9 (negative)", [["x", 1.0]], [[[None, 1.0]]],
     rules(["other", "amount"], ["Nullable(String)", "Float64"], [0, 1], identifier_columns=[0]), "wrong", "values")
case("empty/numeric-col-not-relaxed", "3.6", [["x"]], [[[None]]],
     rules(["amount"], ["Nullable(Float64)"], [0]), "wrong", "values")

# ---------------------------------------------------------------------------
# 7. Names split / merged (3.7, 11.2): both directions, both orders
# ---------------------------------------------------------------------------
Rfull = rules(["other", "amount"], ["String", "Float64"], [0, 1])
reff = [["Ann Lee", 1.0], ["Bo Chen", 2.0]]
case("name/cand-split", "3.7 (cand split)", [["Ann", "Lee", 1.0], ["Bo", "Chen", 2.0]], [reff], Rfull, "correct")
case("name/cand-split-reversed-cols", "3.7 (cand split, other order)", [["Lee", "Ann", 1.0], ["Chen", "Bo", 2.0]], [reff], Rfull, "correct")
Rsplit = rules(["other", "other", "amount"], ["String", "String", "Float64"], [0, 1, 2])
refs_ = [["Ann", "Lee", 1.0], ["Bo", "Chen", 2.0]]
case("name/ref-split", "3.7 (ref split), 11.2", [["Ann Lee", 1.0], ["Bo Chen", 2.0]], [refs_], Rsplit, "correct")
case("name/ref-split-reversed", "3.7 (ref split, other order)", [["Lee Ann", 1.0], ["Chen Bo", 2.0]], [refs_], Rsplit, "correct")
case("name/ref-split-separate-ok", "4.1", [["Lee", "Ann", 1.0], ["Chen", "Bo", 2.0]], [refs_], Rsplit, "correct")
case("name/comma", "3.7 (negative)", [["Lee, Ann", 1.0], ["Chen, Bo", 2.0]], [refs_], Rsplit, "wrong", "values")
case("name/middle-name", "3.7 (negative)", [["Ann M Lee", 1.0], ["Bo Chen", 2.0]], [reff], Rfull, "wrong", "values")
case("name/merge-needs-both-required", "11.2 (negative)", [["Ann Lee", 1.0], ["Bo Chen", 2.0]], [refs_],
     rules(["other", "other", "amount"], ["String", "String", "Float64"], [0, 2]), "wrong", "values",
     note="only one of the two is required: compared as a single column")
case("name/early-reject-counts-merge-as-one", "6.6, 11.2", [["Ann Lee", 1.0], ["Bo Chen", 2.0]], [refs_], Rsplit, "correct",
     note="3 required columns, candidate has 2: not an early reject")
case("name/mixed-order-rows", "12.8 (negative)", [["Ann Lee", 1.0], ["Chen Bo", 2.0]], [refs_], Rsplit, "wrong", "values",
     note="one join order per answer")
case("name/null-part", "12.8 (negative)", [["Ann", None, 1.0], ["Bo", "Chen", 2.0]], [reff], Rfull, "wrong", "values")
sel_name = {"version": 1, "output_order": [], "stages": [
    {"parent": None, "where": [], "group_columns": [2], "object_columns": [0, 1],
     "order_by": [{"column": 3, "descending": True}], "n": 1}]}
Rseln = rules(["other", "other", "other", "amount"], ["String", "String", "String", "Float64"], [0, 1, 2, 3], selection=sel_name)
refseln = [["Ann", "Lee", "US", 9.0], ["Bo", "Chen", "CN", 8.0], ["Cy", "Wu", "CN", 8.0]]
case("name/selection-identity-merged", "12.8 (selection identity)", [["Ann Lee", "US", 9.0], ["Cy Wu", "CN", 8.0]],
     [refseln], Rseln, "correct")
case("name/selection-identity-wrong", "12.8, 13.2 (negative)", [["Ann Lee", "US", 9.0], ["Cy Chen", "CN", 8.0]],
     [refseln], Rseln, "wrong", "selection", note="a wrong object in a group is a selection problem (13.2)")
case("name/selection-identity-two-boundary", "12.8, 5.7 (negative)", [["Ann Lee", "US", 9.0], ["Cy Wu", "CN", 8.0], ["Bo Chen", "CN", 8.0]],
     [refseln], Rseln, "wrong", "selection")
case("name/identifier-not-split", "12.8 (negative)", [["10", "000", 1.0]], [[["10 000", 1.0]]],
     rules(["other", "amount"], ["String", "Float64"], [0, 1], identifier_columns=[0]), "wrong", "values")

# ---------------------------------------------------------------------------
# 8. Row sets (5.1, 5.2)
# ---------------------------------------------------------------------------
R3 = rules(["other", "count"], ["String", "UInt64"], [0, 1])
ref3 = [["a", 1], ["b", 2], ["b", 2]]
case("rows/multiset-dup-ok", "5.1", [["b", 2], ["a", 1], ["b", 2]], [ref3], R3, "correct")
case("rows/multiset-dup-wrong", "5.1", [["b", 2], ["a", 1], ["a", 1]], [ref3], R3, "wrong", "values")
case("rows/extra-row", "5.1, 6.6", [["b", 2.0], ["a", 1.0], ["b", 2.0], ["c", 3.0]], [[["a", 1.0], ["b", 2.0], ["b", 2.0]]],
     rules(["other", "amount"], ["String", "Float64"], [0, 1]), "wrong", "row_count")
case("rows/extra-row-count-col", "5.1, 5.4", [["b", 2], ["a", 1], ["b", 2], ["c", 3]], [ref3], R3, "wrong", None,
     note="with a required count column the row count alone cannot reject (a zero group could be extra); judged at matching")
Rord = rules(["other", "amount"], ["String", "Float64"], [0, 1], ordered=True,
             order_by=[{"column": 1, "descending": True}])
refo = [["a", 30.0], ["b", 20.0], ["c", 20.0], ["d", 10.0]]
case("order/ok", "5.2", [["a", 30.0], ["b", 20.0], ["c", 20.0], ["d", 10.0]], [refo], Rord, "correct")
case("order/within-block-swap-ok", "5.2", [["a", 30.0], ["c", 20.0], ["b", 20.0], ["d", 10.0]], [refo], Rord, "correct")
case("order/cross-block-swap", "5.2", [["b", 20.0], ["a", 30.0], ["c", 20.0], ["d", 10.0]], [refo], Rord, "wrong", "order")
Rord2 = rules(["other"], ["String"], [0], ordered=True, order_by=[{"column": 1, "descending": True}])
Rord2["value_kinds"] = ["other", "amount"]
Rord2["value_types"] = ["String", "Float64"]
case("order/key-not-required", "2 (order_by on a hidden column), 5.2",
     [["a"], ["c"], ["b"], ["d"]], [refo], Rord2, "correct")
case("order/key-not-required-wrong", "5.2", [["d"], ["c"], ["b"], ["a"]], [refo], Rord2, "wrong", "order")
case("order/quantized-tie", "5.2", [["y", 1.0], ["x", 1.0]], [[["x", 1.004], ["y", 1.001]]], rules(
    ["other", "amount"], ["String", "Float64"], [0, 1], ordered=True, order_by=[{"column": 1, "descending": True}]),
    "correct", note="1.004 and 1.001 quantize to 1.00 (amount, 2 places): one block")

# ---------------------------------------------------------------------------
# 9. Top-N (5.3)
# ---------------------------------------------------------------------------
Rtop = rules(["other", "amount"], ["String", "Float64"], [0, 1], ordered=True, top_n=3, ties=[1],
             order_by=[{"column": 1, "descending": True}])
reft = [["a", 9.0], ["b", 8.0], ["c", 7.0], ["d", 7.0], ["e", 7.0]]
case("top/boundary-any-member", "5.3", [["a", 9.0], ["b", 8.0], ["e", 7.0]], [reft], Rtop, "correct")
case("top/missing-prefix", "5.3", [["a", 9.0], ["c", 7.0], ["d", 7.0]], [reft], Rtop, "wrong", "values")
case("top/full-group", "5.3", reft, [reft], Rtop, "wrong", "top_n_full_group")
case("top/too-many-not-full", "5.3", [["a", 9.0], ["b", 8.0], ["c", 7.0], ["d", 7.0]], [reft], Rtop, "wrong", "row_count")
case("top/boundary-duplicated", "5.3", [["a", 9.0], ["b", 8.0], ["b", 8.0]], [reft], Rtop, "wrong", "values")
case("top/order-wrong", "5.3, 5.2", [["b", 8.0], ["a", 9.0], ["c", 7.0]], [reft], Rtop, "wrong", "order")
case("top/domain-smaller-than-n", "5.3", [["a", 9.0]], [[["a", 9.0]]], Rtop, "correct")

# ---------------------------------------------------------------------------
# 10. Zero-count groups (5.4), both directions and the exclusions
# ---------------------------------------------------------------------------
Rz = rules(["other", "count", "amount"], ["String", "UInt64", "Nullable(Float64)"], [0, 1, 2])
refz = [["Q1", 5, 10.0], ["Q2", 0, None], ["Q3", 2, 4.0]]
case("zero/ref-has-cand-omits", "5.4 (ref extra)", [["Q1", 5, 10.0], ["Q3", 2, 4.0]], [refz], Rz, "correct")
case("zero/cand-has-extra", "5.4 (cand extra)", [["Q1", 5, 10.0], ["Q3", 2, 4.0], ["Q2", 0, None], ["Q4", 0, 0.0]],
     [[["Q1", 5, 10.0], ["Q3", 2, 4.0]]], Rz, "correct")
case("zero/nonzero-other-numeric", "5.4 (negative)", [["Q1", 5, 10.0]], [[["Q1", 5, 10.0], ["Q2", 0, 3.0]]], Rz,
     "wrong", "row_count", note="count 0 but amount 3: not a zero group")
case("zero/identifier-not-required-zero", "5.4", [["Q1", 5, 10.0]],
     [[["Q1", 5, 10.0], ["Q9", 0, 0.0]]], rules(["other", "count", "amount"], ["Int32", "UInt64", "Float64"], [0, 1, 2],
                                                   identifier_columns=[0]), "correct")
case("zero/only-count-kind", "5.4 (negative)", [["Q1", 5, 10.0]], [[["Q1", 5, 10.0], ["Q2", 0, 0.0]]],
     rules(["other", "other", "amount"], ["String", "UInt64", "Float64"], [0, 1, 2]), "wrong", "row_count")
case("zero/not-in-top-n", "5.4 (Top-N excluded)", [["a", 5]],
     [[["a", 5], ["b", 0]]], rules(["other", "count"], ["String", "UInt64"], [0, 1], top_n=2, ties=[1]),
     "wrong", "row_count")
Rzr = rules(["other", "count", "other"], ["String", "UInt64", "UInt64"], [0, 1, 2], rank_columns=[2],
            rankings=[{"column": 2, "group_columns": [], "object_columns": [0], "prefix": True, "blocks": blocks_for([1, 2])}])
case("zero/rank-column-excluded", "12.11", [["a", 5, 1]], [[["a", 5, 1], ["b", 0, 2]]], Rzr, "correct",
     note="the rank column is not one of the 'other numbers' that must be 0")
case("zero/two-count-columns", "12.11 (negative)", [["a", 5, 1]], [[["a", 5, 1], ["b", 0, 3]]],
     rules(["other", "count", "count"], ["String", "UInt64", "UInt64"], [0, 1, 2]), "wrong", "row_count",
     note="both count columns must be 0")
case("zero/extra-wrong-value", "5.4 (negative)", [["Q1", 5, 10.0], ["Q3", 2, 4.0], ["Q5", 1, 0.0]],
     [[["Q1", 5, 10.0], ["Q3", 2, 4.0]]], Rz, "wrong", "values")

# ---------------------------------------------------------------------------
# 11. Unordered pairs (5.5)
# ---------------------------------------------------------------------------
Rp = rules(["other", "other", "other", "other", "count"], ["Int32", "String", "Int32", "String", "UInt64"],
           [1, 3, 4], unordered_pairs=[{"left": [0, 1], "right": [2, 3]}], identifier_columns=[0, 2])
refp = [[1, "A", 2, "B", 10], [3, "C", 4, "D", 7]]
case("pair/as-is", "5.5", [["A", "B", 10], ["C", "D", 7]], [refp], Rp, "correct")
case("pair/swapped-some-rows", "5.5 (swap)", [["B", "A", 10], ["C", "D", 7]], [refp], Rp, "correct")
case("pair/wrong-partner", "5.5 (negative)", [["A", "D", 10], ["C", "B", 7]], [refp], Rp, "wrong", "values")
Rp2 = rules(["other", "other", "other", "other", "count"], ["Int32", "String", "Int32", "String", "UInt64"],
            [0, 1, 2, 3, 4], unordered_pairs=[{"left": [0, 1], "right": [2, 3]}], identifier_columns=[0, 2])
case("pair/half-swapped", "5.5 (negative)", [[2, "A", 1, "B", 10], [3, "C", 4, "D", 7]], [refp], Rp2, "wrong", "values",
     note="keys swapped but names not")
case("pair/both-swapped", "5.5", [[2, "B", 1, "A", 10], [3, "C", 4, "D", 7]], [refp], Rp2, "correct")

# ---------------------------------------------------------------------------
# 12. Rank styles (5.9)
# ---------------------------------------------------------------------------
def rank_rules(n_rows_ranks, ordered=False, top_n=None, prefix=True):
    return rules(["other", "amount", "other"], ["String", "Float64", "UInt64"], [0, 2], ordered=ordered,
                 top_n=top_n, ties=[1] if top_n else [],
                 order_by=[{"column": 1, "descending": True}] if ordered else None,
                 rank_columns=[2], rankings=[{"column": 2, "group_columns": [], "object_columns": [0],
                                               "prefix": prefix, "blocks": blocks_for(n_rows_ranks)}])


def strip_none(r):
    return {k: v for k, v in r.items() if not (k == "order_by" and v is None)}


refr = [["a", 9.0, 1], ["b", 8.0, 2], ["c", 8.0, 2], ["d", 7.0, 4]]
Rr = strip_none(rank_rules([1, 2, 2, 4]))
case("rank/competition", "5.9", [["a", 1], ["b", 2], ["c", 2], ["d", 4]], [refr], Rr, "correct")
case("rank/dense", "5.9", [["a", 1], ["b", 2], ["c", 2], ["d", 3]], [refr], Rr, "correct")
case("rank/position", "5.9", [["a", 1], ["b", 3], ["c", 2], ["d", 4]], [refr], Rr, "correct")
case("rank/mixed-styles", "5.9 (negative)", [["a", 1], ["b", 2], ["c", 3], ["d", 3]], [refr], Rr, "wrong", "rank",
     note="b,c positional but d dense")
case("rank/wrong-value", "5.9 (negative)", [["a", 1], ["b", 2], ["c", 2], ["d", 5]], [refr], Rr, "wrong", "rank")
case("rank/string-rank", "5.9", [["a", "1"], ["b", "2"], ["c", "2"], ["d", "4"]], [refr], Rr, "wrong", None,
     note="ranks are integers (SPEC-GAP: numeric strings not accepted)")

# ---------------------------------------------------------------------------
# 13. Multiple references (5.6, 11.3)
# ---------------------------------------------------------------------------
case("multi/second-ref", "5.6", [[2.0]], [[[1.0]], [[2.0]]], [Ramt, Ramt], "correct")
case("multi/none", "5.6", [[3.0]], [[[1.0]], [[2.0]]], [Ramt, Ramt], "wrong", "values")
case("multi/per-ref-rules", "2 (per reference)", [["x", 2.0]], [[[1.0]], [["x", 2.0]]],
     [Ramt, rules(["other", "amount"], ["String", "Float64"], [0, 1])], "correct")

# ---------------------------------------------------------------------------
# 14. Selection (5.7), Q117-like nested and Q85-like two roots
# ---------------------------------------------------------------------------
sel_nested = {"version": 1, "output_order": [], "stages": [
    {"parent": None, "where": [], "group_columns": [], "object_columns": [0],
     "order_by": [{"column": 1, "descending": True}], "n": 2},
    {"parent": 0, "where": [], "group_columns": [0], "object_columns": [2],
     "order_by": [{"column": 3, "descending": True}], "n": 1}]}
Rsel = rules(["other", "percentage", "other", "amount"], ["String", "Float64", "String", "Float64"], [0, 1, 2, 3],
             selection=sel_nested)
refsel = [["S1", 30.0, "TV", 50.0], ["S2", 20.0, "Audio", 9.0], ["S3", 20.0, "TV", 8.0], ["S3", 20.0, "Cams", 8.0]]
case("sel/ok", "5.7", [["S1", 30.0, "TV", 50.0], ["S2", 20.0, "Audio", 9.0]], [refsel], Rsel, "correct")
case("sel/boundary-parent-any-child", "5.7", [["S1", 30.0, "TV", 50.0], ["S3", 20.0, "Cams", 8.0]], [refsel], Rsel, "correct")
case("sel/missing-prefix-parent", "5.7 (negative)", [["S2", 20.0, "Audio", 9.0], ["S3", 20.0, "TV", 8.0]], [refsel], Rsel,
     "wrong", "selection")
case("sel/n-plus-k-children", "5.7 (negative)", [["S1", 30.0, "TV", 50.0], ["S3", 20.0, "TV", 8.0], ["S3", 20.0, "Cams", 8.0]],
     [refsel], Rsel, "wrong", "selection")
case("sel/too-many-parents", "5.7 (negative)",
     [["S1", 30.0, "TV", 50.0], ["S2", 20.0, "Audio", 9.0], ["S3", 20.0, "TV", 8.0]], [refsel], Rsel, "wrong", "selection")
Rsel_bad = rules(["other", "percentage", "other", "amount"], ["String", "Float64", "String", "Float64"], [1, 2, 3],
                 selection=sel_nested)
case("sel/identity-not-required-rejected", "5.7 (rules error)", [["S1", 30.0, "TV", 50.0]], [refsel], Rsel_bad,
     "error", note="group/object identity must be required: the rules are refused")
sel_two = {"version": 1, "output_order": [], "stages": [
    {"parent": None, "where": [{"column": 0, "equals": "high"}], "group_columns": [0], "object_columns": [1],
     "order_by": [{"column": 2, "descending": True}], "n": 1},
    {"parent": None, "where": [{"column": 0, "equals": "low"}], "group_columns": [0], "object_columns": [1],
     "order_by": [{"column": 2, "descending": False}], "n": 1}]}
Rsel2 = rules(["other", "other", "percentage"], ["String", "String", "Float64"], [0, 1, 2], selection=sel_two)
refsel2 = [["high", "A", 99.0], ["low", "Z", 10.0], ["low", "Y", 10.0]]
case("sel/two-roots-ok", "5.7", [["high", "A", 99.0], ["low", "Y", 10.0]], [refsel2], Rsel2, "correct")
case("sel/two-roots-missing-group", "5.7 (negative)", [["high", "A", 99.0]], [refsel2], Rsel2, "wrong", "selection")
case("sel/two-roots-both-boundary", "5.7 (negative)", [["high", "A", 99.0], ["low", "Y", 10.0], ["low", "Z", 10.0]],
     [refsel2], Rsel2, "wrong", "selection")
# 13.2: anything the selection finds is 'selection'; 'values' only when every chosen object is right
case("sel/wrong-child-object", "13.2 (negative)", [["S1", 30.0, "Cams", 50.0], ["S2", 20.0, "Audio", 9.0]], [refsel], Rsel,
     "wrong", "selection", note="a group's object is one the reference never chose for that group")
case("sel/objects-right-value-wrong", "13.2 (negative)", [["S1", 30.0, "TV", 55.0], ["S2", 20.0, "Audio", 9.0]], [refsel],
     Rsel, "wrong", "values")
case("sel/n-plus-k-values-also-wrong", "13.2 (negative)",
     [["S1", 31.0, "TV", 50.0], ["S3", 20.0, "TV", 8.0], ["S3", 20.0, "Cams", 8.0]], [refsel], Rsel, "wrong", "selection")

# 13.1: Q119-like. Per-group top 1 (selection) and a global, non-prefix object ranking; the same
# object is chosen in several groups and carries the same rank every time.
sel_q119 = {"version": 1, "output_order": [], "stages": [
    {"parent": None, "where": [], "group_columns": [0], "object_columns": [1],
     "order_by": [{"column": 2, "descending": True}], "n": 1}]}
rk_q119 = [{"column": 3, "group_columns": [], "object_columns": [1], "prefix": False,
            "blocks": [{"group": [], "rank": 1, "dense": 1, "size": 1}, {"group": [], "rank": 2, "dense": 2, "size": 1},
                       {"group": [], "rank": 3, "dense": 3, "size": 2}]}]
Rq119 = rules(["other", "other", "amount", "other"], ["String", "String", "Float64", "UInt64"], [0, 1, 3],
              selection=sel_q119, rank_columns=[3], rankings=rk_q119)
Rq119_nosel = rules(["other", "other", "amount", "other"], ["String", "String", "Float64", "UInt64"], [0, 1, 3],
                    rank_columns=[3], rankings=rk_q119)
refq119 = [["g1", "A", 50.0, 1], ["g2", "A", 40.0, 1], ["g3", "B", 30.0, 2], ["g4", "C", 20.0, 3], ["g4", "D", 20.0, 3]]
case("rank/object-in-many-groups-ref-itself", "13.1", refq119, [refq119], Rq119_nosel, "correct",
     note="the reference scored against itself: object A twice with the same rank is not a repeat")
case("rank/object-in-many-groups-competition", "13.1", [["g1", "A", 1], ["g2", "A", 1], ["g3", "B", 2], ["g4", "C", 3]],
     [refq119], Rq119, "correct")
case("rank/object-in-many-groups-position", "13.1", [["g1", "A", 1], ["g2", "A", 1], ["g3", "B", 2], ["g4", "D", 4]],
     [refq119], Rq119, "correct",
     note="only the position style fits (D numbered 4 in the C/D block); A in two rows is one object")
case("rank/object-in-many-groups-legal-selection", "13.1 addendum (PR #120)",
     [["g1", "A", 1], ["g2", "A", 1], ["g3", "B", 2], ["g4", "D", 3]], [refq119], Rq119, "correct",
     note="a legal selection from the reference (the other boundary object of g4) scores correct")
case("rank/object-in-many-groups-wrong-rank", "13.1 (negative)",
     [["g1", "A", 1], ["g2", "A", 1], ["g3", "B", 3], ["g4", "C", 3]], [refq119], Rq119, "wrong", "rank")
case("rank/object-in-many-groups-n-plus-k", "13.1, 13.2 (negative)",
     [["g1", "A", 1], ["g2", "A", 1], ["g3", "B", 2], ["g4", "C", 3], ["g4", "D", 3]], [refq119], Rq119, "wrong", "selection",
     note="the whole boundary domain submitted as is: N+k (PR #120 addendum)")

# 13.3: Q92-like. Ordered with a rank column and a NULL label in the reference; reasons follow 12.6
R92 = rules(["other", "percentage", "other"], ["Nullable(String)", "Float64", "UInt64"], [0, 2], ordered=True,
            order_by=[{"column": 1, "descending": True}], rank_columns=[2],
            rankings=[{"column": 2, "group_columns": [], "object_columns": [0], "prefix": True,
                       "blocks": blocks_for([1, 2, 3, 4])}])
ref92 = [["a", 52.0, 1], ["b", 51.0, 2], ["c", 50.0, 3], [None, 45.0, 4]]
case("order/rank-col-positional-rows-swapped", "13.3 (negative)",
     [[1, "b"], [2, "a"], [3, "c"], [4, "unknown"]], [ref92], R92, "wrong", "order",
     note="ranks numbered by the candidate's own row positions; the row order is wrong")
case("order/no-rank-col-rows-swapped", "13.3 (negative)",
     [["b", 0.51], ["a", 0.52], ["c", 0.50], ["unknown", 0.45]], [ref92], R92, "wrong", "order",
     note="no rank column: a non-integer column falls on the rank, but the order fails first")
case("order/no-rank-col-rows-in-order", "13.3 (negative)",
     [["a", 0.52], ["b", 0.51], ["c", 0.50], ["unknown", 0.45]], [ref92], R92, "wrong", "rank")
case("order/rank-col-rows-in-order", "13.3", [[1, "a"], [2, "b"], [3, "c"], [4, "unknown"]], [ref92], R92, "correct")

# ---------------------------------------------------------------------------
# 15. Not relaxed (5.8): wide vs long
# ---------------------------------------------------------------------------
Rlong = rules(["other", "amount"], ["String", "Float64"], [0, 1])
case("strict/wide-vs-long", "5.8", [[100.0, 80.0]], [[["Actual", 100.0], ["Budget", 80.0]]], Rlong, "wrong", "row_count")

# ---------------------------------------------------------------------------
# 15b. Array / Tuple cells (corpus $array)
# ---------------------------------------------------------------------------
Rarr = rules(["other", "count"], ["Array(UInt8)", "UInt64"], [0, 1])
case("cell/array-equal", "12 (corpus)", [[{"$array": [1, 2]}, 3]], [[[{"$array": [1, 2]}, 3]]], Rarr, "correct")
case("cell/array-differs", "12 (corpus, negative)", [[{"$array": [2, 1]}, 3]], [[[{"$array": [1, 2]}, 3]]], Rarr, "wrong", "values")

# ---------------------------------------------------------------------------
# 16. Rules validation (spec 2)
# ---------------------------------------------------------------------------
case("rules/missing-required-columns", "2", [[1]], [[[1]]],
     {"ordered": False, "top_n": None, "tie_columns": [], "value_kinds": ["count"], "value_types": ["UInt64"]}, "error")
case("rules/old-switch", "2", [[1]], [[[1]]], dict(R1, use_absolute_tolerance=True), "error")
case("rules/ordered-without-order-by", "2", [[1]], [[[1]]], dict(R1, ordered=True), "error")
case("rules/unknown-field", "12.3", [[1]], [[[1]]], dict(R1, label_values=[["x"]]), "error")
case("rules/top-n-without-ties", "12.3", [[1]], [[[1]]], dict(R1, top_n=1), "error")
case("rules/where-not-required", "12.4", [["high", "A", 99.0]], [[["high", "A", 99.0]]],
     rules(["other", "other", "percentage"], ["String", "String", "Float64"], [1, 2], selection={"version": 1, "output_order": [], "stages": [
         {"parent": None, "where": [{"column": 0, "equals": "high"}], "group_columns": [], "object_columns": [1],
          "order_by": [{"column": 2, "descending": True}], "n": 1}]}), "error")
case("rules/top-n-not-prefix-boundary", "12.5", [["a", 9.0]], [[["a", 9.0], ["b", 5.0], ["c", 7.0]]],
     rules(["other", "amount"], ["String", "Float64"], [0, 1], top_n=1, ties=[1]), "error",
     note="rows after the N-th must all share its tie key")
case("edge/ragged-candidate", "12.14", [["a", 1.0], ["b"]], [[["a", 1.0], ["b", 2.0]]],
     rules(["other", "amount"], ["String", "Float64"], [0, 1]), "error")
case("edge/empty-ref-empty-cand", "12.14", [], [[]], rules(["other"], ["String"], [0]), "correct")
case("edge/empty-ref-rows", "12.14", [["a"]], [[]], rules(["other"], ["String"], [0]), "wrong", "row_count")
case("edge/bool-vs-int", "12.14", [[True]], [[[1]]], rules(["other"], ["UInt8"], [0]), "wrong", "values")


# ---------------------------------------------------------------------------
# STRESS (spec 7.2): large tie blocks, wide tables, large wrong answers,
# shuffled columns, many references
# ---------------------------------------------------------------------------
def stress():
    rnd = random.Random(20261019)
    # S1. Q79-like: 42 stores tied at rank 1, top 10, ordered
    names = [f"Store {i:03d}" for i in range(42)]
    ref = [[n, 1000.0 + i, 1000.0 + i, 100.0, 1] for i, n in enumerate(names)]
    R = rules(["other", "amount", "amount", "percentage", "other"], ["String", "Float64", "Float64", "Float64", "UInt64"],
              [0, 4], ordered=True, top_n=10, ties=[3], order_by=[{"column": 3, "descending": True}],
              rank_columns=[4], rankings=[{"column": 4, "group_columns": [], "object_columns": [0], "prefix": True,
                                            "blocks": [{"group": [], "rank": 1, "dense": 1, "size": 42}]}])
    pick = rnd.sample(names, 10)
    case("stress/tie42-competition", "7.2, 5.3, 5.9", [[n, 1] for n in pick], [ref], R, "correct")
    case("stress/tie42-position", "7.2, 5.9", [[n, i + 1] for i, n in enumerate(pick)], [ref], R, "correct")
    case("stress/tie42-wrong-name", "7.2", [[n, 1] for n in pick[:9]] + [["Store 999", 1]], [ref], R, "wrong", "values")
    case("stress/tie42-wrong-rank", "7.2", [[n, 1] for n in pick[:9]] + [[pick[9], 2]], [ref], R, "wrong", "rank")
    case("stress/tie42-position-gap", "7.2", [[n, i + 2] for i, n in enumerate(pick)], [ref], R, "wrong", "rank",
         note="positions 2..11: block starts at 1")
    case("stress/tie42-full-group", "7.2, 5.3", [[n, 1] for n in names], [ref], R, "wrong", "top_n_full_group")
    case("stress/tie42-empty", "5.3", [], [ref], R, "wrong", "row_count",
         note="every reference row is in the boundary group, yet N rows are still required")
    case("stress/tie42-wrong-all-columns", "7.2", [[n, 1000.0 + i, 1000.0 + i, 99.0, 1] for i, n in enumerate(pick)],
         [ref], R, "correct", note="extra columns are not compared")
    # S2. 60-row tie block, unordered, ranks positional permutation
    ref60 = [[f"P{i}", 5.0, 1] for i in range(60)]
    R60 = rules(["other", "amount", "other"], ["String", "Float64", "UInt64"], [0, 2], rank_columns=[2],
                rankings=[{"column": 2, "group_columns": [], "object_columns": [0], "prefix": True,
                           "blocks": [{"group": [], "rank": 1, "dense": 1, "size": 60}]}])
    perm = list(range(1, 61))
    rnd.shuffle(perm)
    case("stress/tie60-position-permuted", "7.2, 5.9", [[f"P{i}", perm[i]] for i in range(60)], [ref60], R60, "correct")
    perm2 = list(perm)
    perm2[0] = perm2[1]
    case("stress/tie60-position-duplicate", "7.2, 5.9", [[f"P{i}", perm2[i]] for i in range(60)], [ref60], R60, "wrong", "rank")
    # S3. wide table, 24 columns, shuffled
    W = 24
    kinds = (["other"] + ["amount"] * 11 + ["count"] * 6 + ["percentage"] * 6)[:W]
    types = (["String"] + ["Float64"] * 11 + ["UInt64"] * 6 + ["Float64"] * 6)[:W]
    rows = []
    for i in range(300):
        rows.append([f"k{i}"] + [round(rnd.uniform(1, 1e6), 2) for _ in range(11)] + [rnd.randint(0, 10**6) for _ in range(6)]
                    + [round(rnd.uniform(0, 100), 4) for _ in range(6)])
    Rw = rules(kinds, types, list(range(W)))
    order = list(range(W))
    rnd.shuffle(order)
    shuffled = [[r[j] for j in order] for r in rows]
    rnd.shuffle(shuffled)
    case("stress/wide24-shuffled-correct", "7.2, 4.1", shuffled, [rows], Rw, "correct")
    bad = [list(r) for r in shuffled]
    bad[137][order.index(5)] = bad[137][order.index(5)] * 1.02
    case("stress/wide24-one-cell-wrong", "7.2", bad, [rows], Rw, "wrong", "values")
    # S4. wide table with 8 identical count columns: mapping explosion
    Wz = 9
    rz = [[f"k{i}"] + [i % 5] * 8 for i in range(50)]
    Rz8 = rules(["other"] + ["count"] * 8, ["String"] + ["UInt64"] * 8, list(range(Wz)))
    case("stress/identical-columns-correct", "6.5, 11.4", [list(r) for r in rz], [rz], Rz8, "correct",
         note="the first mapping tried already matches")
    rzbad = [list(r) for r in rz]
    rzbad[3][1], rzbad[4][1] = rzbad[4][1], rzbad[3][1]  # column multisets unchanged, rows broken
    case("stress/identical-columns-wrong-cap", "6.5, 11.4", rzbad, [rz], Rz8, "unscored", "mapping_cap",
         note="8! mappings pass the column filter; none can match; cap of 1,000 reached with more left")
    # S5. large wrong answers (thousands to hundreds of thousands of rows)
    for n in (5_000, 50_000, 200_000):
        refL = [[i, f"name{i}", float(i) * 1.5, i % 97 + 1] for i in range(n)]
        RL = rules(["other", "other", "amount", "count"], ["Int32", "String", "Float64", "UInt64"], [0, 1, 2, 3],
                   identifier_columns=[0])
        cand = [list(r) for r in refL]
        rnd.shuffle(cand)
        case(f"stress/rows{n}-correct-shuffled", "7.2, 6.2", cand, [refL], RL, "correct")
        wrong = [list(r) for r in cand]
        wrong[n // 2][2] = wrong[n // 2][2] * 1.02  # outside the 0.5% tolerance
        case(f"stress/rows{n}-one-value-wrong", "7.2, 6.3", wrong, [refL], RL, "wrong", "values")
        allwrong = [[r[0], r[1], r[2] * 1.1 + 1, r[3]] for r in cand]
        case(f"stress/rows{n}-all-values-wrong", "7.2", allwrong, [refL], RL, "wrong", "values")
        case(f"stress/rows{n}-one-row-short", "7.2, 6.6", cand[:-1], [refL], RL, "wrong", "row_count")
    # S6. tolerance graph that is not transitive (spec 6.3): chains of near-equal values
    refc = [[100.0 * (1.004 ** i)] for i in range(2000)]
    candc = [[v[0] * 1.0049] for v in refc]
    case("stress/tolerance-chain", "6.3", candc, [refc], rules(["other"], ["Float64"], [0]), "correct",
         note="each candidate is within 0.5% of its own reference and of the next one")
    # S7. many references, match only the last
    many = [[[float(k)]] for k in range(30)]
    case("stress/30-refs-last", "5.6", [[29.0]], many, [Ramt] * 30, "correct")
    case("stress/30-refs-none", "5.6", [[99.0]], many, [Ramt] * 30, "wrong", "values")
    # S8. big ordered table with large tie blocks
    refO = []
    for b in range(200):
        for k in range(25):
            refO.append([f"o{b}-{k}", float(1000 - b)])
    RO = rules(["other", "amount"], ["String", "Float64"], [0, 1], ordered=True, order_by=[{"column": 1, "descending": True}])
    candO = []
    for b in range(200):
        blk = refO[b * 25:(b + 1) * 25]
        blk = list(blk)
        rnd.shuffle(blk)
        candO += blk
    case("stress/ordered-5000-blocks-shuffled", "7.2, 5.2", candO, [refO], RO, "correct")
    candO2 = list(candO)
    candO2[24], candO2[25] = candO2[25], candO2[24]
    case("stress/ordered-5000-cross-block", "7.2, 5.2", candO2, [refO], RO, "wrong", "order")
    # S9. grouped ranking with ties per group
    refG, groups, ranks = [], [], []
    for g in range(100):
        vals = [10.0, 9.0, 9.0, 9.0, 5.0]
        comp = [1, 2, 2, 2, 5]
        for k, (v, r) in enumerate(zip(vals, comp)):
            refG.append([f"g{g}", f"x{k}", v, r])
            groups.append([f"g{g}"])
            ranks.append(r)
    RG = rules(["other", "other", "amount", "other"], ["String", "String", "Float64", "UInt64"], [0, 1, 2, 3],
               rank_columns=[3], rankings=[{"column": 3, "group_columns": [0], "object_columns": [1], "prefix": True,
                                             "blocks": blocks_for(ranks, groups)}])
    dense = {1: 1, 2: 2, 5: 3}
    case("stress/group-ranks-dense", "5.9 (grouped)", [[a, b, c, dense[d]] for a, b, c, d in refG], [refG], RG, "correct")
    pos = []
    for g in range(100):
        pos += [[f"g{g}", "x0", 10.0, 1], [f"g{g}", "x1", 9.0, 4], [f"g{g}", "x2", 9.0, 2], [f"g{g}", "x3", 9.0, 3],
                [f"g{g}", "x4", 5.0, 5]]
    case("stress/group-ranks-position", "5.9 (grouped)", pos, [refG], RG, "correct")
    mixed = [list(r) for r in pos]
    mixed[0][3] = 1
    mixed[6][3] = 2  # group g1: x1 gets 2 while x2 also 2 -> duplicate position, and not competition overall
    case("stress/group-ranks-mixed", "5.9 (negative)", mixed, [refG], RG, "wrong", "rank")


stress()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for c in CASES:
            line = dict(c)
            line["candidate"] = c["candidate"] if isinstance(c["candidate"], (str, dict)) else encode_value(c["candidate"])
            line["refs"] = encode_value(c["refs"])
            fh.write(json.dumps(line, ensure_ascii=False, allow_nan=False) + "\n")
    print(len(CASES), "cases ->", out)


if __name__ == "__main__":
    main()
