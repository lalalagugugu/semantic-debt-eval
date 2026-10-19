"""T05b independent checker for scorer spec v2 (decisions/2026-10-18-scorer-spec-v2.md).

Written from the spec only (and the selection semantics it cites,
decisions/2026-10-16-reference-rules-and-selection.md). It does not import or copy
harness/scorer.py or the new scorer. Correctness over speed: every matching is a
flow problem (flow.py); nothing enumerates row combinations or rank positions.

Interface (spec section 1):
    score(candidate, refs, rules) -> Result(outcome, reason)
      candidate: list of rows | CANNOT_ANSWER | ExecError(message)
      refs:      list of reference row sets
      rules:     list of per-reference rules dicts (same length as refs)
    outcome: correct | wrong | exec_error | refused | unscored
    reason:  wrong -> row_count | missing_columns | values | order |
             top_n_full_group | selection | rank;  unscored -> mapping_cap

Where the spec leaves a choice open, the choice made here is marked "SPEC-GAP" and
listed in the report; no rule beyond the spec is added.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass

from . import cells as C
from .flow import Dinic, feasible

CANNOT_ANSWER = "CANNOT_ANSWER"
MAPPING_CAP = 1000
KINDS = {"percentage", "ratio", "amount", "count", "other"}
REQUIRED_FIELDS = ("required_columns", "value_kinds", "value_types", "ordered", "top_n", "tie_columns")  # SPEC-GAP G1
OPTIONAL_FIELDS = ("order_by", "selection", "identifier_columns", "rank_columns", "rankings", "unordered_pairs")
FORBIDDEN_FIELDS = ("use_absolute_tolerance", "exact_counts")
REASON_PROGRESS = ["values", "order", "selection", "rank"]  # later = got further
SEL_GATE = "selection-gate"  # a mapping whose chosen objects are wrong (13.2)


@dataclass(frozen=True)
class ExecError:
    message: str


@dataclass(frozen=True)
class Result:
    outcome: str
    reason: str | None = None
    matched_ref: int | None = None


class RulesError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Rules (spec section 2)
# ---------------------------------------------------------------------------
@dataclass
class Rules:
    required: list
    kinds: list
    types: list
    ordered: bool
    order_by: list
    top_n: int | None
    tie_columns: list
    selection: dict | None
    identifier: set
    rank_columns: set
    rankings: list
    pairs: list


def _cols(xs, width, what, nonempty=False):
    if not isinstance(xs, list) or (nonempty and not xs):
        raise RulesError(f"{what} must be a {'non-empty ' if nonempty else ''}list")
    for x in xs:
        if not isinstance(x, int) or isinstance(x, bool) or not (0 <= x < width):
            raise RulesError(f"{what}: column {x!r} outside the reference width {width}")
    if len(set(xs)) != len(xs):
        raise RulesError(f"{what} repeats a column")
    return list(xs)


def parse_rules(rules, ref_rows):
    if not isinstance(rules, dict):
        raise RulesError("rules must be a dict per reference")
    for f in FORBIDDEN_FIELDS:
        if f in rules:
            raise RulesError(f"{f} is no longer accepted (spec 2)")
    unknown = set(rules) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS)
    if unknown:
        raise RulesError(f"unknown rules fields {sorted(unknown)}")  # SPEC-GAP G2
    for f in REQUIRED_FIELDS:
        if f not in rules:
            raise RulesError(f"missing required rules field {f}")
    kinds, types = rules["value_kinds"], rules["value_types"]
    if not isinstance(kinds, list) or not isinstance(types, list) or len(kinds) != len(types):
        raise RulesError("value_kinds and value_types must be lists of the same length")
    width = len(kinds)
    for row in ref_rows:
        if len(row) != width:
            raise RulesError("reference width differs from value_kinds")
    if any(k not in KINDS for k in kinds):
        raise RulesError("unknown value kind")
    required = _cols(rules["required_columns"], width, "required_columns", nonempty=True)
    ordered = rules["ordered"]
    if not isinstance(ordered, bool):
        raise RulesError("ordered must be a boolean")
    order_by = rules.get("order_by") or []
    if ordered and not order_by:
        raise RulesError("ordered=true needs order_by")
    for k in order_by:
        if not isinstance(k, dict) or set(k) != {"column", "descending"}:
            raise RulesError("order_by items are {column, descending}")
        _cols([k["column"]], width, "order_by")
    top_n = rules["top_n"]
    if top_n is not None and (not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1):
        raise RulesError("top_n must be null or a positive integer")
    ties = _cols(rules["tie_columns"], width, "tie_columns")
    if top_n is not None and not ties:
        raise RulesError("top_n needs tie_columns")  # SPEC-GAP G3
    selection = rules.get("selection")
    if selection is not None:
        if top_n is not None or ties:
            raise RulesError("selection excludes flat top_n and tie_columns")
        _check_selection(selection, width, required, ordered)
    ident = set(_cols(rules.get("identifier_columns") or [], width, "identifier_columns"))
    ranks = set(_cols(rules.get("rank_columns") or [], width, "rank_columns"))
    if ident & ranks:
        raise RulesError("identifier_columns and rank_columns overlap")
    rankings = rules.get("rankings") or []
    if {r["column"] for r in rankings} != ranks:
        raise RulesError("rankings must describe exactly the rank_columns")
    for r in rankings:
        _cols([r["column"]], width, "rankings.column")
        _cols(r["group_columns"], width, "rankings.group_columns")
        _cols(r["object_columns"], width, "rankings.object_columns", nonempty=True)
    pairs = []
    for p in rules.get("unordered_pairs") or []:
        left = _cols(p["left"], width, "unordered_pairs.left", nonempty=True)
        right = _cols(p["right"], width, "unordered_pairs.right", nonempty=True)
        if len(left) != len(right) or set(left) & set(right):
            raise RulesError("unordered_pairs sides must be equal width and disjoint")
        pairs.append((left, right))
    used = [c for l, r in pairs for c in l + r]
    if len(used) != len(set(used)):
        raise RulesError("unordered_pairs overlap each other")
    return Rules(required, kinds, types, ordered, order_by, top_n, ties, selection, ident, ranks, rankings, pairs)


def _check_selection(sel, width, required, ordered):
    if sel.get("version") != 1:
        raise RulesError("selection.version must be 1")
    stages = sel.get("stages")
    if not isinstance(stages, list) or not stages:
        raise RulesError("selection.stages must be non-empty")
    for i, st in enumerate(stages):
        p = st.get("parent")
        if p is not None and not (isinstance(p, int) and 0 <= p < i):
            raise RulesError("selection parent must be an earlier stage")
        g = _cols(st["group_columns"], width, "selection.group_columns")
        o = _cols(st["object_columns"], width, "selection.object_columns", nonempty=True)
        if set(g) & set(o):
            raise RulesError("selection group and object columns overlap")
        if p is not None:
            par = stages[p]
            if not set(par["group_columns"]) | set(par["object_columns"]) <= set(g):
                raise RulesError("child group_columns must contain the parent's identity")
        for w in st.get("where") or []:
            _cols([w["column"]], width, "selection.where")
        if not st.get("order_by"):
            raise RulesError("selection stage needs order_by")
        if not isinstance(st.get("n"), int) or st["n"] < 1:
            raise RulesError("selection n must be a positive integer")
        # Spec 5.7: group and object identity must be required columns.
        ident = set(g) | set(o) | {w["column"] for w in st.get("where") or []}  # SPEC-GAP G4 (where)
        if not ident <= set(required):
            raise RulesError("selection identity columns must all be required (spec 5.7)")
    out = sel.get("output_order") or []
    if ordered and not out:
        raise RulesError("ordered selection needs output_order")
    if not ordered and out:
        raise RulesError("unordered selection must not declare output_order")


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------
def score(candidate, refs, rules):
    if not isinstance(refs, list) or not refs:
        raise RulesError("at least one reference")
    if not isinstance(rules, list) or len(rules) != len(refs):
        raise RulesError("one rules dict per reference")
    parsed = [parse_rules(r, ref) for r, ref in zip(rules, refs)]
    if isinstance(candidate, ExecError):
        return Result("exec_error")
    if isinstance(candidate, str):
        if candidate == CANNOT_ANSWER:
            return Result("refused")
        raise TypeError("a string candidate must be CANNOT_ANSWER")
    if not isinstance(candidate, list):
        raise TypeError("candidate must be rows, CANNOT_ANSWER or ExecError")
    if candidate and len({len(r) for r in candidate}) != 1:
        raise TypeError("candidate rows differ in width")  # SPEC-GAP G5
    first_wrong = None
    unscored = None
    for i, (ref, R) in enumerate(zip(refs, parsed)):
        res = RefCheck(candidate, ref, R).run()
        if res == "correct":
            return Result("correct", None, i)
        if res == "mapping_cap":
            unscored = unscored if unscored is not None else i
            continue
        if first_wrong is None:
            first_wrong = res
    if unscored is not None:
        return Result("unscored", "mapping_cap", unscored)  # SPEC-GAP G6
    return Result("wrong", first_wrong)


# ---------------------------------------------------------------------------
# One reference
# ---------------------------------------------------------------------------
JOIN_FAIL = object()


class Unit:
    """One required reference column (or an adjacent pair, 3.7) mapped to candidate column(s)."""

    __slots__ = ("ref_cols", "cand_cols", "mode", "order")

    def __init__(self, ref_cols, cand_cols, mode, order=0):
        self.ref_cols, self.cand_cols, self.mode, self.order = ref_cols, cand_cols, mode, order

    def cand_value(self, row):
        if self.mode == "split":
            a, b = row[self.cand_cols[0]], row[self.cand_cols[1]]
            v = C.joined(a, b) if self.order == 0 else C.joined(b, a)
            return JOIN_FAIL if v is None else v
        return row[self.cand_cols[0]]

    def ref_value(self, row):
        if self.mode == "merge":
            a, b = row[self.ref_cols[0]], row[self.ref_cols[1]]
            v = C.joined(a, b) if self.order == 0 else C.joined(b, a)
            return JOIN_FAIL if v is None else v
        return row[self.ref_cols[0]]

    def key(self):
        return (self.mode, self.ref_cols, self.cand_cols, self.order)


def _ckey(v):
    return ("joinfail",) if v is JOIN_FAIL else C.class_key(v)


class RefCheck:
    def __init__(self, cand, ref, R: Rules):
        self.cand, self.ref, self.R = cand, ref, R
        self.width = len(cand[0]) if cand else 0
        self.cols = [C.make_col(j, R.kinds[j], R.types[j], j in R.identifier, [row[j] for row in ref])
                     for j in range(len(R.kinds))]
        self.string_col = [C.is_string_type(t) for t in R.types]
        self.req = list(R.required)
        self.req_set = set(R.required)
        # selection identity columns compare exactly (selection contract)
        self.sel_ident = set()
        self.sel_where = set()
        if R.selection:
            for st in R.selection["stages"]:
                self.sel_ident |= set(st["group_columns"]) | set(st["object_columns"])
                self.sel_ident |= {w["column"] for w in st.get("where") or []}
                self.sel_where |= {w["column"] for w in st.get("where") or []}
        for j in self.sel_ident:
            if not self.cols[j].identifier:
                self.cols[j] = C.make_col(j, R.kinds[j], R.types[j], True, [row[j] for row in ref])
        # unordered pairs, restricted to positions where both sides are required
        self.pairs = []
        for left, right in R.pairs:
            z = [(a, b) for a, b in zip(left, right) if a in self.req_set and b in self.req_set]
            if z:
                self.pairs.append(z)
        self.pair_cols = {c for z in self.pairs for ab in z for c in ab}
        self.rank_req = [j for j in self.req if j in R.rank_columns]
        self.rankings = {r["column"]: r for r in R.rankings}
        self.cand_mand = [True] * len(cand)
        self._prep_rank_blocks()
        self._prep_zero()
        self._prep_top()

    # ---------------- reference-side preparation
    def _prep_rank_blocks(self):
        self.ref_block = {}  # (rank col, ref row) -> block dict
        for j in self.rank_req:
            spec = self.rankings[j]
            blocks = {}
            for b in spec["blocks"]:
                g = tuple(C.ident_key(v) for v in b["group"])
                blocks[(g, b["rank"])] = b
            for i, row in enumerate(self.ref):
                g = tuple(C.ident_key(row[c]) for c in spec["group_columns"])
                r = row[j]
                if not (C.is_num(r) and C.finite(r) and float(r) == int(r)):
                    raise RulesError("reference rank must be an integer")
                b = blocks.get((g, int(r)))
                if b is None:
                    raise RulesError("reference rank has no block in rankings")
                self.ref_block[(j, i)] = b

    def _prep_zero(self):
        R = self.R
        self.zero_cols = [j for j in self.req if R.kinds[j] == "count" and j not in R.identifier]
        self.zero_ok = bool(self.zero_cols) and R.top_n is None and R.selection is None
        # 12.11: other required numbers exclude identifier and rank columns
        self.other_numeric = [j for j in self.req if j not in R.identifier and j not in R.rank_columns
                              and j not in self.zero_cols and self.cols[j].numeric]
        self.ref_zero = [self.zero_ok and self._is_zero([row[j] for j in self.zero_cols], [row[j] for j in self.other_numeric])
                         for row in self.ref]

    @staticmethod
    def _is_zero(counts, others):
        return all(C.is_num(v) and C.finite(v) and v == 0 for v in counts) and \
            all(v is None or (C.is_num(v) and C.finite(v) and v == 0) for v in others)

    def _prep_top(self):
        R = self.R
        self.ref_mand = [True] * len(self.ref)
        self.expected_rows = None
        if R.top_n is not None:
            n = R.top_n
            if len(self.ref) <= n:
                self.expected_rows = len(self.ref)
            else:
                key = lambda row: tuple(C.quantize_tie(row[c], R.kinds[c]) for c in R.tie_columns)
                bkey = key(self.ref[n - 1])
                first = next(i for i, row in enumerate(self.ref) if key(row) == bkey)
                if any(key(row) != bkey for row in self.ref[first:]):
                    raise RulesError("top_n reference is not strict prefix + complete boundary group")  # SPEC-GAP G7
                for i in range(first, len(self.ref)):
                    self.ref_mand[i] = False
                self.expected_rows = n
        elif R.selection is not None:
            self.ref_mand = [False] * len(self.ref)
        else:
            self.ref_mand = [not z for z in self.ref_zero]
        # ordered blocks: consecutive reference rows with equal quantized order key
        self.blocks = []
        if R.ordered:
            ok = lambda row: tuple(C.quantize_tie(row[k["column"]], R.kinds[k["column"]]) for k in R.order_by)
            prev = object()
            for i, row in enumerate(self.ref):
                k = ok(row)
                if k != prev:
                    self.blocks.append([])
                    prev = k
                self.blocks[-1].append(i)

    # ---------------- top level
    def run(self):
        R, cand, ref = self.R, self.cand, self.ref
        if not ref:
            return "correct" if not cand else "row_count"  # SPEC-GAP G8
        if not cand:
            # only optional zero rows may all be absent; Top-N still needs exactly N rows (5.3)
            return "correct" if not any(self.ref_mand) and R.selection is None and R.top_n is None else "row_count"
        if R.top_n is not None and len(cand) != self.expected_rows:
            if len(cand) == len(ref) and len(ref) > R.top_n and self._full_group_matches():
                return "top_n_full_group"
            return "row_count"
        if R.top_n is None and R.selection is None:
            if self.zero_ok:
                if len(cand) < sum(self.ref_mand):
                    return "row_count"
            elif len(cand) != len(ref):
                return "row_count"
        merges = self._merge_pairs()
        if self.width < len(self.req) - self._max_disjoint(merges):
            return "missing_columns"
        best = None
        tried = 0
        for units in self._mappings(merges):
            if tried == MAPPING_CAP:
                return "mapping_cap"   # 11.4: cap reached with mappings left untried
            tried += 1
            res = self._check_mapping(units)
            if res == "correct":
                return "correct"
            if res == SEL_GATE:
                continue
            if best is None or REASON_PROGRESS.index(res) > REASON_PROGRESS.index(best):
                best = res
        if best is None and R.selection is not None:
            # 13.2: 'values' only if some mapping gets every chosen object right. Mappings the
            # value filter dropped were never shown to the selection gate, so look again without it.
            return "values" if self._some_mapping_selects(merges) else "selection"
        if best is None:
            return "values"  # SPEC-GAP G9: missing_columns only for the early column-count reject
        return best  # SPEC-GAP G9

    def _some_mapping_selects(self, merges):
        """13.2 reason: does some mapping of the selection identity columns alone choose every object
        right? _selection_ok reads only those columns, so the other required columns are not mapped
        here and the value filter is off (a filtered-out mapping was never shown to the selection gate)."""
        saved = self._opt_cache
        self._opt_cache, self._no_value_filter = {}, True
        try:
            seen, tried = set(), 0
            for parts in self._partitions(merges):
                parts = tuple(p for p in parts if set(p[0]) & self.sel_ident)
                if parts in seen:
                    continue
                seen.add(parts)
                opts = [self._options(rc, m) for rc, m in parts]
                chosen = [None] * len(parts)

                def bt(i, used):
                    if i == len(parts):
                        yield list(chosen)
                        return
                    for u in opts[i]:
                        if used.isdisjoint(u.cand_cols):
                            chosen[i] = u
                            yield from bt(i + 1, used | set(u.cand_cols))

                for units in bt(0, frozenset()):
                    tried += 1
                    if tried > 100_000:
                        raise RuntimeError("selection reason search too large")  # never seen; fail loudly
                    if self._selection_ok(units):
                        return True
            return False
        finally:
            self._opt_cache, self._no_value_filter = saved, False

    def _full_group_matches(self):
        """N+k rows that equal the whole reference (spec 5.3 reason code)."""
        saved = self.ref_mand, self.expected_rows
        self.ref_mand = [True] * len(self.ref)
        try:
            merges = self._merge_pairs()
            for t, units in enumerate(self._mappings(merges)):
                if t == MAPPING_CAP:
                    return False
                if self._match(units, list(range(len(self.cand))), list(range(len(self.ref))), None):
                    return True
            return False
        finally:
            self.ref_mand, self.expected_rows = saved

    # ---------------- column mapping (spec 4, 3.7, 6.5)
    def _special(self, j):
        """Columns that never take part in name split/merge (12.8): identifiers, ranks, pairs,
        and selection where-columns (compared against literal values)."""
        return j in self.R.identifier or j in self.R.rank_columns or j in self.pair_cols or j in self.sel_where

    def _merge_pairs(self):
        """Adjacent required string reference columns that may be joined (3.7, reference side)."""
        out = []
        for j in self.req:
            if j + 1 in self.req_set and self.string_col[j] and self.string_col[j + 1] \
                    and not self._special(j) and not self._special(j + 1):
                out.append(j)
        return out

    @staticmethod
    def _max_disjoint(starts):
        """Most non-overlapping adjacent pairs (j, j+1); greedy is optimal on a line."""
        best, last = 0, -10
        for j in sorted(starts):
            if j >= last + 2:
                best += 1
                last = j
        return best

    def _cand_string_col(self, k):
        vals = [row[k] for row in self.cand]
        return all(v is None or isinstance(v, str) for v in vals) and any(isinstance(v, str) for v in vals)

    def _options(self, ref_cols, mode):
        """Candidate column choices for one unit that pass the per-unit necessary condition."""
        key = (ref_cols, mode)
        if key in self._opt_cache:
            return self._opt_cache[key]
        W, need = self.width, self._unit_need()
        opts = []
        if mode == "one":
            j = ref_cols[0]
            for k in range(W):
                u = Unit(ref_cols, (k,), "one")
                if self._unit_feasible(u, need):
                    opts.append(u)
            if self.string_col[j] and not self._special(j):
                for k in range(W - 1):
                    if self._cand_str[k] and self._cand_str[k + 1]:
                        for o in (0, 1):
                            u = Unit(ref_cols, (k, k + 1), "split", o)
                            if self._unit_feasible(u, need):
                                opts.append(u)
        else:
            for k in range(W):
                if self._cand_str[k]:
                    for o in (0, 1):
                        u = Unit(ref_cols, (k,), "merge", o)
                        if self._unit_feasible(u, need):
                            opts.append(u)
        self._opt_cache[key] = opts
        return opts

    def _partitions(self, merges):
        """Required columns split into singles and merged adjacent pairs (3.7), singles first."""
        out = []

        def part(i, acc):
            if i == len(self.req):
                out.append(list(acc))
                return
            j = self.req[i]
            acc.append(((j,), "one"))
            part(i + 1, acc)
            acc.pop()
            if j in merges and i + 1 < len(self.req) and self.req[i + 1] == j + 1:
                acc.append(((j, j + 1), "merge"))
                part(i + 2, acc)
                acc.pop()

        part(0, [])
        return out

    def _mappings(self, merges):
        """Column mappings passing the necessary condition, in a fixed order (6.5, 11.4)."""
        if not hasattr(self, "_opt_cache"):
            self._opt_cache = {}
            self._cand_str = [self._cand_string_col(k) for k in range(self.width)]
        for parts in self._partitions(merges):
            opts = [self._options(rc, m) for rc, m in parts]
            if any(not o for o in opts):
                continue
            order = sorted(range(len(parts)), key=lambda i: (len(opts[i]), i))
            chosen = [None] * len(parts)

            def bt(t, used):
                if t == len(order):
                    yield [chosen[i] for i in range(len(parts))]
                    return
                i = order[t]
                for u in opts[i]:
                    if used.isdisjoint(u.cand_cols):
                        chosen[i] = u
                        yield from bt(t + 1, used | set(u.cand_cols))

            yield from bt(0, frozenset())

    def _some_column_unmatched(self, merges):
        """missing_columns: some required column has no candidate column at all."""
        for j in self.req:
            if self._options((j,), "one"):
                continue
            if any(m in merges and self._options((m, m + 1), "merge") for m in (j - 1, j)):
                continue
            return True
        return False

    def _unit_need(self):
        """How many rows each single unit must pair (necessary condition for 6.5)."""
        if self.R.top_n is not None or self.R.selection is not None:
            return len(self.cand)
        return sum(self.ref_mand)

    def _unit_feasible(self, u, need):
        """Necessary condition: this unit alone can pair `need` rows."""
        if getattr(self, "_no_value_filter", False):
            return True
        cv = [u.cand_value(row) for row in self.cand]
        rv = [u.ref_value(row) for row in self.ref]
        j = u.ref_cols[0]
        if u.mode == "merge":
            col = C.Col(index=j, kind="other", vtype="String")
        else:
            col = self.cols[j]
        cc = {}
        for v in cv:
            k = _ckey(v)
            cc.setdefault(k, [v, 0])[1] += 1
        rc = {}
        for i, v in enumerate(rv):
            if j in self.rank_req:
                b = self.ref_block[(j, i)]
                k = ("rank", b["rank"], b["dense"], b["size"], tuple(map(str, b["group"])))
                rc.setdefault(k, [(v, b), 0])[1] += 1
            else:
                k = _ckey(v)
                rc.setdefault(k, [v, 0])[1] += 1
        partner = {}
        for z in self.pairs:
            for a, b in z:
                partner[a], partner[b] = b, a
        L = list(cc.values())
        if j in partner:
            # an unordered-pair column may meet either side of its pair, row by row
            pj = partner[j]
            rc = {}
            for row in self.ref:
                k = (_ckey(row[j]), _ckey(row[pj]))
                rc.setdefault(k, [(row[j], row[pj]), 0])[1] += 1
            Rr = list(rc.values())
            edges = [(a, b) for a, (c, _) in enumerate(L) for b, ((r1, r2), _) in enumerate(Rr)
                     if c is not JOIN_FAIL and (C.equal(c, r1, self.cols[j]) or C.equal(c, r2, self.cols[pj]))]
            return _max_match(L, Rr, edges) >= need
        Rr = list(rc.values())
        if j in self.rank_req:
            # rank values, integrality included (5.9), are judged in the rank step (reason 'rank')
            return True
        elif u.mode == "merge":
            idx = {}
            for b, (r, _) in enumerate(Rr):
                if isinstance(r, str):
                    idx.setdefault(r.strip(), []).append(b)
            edges = [(a, b) for a, (c, _) in enumerate(L) if isinstance(c, str) for b in idx.get(c.strip(), [])]
        else:
            edges = _col_edges([c for c, _ in L], [r for r, _ in Rr], col, budget=40 * len(L) + 2000)
            if edges is None:
                return True  # filter too costly here: keep the option, the row matching decides
        return _max_match(L, Rr, edges) >= need

    # ---------------- one mapping
    def _check_mapping(self, units):
        R = self.R
        n = len(self.cand)
        cand_idx = list(range(n))
        ref_idx = list(range(len(self.ref)))
        self.cand_mand = [True] * n
        if self.zero_ok:
            ucol = {u.ref_cols[0]: u for u in units if u.mode == "one"}
            for i, row in enumerate(self.cand):
                counts = [ucol[j].cand_value(row) for j in self.zero_cols if j in ucol]
                others = [ucol[j].cand_value(row) for j in self.other_numeric if j in ucol]
                self.cand_mand[i] = not self._is_zero(counts, others)
        # 0. selection gate (13.2): missing or extra groups, N+k, wrong objects -> 'selection';
        #    later stages are reached only when all chosen objects are right
        if R.selection is not None and not self._selection_ok(units):
            return SEL_GATE
        # 1. values: multiset pairing, ranks as wildcard
        if not self._match(units, cand_idx, ref_idx, "any"):
            return "values"
        # 2. order
        if R.ordered and not self._ordered(units, "any"):
            return "order"
        # 4. ranks: one style for the whole answer (5.9)
        if self.rank_req:
            for style in ("competition", "dense", "position"):
                if self._styled(units, style):
                    return "correct"
            return "rank"
        return "correct"

    def _styled(self, units, style):
        n = len(self.cand)
        if style == "position":
            flows = self._match(units, list(range(n)), list(range(len(self.ref))), style, want=True)
            if flows is None:
                return False
            if not self._position_blocks_ok(units, flows):
                return False  # SPEC-GAP G10 (one assignment checked)
            if self.R.ordered:
                return self._ordered(units, style)
            return True
        if not self._match(units, list(range(n)), list(range(len(self.ref))), style):
            return False
        return not self.R.ordered or self._ordered(units, style)

    def _position_blocks_ok(self, units, flows):
        # 13.1: count objects, not rows; blocks are per group, so groups are checked separately.
        # The same object in several rows (e.g. under several selection groups) is one object.
        per_block = {}
        for (ci, ri), f in flows:
            for j in self.rank_req:
                u = next(u for u in units if u.ref_cols == (j,))
                b = self.ref_block[(j, ri)]
                v = int(float(u.cand_value(self.cand[ci])))
                obj = tuple(C.ident_key(self.ref[ri][c]) for c in self.rankings[j]["object_columns"])
                per_block.setdefault((j, id(b)), (b, self.rankings[j]["prefix"], {}))[2].setdefault(obj, set()).add(v)
        for b, prefix, by_obj in per_block.values():
            owner = {}
            for obj, vs in by_obj.items():
                for v in vs:
                    if owner.setdefault(v, obj) != obj:
                        return False  # two different objects share a position number
            if prefix and sorted(owner) != list(range(b["rank"], b["rank"] + len(by_obj))):
                return False
        return True

    # ---------------- matching
    def _row_equal(self, units, crow, ri, style):
        rrow = self.ref[ri]
        unit_of = {}
        for u in units:
            j = u.ref_cols[0]
            if u.mode == "one" and j in self.pair_cols:
                unit_of[j] = u
                continue
            c = u.cand_value(crow)
            if u.mode == "one" and j in self.rank_req:
                if style is not None and not _rank_ok(c, self.ref_block[(j, ri)], style):
                    return False
                continue
            r = u.ref_value(rrow)
            if c is JOIN_FAIL or r is JOIN_FAIL:
                return False
            if u.mode == "merge":
                if not (isinstance(c, str) and c.strip() == r.strip()):
                    return False
            elif not C.equal(c, r, self.cols[j]):
                return False
        for z in self.pairs:
            direct = all(C.equal(unit_of[a].cand_value(crow), rrow[a], self.cols[a]) and
                         C.equal(unit_of[b].cand_value(crow), rrow[b], self.cols[b]) for a, b in z)
            if direct:
                continue
            swapped = all(C.equal(unit_of[a].cand_value(crow), rrow[b], self.cols[b]) and
                          C.equal(unit_of[b].cand_value(crow), rrow[a], self.cols[a]) for a, b in z)
            if not swapped:
                return False
        return True

    def _match(self, units, cand_idx, ref_idx, style, want=False):
        """Flow over row classes. style: None/'any' = rank columns as wildcard (style
        'any' still requires the value to fit some style), or a style name."""
        sty = None if style == "any" else style
        ckeys = {}
        for i in cand_idx:
            row = self.cand[i]
            k = (tuple(_ckey(u.cand_value(row)) for u in units), self.cand_mand[i])
            ckeys.setdefault(k, []).append(i)
        rkeys = {}
        for i in ref_idx:
            row = self.ref[i]
            blk = tuple(id(self.ref_block[(j, i)]) for j in self.rank_req)
            k = (tuple(_ckey(row[j]) for j in self.req), self.ref_mand[i], blk)
            rkeys.setdefault(k, []).append(i)
        L = list(ckeys.values())
        Rr = list(rkeys.values())
        left = [(len(v) if self.cand_mand[v[0]] else 0, len(v)) for v in L]
        right = [(len(v) if self.ref_mand[v[0]] else 0, len(v)) for v in Rr]
        edges = self._edges(units, L, Rr, sty, style == "any")
        if not want:
            return feasible(left, right, edges)
        return _feasible_flows(left, right, edges, L, Rr)

    def _edges(self, units, L, Rr, style, any_style):
        """Class pairs whose representative rows are equal. Exact units bucket the
        reference classes first; the first tolerance unit narrows by sorted windows."""
        exact, tol = [], None
        for u in units:
            j = u.ref_cols[0]
            if u.mode != "one":
                exact.append(u)
            elif j in self.rank_req or j in self.pair_cols:
                continue
            elif self.cols[j].identifier:
                exact.append(u)
            elif self.cols[j].exact_count:
                exact.append(u)
            elif self.string_col[j] and not self.cols[j].empty_label_rule:
                exact.append(u)
            elif self.cols[j].numeric and tol is None:
                tol = u

        def ukey(u, v, side):
            j = u.ref_cols[0]
            if v is JOIN_FAIL:
                return ("joinfail", side)  # never equal across sides
            if u.mode == "one" and self.cols[j].identifier:
                k = C.ident_key(v)
                return k if k[0] != "nonfinite" else ("nonfinite", side, id(v))
            k = _ckey(v)
            if k[0] == "nonfinite":
                return ("nonfinite", side)
            if u.mode != "one":
                return ("s", v.strip()) if isinstance(v, str) else k
            return k

        buckets = {}
        for b, rows in enumerate(Rr):
            rrow = self.ref[rows[0]]
            key = tuple(ukey(u, u.ref_value(rrow), "r") for u in exact)
            buckets.setdefault(key, []).append(b)
        index = {}
        edges = []
        mode_style = None if any_style else style
        for a, rows in enumerate(L):
            crow = self.cand[rows[0]]
            key = tuple(ukey(u, u.cand_value(crow), "c") for u in exact)
            bl = buckets.get(key)
            if not bl:
                continue
            if tol is not None and len(bl) > 32:
                if key not in index:
                    index[key] = _window_index(bl, Rr, self.ref, tol.ref_cols[0])
                cands = index[key].query(tol.cand_value(crow), self.cols[tol.ref_cols[0]].kind)
            else:
                cands = bl
            for b in cands:
                ri = Rr[b][0]
                if any_style:
                    if not self._row_equal(units, crow, ri, None):  # rank columns as wildcard
                        continue
                elif not self._row_equal(units, crow, ri, mode_style):
                    continue
                edges.append((a, b))
        return edges

    def _ordered(self, units, style):
        """Spec 5.2 with optional rows (Top-N boundary, selection, zero groups): split the
        candidate into consecutive segments, one per reference block, each segment a
        valid multiset pairing with its block."""
        n = len(self.cand)
        optional_cand = any(not m for m in self.cand_mand)
        reach = {0}
        for blk in self.blocks:
            mand = sum(self.ref_mand[i] for i in blk)
            new = set()
            for p in sorted(reach):
                lo = 0 if optional_cand else mand
                hi = (n - p) if optional_cand else min(len(blk), n - p)
                if not optional_cand and all(self.ref_mand[i] for i in blk):
                    lo = hi = len(blk)
                    if p + lo > n:
                        continue
                for q in range(p + lo, p + hi + 1):
                    if q in new:
                        continue
                    if self._match(units, list(range(p, q)), blk, style):
                        new.add(q)
            reach = new
            if not reach:
                return False
        return n in reach

    # ---------------- selection (spec 5.7 + 2026-10-16 contract)
    def _selection_ok(self, units):
        sel = self.R.selection
        stages = sel["stages"]
        unit_of = {}
        for u in units:
            for j in u.ref_cols:
                unit_of[j] = u
        children = {i: [] for i in range(len(stages))}
        for i, st in enumerate(stages):
            if st.get("parent") is not None:
                children[st["parent"]].append(i)
        leaves = [i for i in range(len(stages)) if not children[i]]

        def cval(row, j):
            v = unit_of[j].cand_value(row)
            return ("joinfail", id(row)) if v is JOIN_FAIL else C.ident_key(v)

        def rval(row, j):
            v = unit_of[j].ref_value(row)
            return ("joinfail",) if v is JOIN_FAIL else C.ident_key(v)

        def chain(i):
            out = []
            while i is not None:
                out.append(i)
                i = stages[i].get("parent")
            return out[::-1]

        def in_stage(get, row, i):
            for s in chain(i):
                for w in stages[s].get("where") or []:
                    if get(row, w["column"]) != C.ident_key(w["equals"]):
                        return False
            return True

        # reference domains
        dom = {}  # (stage, group) -> {object: key}
        for i, st in enumerate(stages):
            for row in self.ref:
                if not in_stage(rval, row, i):
                    continue
                g = tuple(rval(row, c) for c in st["group_columns"])
                o = tuple(rval(row, c) for c in st["object_columns"])
                k = tuple(C.quantize_tie(row[x["column"]], self.R.kinds[x["column"]]) for x in st["order_by"])
                prev = dom.setdefault((i, g), {}).get(o)
                if prev is not None and prev != k:
                    raise RulesError("selection object has inconsistent order keys in the reference")
                dom[(i, g)][o] = k
        need = {}
        for (i, g), objs in dom.items():
            st = stages[i]
            n = st["n"]
            items = sorted(objs.items(), key=lambda kv: _sort_key(kv[1], st["order_by"]))
            if len(items) <= n:
                need[(i, g)] = (set(objs), len(items), set(objs))
                continue
            bkey = items[n - 1][1]
            prefix = {o for o, k in items if _sort_key(k, st["order_by"]) < _sort_key(bkey, st["order_by"])}
            if any(_sort_key(k, st["order_by"]) > _sort_key(bkey, st["order_by"]) for _, k in items):
                raise RulesError("selection reference holds objects beyond the boundary")
            need[(i, g)] = (prefix, n, set(objs))
        # candidate choices
        chosen = {}
        leaf_seen = {}
        for row in self.cand:
            in_leaf = False
            for i in range(len(stages)):
                if not in_stage(cval, row, i):
                    continue
                st = stages[i]
                g = tuple(cval(row, c) for c in st["group_columns"])
                o = tuple(cval(row, c) for c in st["object_columns"])
                chosen.setdefault((i, g), set()).add(o)
                if i in leaves:
                    in_leaf = True
                    leaf_seen[(i, g, o)] = leaf_seen.get((i, g, o), 0) + 1
            if not in_leaf:
                return False
        if any(c > 1 for c in leaf_seen.values()):
            return False
        # which groups must be covered: every root group; child groups under chosen parents
        required_groups = set()
        for i, st in enumerate(stages):
            p = st.get("parent")
            for (si, g) in dom:
                if si != i:
                    continue
                if p is None:
                    required_groups.add((i, g))
                else:
                    pst = stages[p]
                    pid = pst["group_columns"] + pst["object_columns"]
                    pos = [st["group_columns"].index(c) for c in pid]
                    pg = tuple(g[x] for x in pos[:len(pst["group_columns"])])
                    po = tuple(g[x] for x in pos[len(pst["group_columns"]):])
                    if po in chosen.get((p, pg), set()):
                        required_groups.add((i, g))
        for key in set(chosen) | required_groups:
            if key not in need:
                return False
            if key not in required_groups:
                return False  # rows under a parent the candidate did not choose
            prefix, cnt, objs = need[key]
            got = chosen.get(key, set())
            if len(got) != cnt or not prefix <= got or not got <= objs:
                return False
        return True


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _sort_key(qkey, order_by):
    out = []
    for v, ob in zip(qkey, order_by):
        out.append(_Desc(v) if ob["descending"] else _Asc(v))
    return tuple(out)


class _Asc:
    __slots__ = ("v",)

    def __init__(self, v):
        if v[0] != "num" and v[0] not in ("str", "date"):
            raise RulesError("selection order keys must be non-NULL finite")
        self.v = v

    def __lt__(self, o):
        return self.v[1] < o.v[1]

    def __gt__(self, o):
        return self.v[1] > o.v[1]

    def __eq__(self, o):
        return self.v[1] == o.v[1]


class _Desc(_Asc):
    def __lt__(self, o):
        return self.v[1] > o.v[1]

    def __gt__(self, o):
        return self.v[1] < o.v[1]


def _as_int(v):
    if C.is_num(v) and C.finite(v) and float(v) == int(v):
        return int(v)
    return None  # SPEC-GAP G11: integral numbers only, no strings


def _rank_ok(c, block, style):
    v = _as_int(c)
    if v is None:
        return False
    if style == "competition":
        return v == block["rank"]
    if style == "dense":
        return v == block["dense"]
    return block["rank"] <= v < block["rank"] + block["size"]


def _rank_any(c, block):
    return any(_rank_ok(c, block, s) for s in ("competition", "dense", "position"))


def _max_match(L, R, edges):
    """Maximum b-matching size (multiplicities in L[i][1], R[j][1])."""
    nl, nr = len(L), len(R)
    s, t = nl + nr, nl + nr + 1
    g = Dinic(nl + nr + 2)
    for i, (_, m) in enumerate(L):
        g.add(s, i, m)
    for j, (_, m) in enumerate(R):
        g.add(nl + j, t, m)
    for i, j in edges:
        g.add(i, nl + j, min(L[i][1], R[j][1]))
    return g.maxflow(s, t)


def _feasible_flows(left, right, edges, L, Rr):
    """Like flow.feasible but returns per-row-pair flows [((cand row, ref row), f)] or None."""
    nl, nr = len(left), len(right)
    S, T, SS, TT = nl + nr, nl + nr + 1, nl + nr + 2, nl + nr + 3
    g = Dinic(nl + nr + 4)
    excess = [0] * (nl + nr + 4)
    big = sum(m for _, m in left) + sum(m for _, m in right) + 1
    for i, (lo, hi) in enumerate(left):
        if hi - lo:
            g.add(S, i, hi - lo)
        excess[S] -= lo
        excess[i] += lo
    for j, (lo, hi) in enumerate(right):
        if hi - lo:
            g.add(nl + j, T, hi - lo)
        excess[nl + j] -= lo
        excess[T] += lo
    eid = []
    for i, j in edges:
        eid.append((g.add(i, nl + j, big), i, j))
    g.add(T, S, big)
    need = 0
    for v, x in enumerate(excess):
        if x > 0:
            g.add(SS, v, x)
            need += x
        elif x < 0:
            g.add(v, TT, -x)
    if g.maxflow(SS, TT) != need:
        return None
    out = []
    lpos = [0] * nl
    rpos = [0] * nr
    for e, i, j in eid:
        f = big - g.cap[e]
        for _ in range(f):
            out.append(((L[i][lpos[i]], Rr[j][rpos[j]]), 1))
            lpos[i] += 1
            rpos[j] += 1
    return out


def _col_edges(cvals, rvals, col, budget=None):
    """Pairs (a, b) with equal(cvals[a], rvals[b], col), found without comparing all pairs:
    exact keys by dictionary, numbers by sorted tolerance windows, reference empty labels
    (3.6) against every candidate string or NULL; every hit is confirmed by C.equal."""
    by_key, wild, nums = {}, [], []
    for b, r in enumerate(rvals):
        if r is JOIN_FAIL:
            continue
        if col.empty_label_rule and C.is_empty_label(r):
            wild.append(b)
            continue
        if col.identifier:
            by_key.setdefault(C.ident_key(r), []).append(b)
        elif C.is_num(r) and C.finite(r) and not col.exact_count:
            nums.append((float(r), b))
        else:
            by_key.setdefault(C.class_key(r), []).append(b)
    nums.sort()
    keys = [x for x, _ in nums]
    atol = C.ATOL.get(col.kind, 0.0) * (100.0 if col.kind == "percentage" else 1.0)
    edges = []
    work = 0
    for a, c in enumerate(cvals):
        if c is JOIN_FAIL:
            continue
        hits = set(wild)
        if col.identifier:
            hits.update(by_key.get(C.ident_key(c), []))
        else:
            hits.update(by_key.get(C.class_key(c), []))
            if C.is_num(c) and C.finite(c) and nums:
                cf = float(c)
                for cv in (cf, cf * 100.0, cf / 100.0):
                    w = (C.REL * abs(cv) + atol) / (1 - C.REL) * (1 + 1e-9) + 1e-12
                    lo, hi = bisect_left(keys, cv - w), bisect_right(keys, cv + w)
                    hits.update(b for _, b in nums[lo:hi])
        work += len(hits)
        if budget is not None and work > budget:
            return None
        for b in hits:
            if C.equal(c, rvals[b], col):
                edges.append((a, b))
    return edges


class _window_index:
    """Reference classes of one bucket sorted by the tolerance unit's value."""

    def __init__(self, bl, Rr, ref, j):
        self.nums = []
        self.other = {}
        for b in bl:
            v = ref[Rr[b][0]][j]
            if C.is_num(v) and C.finite(v):
                self.nums.append((float(v), b))
            else:
                self.other.setdefault(C.class_key(v), []).append(b)
        self.nums.sort()
        self.keys = [x for x, _ in self.nums]

    def query(self, c, kind):
        if not (C.is_num(c) and C.finite(c)):
            return list(self.other.get(C.class_key(c), []))
        c = float(c)
        atol = C.ATOL.get(kind, 0.0) * (100.0 if kind == "percentage" else 1.0)
        out = set()
        for cv in (c, c * 100.0, c / 100.0):
            w = (C.REL * abs(cv) + atol) / (1 - C.REL) * (1 + 1e-9) + 1e-12
            lo, hi = bisect_left(self.keys, cv - w), bisect_right(self.keys, cv + w)
            out.update(b for _, b in self.nums[lo:hi])
        return sorted(out)
