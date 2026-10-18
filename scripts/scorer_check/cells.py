"""Cell equality, scorer spec v2 section 3 (decisions/2026-10-18-scorer-spec-v2.md).

Written from the spec text only. Every rule applies symmetrically to candidate and
reference unless the spec says "reference side only" (rule 6).
"""

from __future__ import annotations

import datetime as dt
import math
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

ATOL = {"amount": 0.01, "ratio": 0.0001, "percentage": 0.0001}  # spec 3.3; others 0
REL = 0.005

_WRAP = re.compile(r"^(?:Nullable|LowCardinality)\((.*)\)$")
_INT = re.compile(r"^U?Int(?:8|16|32|64|128|256)$")
_NUMERIC = re.compile(r"^(?:U?Int\d+|Float\d+|Decimal\d*(?:\(.*\))?|Decimal)$")
_DATE_STR = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_MIDNIGHT_STR = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) 00:00:00$")
_DEC_INT_STR = re.compile(r"^(?:0|-?[1-9][0-9]*)$")


def base_type(t: str) -> str:
    t = (t or "").strip()
    while True:
        m = _WRAP.match(t)
        if not m:
            return t
        t = m.group(1).strip()


def is_int_type(t: str) -> bool:
    return bool(_INT.match(base_type(t)))


def is_numeric_type(t: str) -> bool:
    return bool(_NUMERIC.match(base_type(t)))


def is_string_type(t: str) -> bool:
    b = base_type(t)
    return b == "String" or b.startswith("FixedString")


def is_num(v) -> bool:
    return isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)


def finite(v) -> bool:
    if isinstance(v, float):
        return math.isfinite(v)
    if isinstance(v, Decimal):
        return v.is_finite()
    return True


def date_key(v):
    """ISO date when v is a date, a YYYY-MM-DD string, or a naive midnight timestamp
    (object or 'YYYY-MM-DD 00:00:00' string); otherwise None (spec 3.5)."""
    if isinstance(v, dt.datetime):
        if v.tzinfo is not None:
            return None
        if (v.hour, v.minute, v.second, v.microsecond) == (0, 0, 0, 0):
            return v.date().isoformat()
        return None
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, str):
        s = v.strip()
        m = _DATE_STR.match(s) or _MIDNIGHT_STR.match(s)
        if m:
            try:
                return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
            except ValueError:
                return None
    return None


def class_key(v):
    """Hashable key for collapsing identical cells. Equal keys imply equal cells
    under every rule below except NaN, which never equals anything (keys keep NaN
    rows together only for counting; edges are still computed by `equal`)."""
    if v is None:
        return ("null",)
    if isinstance(v, bool):
        return ("bool", v)
    dk = date_key(v)
    if dk is not None:
        return ("date", dk)
    if is_num(v):
        if not finite(v):
            return ("nonfinite", str(v))
        return ("num", v)
    if isinstance(v, dt.datetime):
        return ("datetime", v.isoformat())
    if isinstance(v, str):
        return ("str", v.strip())
    return ("obj", type(v).__name__, repr(v))


def ident_key(v):
    """Exact identity key for identifier columns (spec 3.4): numbers exactly, a
    number equals a plain decimal integer string with the same value; dates by 3.5."""
    if v is None:
        return ("null",)
    if isinstance(v, bool):
        return ("bool", v)
    dk = date_key(v)
    if dk is not None:
        return ("date", dk)
    if is_num(v):
        if not finite(v):
            return ("nonfinite", object())  # never equal
        d = Decimal(v) if not isinstance(v, float) else Decimal(repr(v))
        if d == d.to_integral_value():
            return ("int", int(d))
        return ("num", d)
    if isinstance(v, str):
        s = v.strip()
        if _DEC_INT_STR.match(s):
            return ("int", int(s))
        return ("str", s)
    if isinstance(v, dt.datetime):
        return ("datetime", v.isoformat())
    return ("obj", type(v).__name__, repr(v))


def _f(v) -> float:
    return float(v)


