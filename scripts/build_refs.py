#!/usr/bin/env python
"""Recompute every private reference: uv run python scripts/build_refs.py.

Use --check to recompute without changing tracked reference files. Only the
independent chdb-eval database is accepted. No model or network is called.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
from collections import defaultdict
from decimal import Decimal
import difflib

import chdb
from chdb import session
import yaml

REPO = Path(__file__).resolve().parent.parent
TOP_N = {7: (10, 1), 25: (1, 1), 27: (10, 3), 73: (10, 3), 79: (10, 3), 87: (20, 3), 88: (20, 1)}


def load_unit_policy():
    main_dir = os.environ.get("SEMDEBT_MAIN_DIR")
    if not main_dir:
        raise SystemExit("SEMDEBT_MAIN_DIR must be set")
    path = Path(main_dir) / "harness/value_units.py"
    spec = importlib.util.spec_from_file_location("reference_value_units", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, hashlib.sha256(path.read_bytes()).hexdigest()


def validate_questions(questions):
    required = set(json.loads((REPO / "questions/schema.json").read_text())["properties"]["questions"]["items"]["required"])
    ids = []
    paths = []
    for question in questions:
        if set(question) != required:
            raise ValueError(f"{question.get('id')}: unexpected/missing question fields")
        ids.append(question["id"])
        if question["source"] not in {"cube", "new"} or question["scoring"] not in {"deterministic", "judge"}:
            raise ValueError(f"{question['id']}: invalid source/scoring")
        if question["type"] not in {"指标分析", "维度查找", "统计", "开放式"}:
            raise ValueError(f"{question['id']}: invalid question type")
        if question["split"] not in {None, "tuning", "heldout"} or not isinstance(question["labels"], dict):
            raise ValueError(f"{question['id']}: invalid labels/split")
        if not isinstance(question["text_en"], str) or not question["text_en"]:
            raise ValueError(f"{question['id']}: missing English text")
        if not question["refs"]:
            raise ValueError(f"{question['id']}: no references")
        for ref in question["refs"]:
            if not {"interpretation", "sql", "result_path"} <= set(ref) or set(ref) - {"interpretation", "sql", "result_path", "postprocess"} or not all(ref.values()):
                raise ValueError(f"{question['id']}: invalid reference")
            if ref.get("postprocess") not in {None, "abc_groups", "power_customers", "store_top3"}:
                raise ValueError(f"{question['id']}: invalid postprocess")
            if not re.fullmatch(r"refs/[A-Za-z0-9/_-]+\.csv", ref["result_path"]):
                raise ValueError("invalid reference path")
            paths.append(ref["result_path"])
    if len(set(ids)) != len(ids) or len(set(paths)) != len(paths):
        raise ValueError("duplicate question ID or result path")
    if [f"Q{i:02d}" for i in range(1, 101)] != ids:
        raise ValueError("expected ordered Q01–Q100")


def csv_bytes(meta, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow([column["name"] for column in meta])
    for row in rows:
        writer.writerow(["\\N" if value is None else value for value in row])
    return stream.getvalue().encode("utf-8")


def exact_percentile(values, fraction=Decimal("0.9")):
    if not values:
        raise ValueError("empty percentile domain")
    ordered = sorted(values)
    position = Decimal(len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def postprocess_reference(method, meta, rows, policy):
    """Apply explicitly declared, user-approved rules to SQL aggregate domains.

    All membership decisions use the shared Decimal quantizer. The SQL supplies
    current data, never embedded answer literals. Pandas must recompute these
    rules independently in T05b rather than importing this implementation.
    """
    if method is None:
        return meta, rows, None
    positions = {column["name"]: i for i, column in enumerate(meta)}
    def value(row, name):
        return row[positions[name]]
    def quantized(row, name):
        column = meta[positions[name]]
        return policy.quantize_tie(value(row, name), policy.infer_value_kind(name, column["type"]))
    if method == "abc_groups":
        groups = defaultdict(list)
        for row in rows:
            groups[quantized(row, "revenue")].append(row)
        total = sum((revenue * len(members) for revenue, members in groups.items()), Decimal(0))
        if total <= 0:
            raise ValueError("ABC requires positive total revenue")
        buckets = {name: [0, Decimal(0)] for name in ("A", "B", "C")}
        cumulative = Decimal(0)
        for revenue, members in sorted(groups.items(), reverse=True):
            name = "A" if cumulative < total * Decimal("0.8") else "B" if cumulative < total * Decimal("0.95") else "C"
            buckets[name][0] += len(members)
            buckets[name][1] += revenue * len(members)
            cumulative += revenue * len(members)
        columns = [{"name": "abc_class", "type": "String"}, {"name": "product_count", "type": "UInt64"}, {"name": "revenue", "type": "Float64"}, {"name": "pct_of_revenue", "type": "Float64"}]
        output = [[name, count, float(revenue), float(revenue * 100 / total)] for name, (count, revenue) in buckets.items() if count]
        return columns, output, {"domain_rows": len(rows), "same_amount_groups": len(groups), "quantized_total_revenue": str(total)}
    if method == "power_customers":
        order_p90 = exact_percentile([quantized(row, "orders") for row in rows])
        amount_p90 = exact_percentile([quantized(row, "avg_order_amount") for row in rows])
        selected = [row for row in rows if quantized(row, "orders") >= order_p90 and quantized(row, "avg_order_amount") >= amount_p90]
        return meta, selected, {"domain_rows": len(rows), "orders_p90": str(order_p90), "avg_order_amount_p90": str(amount_p90), "percentile_method": "exact linear interpolation at (n-1)*0.9"}
    if method == "store_top3":
        groups = defaultdict(list)
        for row in rows:
            groups[value(row, "StoreKey")].append(row)
        selected = []
        for store, members in sorted(groups.items()):
            members.sort(key=lambda row: json.dumps(row, ensure_ascii=False))
            members.sort(key=lambda row: quantized(row, "product_sales"), reverse=True)
            boundary = quantized(members[min(3, len(members)) - 1], "product_sales")
            selected.extend(row for row in members if quantized(row, "product_sales") >= boundary)
        keep = [i for i, column in enumerate(meta) if column["name"] != "StoreKey"]
        return [meta[i] for i in keep], [[row[i] for i in keep] for row in selected], {"domain_rows": len(rows), "groups": len(groups), "top_n_per_store": 3, "complete_boundary": True}
    raise ValueError(f"unsupported postprocess: {method}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data_dir = os.environ.get("SEMDEBT_DATA_DIR")
    if not data_dir:
        raise SystemExit("SEMDEBT_DATA_DIR must be set")
    db = Path(data_dir) / "chdb-eval"
    if not db.is_dir():
        raise SystemExit("chdb-eval does not exist; rebuild it from Parquet first")
    policy, policy_hash = load_unit_policy()
    questions = yaml.safe_load((REPO / "questions/cube_100.yaml").read_text())["questions"]
    validate_questions(questions)
    records = []
    sess = session.Session(str(db))
    try:
        sess.query("SET max_threads=1")
        sess.query("SET max_execution_time=0")
        sess.query("SET output_format_json_quote_denormals=1")
        version = str(sess.query("SELECT version()", "CSV")).strip().strip('"')
        for question in questions:
            qid = int(question["id"][1:])
            for ref in question["refs"]:
                sql = ref["sql"]
                boundary = TOP_N.get(qid)
                if boundary:
                    sql, replacements = re.subn(rf"\bLIMIT\s+{boundary[0]}\s*;?\s*$", "", sql, flags=re.I)
                    if replacements != 1:
                        raise ValueError(f"{question['id']}: cannot extend boundary")
                payload = json.loads(str(sess.query(sql, "JSONCompact")))
                meta, rows = payload["meta"], payload["data"]
                meta, rows, postprocess_details = postprocess_reference(ref.get("postprocess"), meta, rows, policy)
                count_aliases = {m.group(1).lower() for m in re.finditer(r"(?:\bSELECT\s+|,)\s*(?:count|countDistinct|countIf|uniqExact)\s*\([^)]*\)\s+(?:AS\s+)?([A-Za-z_]\w*)", sql, re.I)}
                kinds = ["count" if c["name"].lower() in count_aliases else policy.infer_value_kind(c["name"], c["type"]) for c in meta]
                if boundary:
                    n, column = boundary
                    key = lambda row: policy.quantize_tie(row[column], kinds[column])
                    rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False))
                    rows.sort(key=key, reverse=qid != 87)
                    if len(rows) < n:
                        raise ValueError(f"{question['id']}: insufficient ranked rows")
                    cut = n
                    while cut < len(rows) and key(rows[cut]) == key(rows[n - 1]):
                        cut += 1
                    rows = rows[:cut]
                else:
                    # Store canonical row sets. Ordering requirements are separately
                    # retained in the source SQL; physical group order is not truth.
                    rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False))
                contents = csv_bytes(meta, rows)
                path = REPO / ref["result_path"]
                if args.check:
                    if not path.is_file() or path.read_bytes() != contents:
                        raise ValueError(f"reference changed: {ref['result_path']}")
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(contents)
                records.append({"question_id": question["id"], "result_path": ref["result_path"], "sql_sha256": hashlib.sha256(ref["sql"].encode()).hexdigest(), "row_count": len(rows), "columns": meta, "value_kinds": kinds, "top_n": boundary[0] if boundary else None, "tie_column": boundary[1] if boundary else None, "postprocess": ref.get("postprocess"), "postprocess_details": postprocess_details, "sha256": hashlib.sha256(contents).hexdigest()})
                print(f"{question['id']} {ref['result_path']} {len(rows)} rows", flush=True)
    finally:
        sess.close()
    manifest = {"chdb_version": chdb.__version__, "clickhouse_version": version, "max_threads": 1, "max_execution_time": 0, "unit_policy_sha256": policy_hash, "tie_quantization": "Decimal ROUND_HALF_EVEN; amount=2; percentage /100 then 6; ratio/other=6", "csv_null": "\\N", "reference_review": "provisional; T05b independent pandas recomputation required", "records": records}
    path = REPO / "refs/MANIFEST.json"
    content = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if path.read_text() != content:
            difference = list(difflib.unified_diff(path.read_text().splitlines(), content.splitlines(), fromfile="stored manifest", tofile="recomputed manifest"))
            raise ValueError("reference manifest changed:\n" + "\n".join(difference[:40]))
    else:
        path.write_text(content)
    print(f"{'Verified' if args.check else 'Built'} {len(records)} references for {len(questions)} questions")


if __name__ == "__main__":
    main()
