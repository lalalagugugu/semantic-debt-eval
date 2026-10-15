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
            if set(ref) != {"interpretation", "sql", "result_path"} or not all(ref.values()):
                raise ValueError(f"{question['id']}: invalid reference")
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
                records.append({"question_id": question["id"], "result_path": ref["result_path"], "sql_sha256": hashlib.sha256(ref["sql"].encode()).hexdigest(), "row_count": len(rows), "columns": meta, "value_kinds": kinds, "top_n": boundary[0] if boundary else None, "tie_column": boundary[1] if boundary else None, "sha256": hashlib.sha256(contents).hexdigest()})
                print(f"{question['id']} {ref['result_path']} {len(rows)} rows", flush=True)
    finally:
        sess.close()
    manifest = {"chdb_version": chdb.__version__, "clickhouse_version": version, "max_threads": 1, "max_execution_time": 0, "unit_policy_sha256": policy_hash, "tie_quantization": "Decimal ROUND_HALF_EVEN; amount=2; percentage /100 then 6; ratio/other=6", "csv_null": "\\N", "reference_review": "provisional; T05b independent pandas recomputation required", "records": records}
    path = REPO / "refs/MANIFEST.json"
    content = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if path.read_text() != content:
            raise ValueError("reference manifest changed")
    else:
        path.write_text(content)
    print(f"{'Verified' if args.check else 'Built'} {len(records)} references for {len(questions)} questions")


if __name__ == "__main__":
    main()