def num_close(c, r, kind: str) -> bool:
    """Spec 3.3, non-exact numbers: |c - r| <= max(0.005|r|, atol); percentages are
    compared as fractions (divide by 100 first); candidate x100 and /100 are also tried;
    a zero reference uses only its declared unit with the absolute floor."""
    if not (finite(c) and finite(r)):
        return False
    c, r = _f(c), _f(r)
    atol = ATOL.get(kind, 0.0)
    scale = 100.0 if kind == "percentage" else 1.0

    def ok(cv):
        a, b = cv / scale, r / scale
        return abs(a - b) <= max(REL * abs(b), atol)

    if ok(c):
        return True
    if r == 0:
        return False
    return ok(c * 100.0) or ok(c / 100.0)


@dataclass
class Col:
    """What the comparison of one reference column needs to know."""
    index: int
    kind: str
    vtype: str
    identifier: bool = False
    exact_count: bool = False
    numeric: bool = False
    empty_label_rule: bool = False      # rule 3.6 applies to this column
    labels: frozenset = field(default_factory=frozenset)  # non-empty reference labels (stripped)


def make_col(j, kind, vtype, identifier, ref_values):
    numeric = is_numeric_type(vtype)
    c = Col(index=j, kind=kind, vtype=vtype, identifier=identifier,
            exact_count=(kind == "count" and is_int_type(vtype)), numeric=numeric)
    # 3.6: non-numeric reference column holding NULL or '' (identifier columns are exact, 3.4).
    if not numeric and not identifier:
        empty = any(v is None or (isinstance(v, str) and v.strip() == "") for v in ref_values)
        if empty:
            c.empty_label_rule = True
            c.labels = frozenset(v.strip() for v in ref_values if isinstance(v, str) and v.strip() != "")
    return c


def is_empty_label(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def equal(c, r, col: Col) -> bool:
    """Candidate cell c against reference cell r in reference column `col`."""
    if col.identifier:
        return ident_key(c) == ident_key(r) and not (ident_key(c)[0] == "nonfinite")
    if col.empty_label_rule and is_empty_label(r):
        if c is None:
            return r is None                      # 3.2: NULL equals NULL only
        if isinstance(c, str):
            return c.strip() not in col.labels     # any string not used by another reference row
        return False
    if c is None or r is None:
        return c is None and r is None
    if isinstance(c, bool) or isinstance(r, bool):
        return isinstance(c, bool) and isinstance(r, bool) and c == r
    dc, dr = date_key(c), date_key(r)
    if dc is not None or dr is not None:
        if dc is not None and dr is not None:
            return dc == dr
        # one side is a date and the other is not date-equivalent
        if isinstance(c, (dt.date, dt.datetime)) and isinstance(r, (dt.date, dt.datetime)):
            return c == r
        return False
    if is_num(c) and is_num(r):
        if col.exact_count:
            return finite(c) and finite(r) and Decimal(repr(c) if isinstance(c, float) else c) == Decimal(repr(r) if isinstance(r, float) else r)
        return num_close(c, r, col.kind)
    if isinstance(c, str) and isinstance(r, str):
        return c.strip() == r.strip()
    if isinstance(c, dt.datetime) and isinstance(r, dt.datetime):
        return c == r
    if type(c) is type(r) and not is_num(c):
        return c == r
    return False


def joined(a, b):
    """3.7: two string cells joined by one space after stripping; None if not two strings."""
    if isinstance(a, str) and isinstance(b, str):
        return a.strip() + " " + b.strip()
    return None


def quantize_tie(v, kind):
    """Order-key quantization named by spec 5.2: Decimal of the decimal string,
    ROUND_HALF_EVEN; amount 2 places, percentage divided by 100 then 6, other numbers 6."""
    if v is None:
        return ("null",)
    if is_num(v):
        if not finite(v):
            return ("nonfinite", str(v))
        d = Decimal(repr(v)) if isinstance(v, float) else Decimal(v)
        with localcontext() as ctx:
            ctx.prec = max(50, len(d.as_tuple().digits) + abs(d.adjusted()) + 10)
            if kind == "percentage":
                d = d / Decimal(100)
            q = Decimal("0.01") if kind == "amount" else Decimal("0.000001")
            return ("num", d.quantize(q, rounding=ROUND_HALF_EVEN))
    return class_key(v)
