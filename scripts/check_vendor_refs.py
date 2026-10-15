#!/usr/bin/env python
"""Re-execute the vendored reference SQL against ``chdb-eval``.

The machine-readable output intentionally contains question IDs and comparison
diagnostics only.  Question text and SQL stay in the private eval repository.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any


RELATIVE_TOLERANCE = 0.005
RUN_ID = "paper-2026-04-22"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    data_dir = os.environ.get("SEMDEBT_DATA_DIR")
    if not data_dir:
        raise SystemExit("SEMDEBT_DATA_DIR must be set")

    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=Path(data_dir) / "chdb-eval")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=repo)
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def values_match(expected: object, actual: object) -> bool:
    if is_number(expected) and is_number(actual):
        expected_float = float(expected)
        actual_float = float(actual)
        if not math.isfinite(expected_float) or not math.isfinite(actual_float):
            return expected_float == actual_float
        return abs(actual_float - expected_float) <= RELATIVE_TOLERANCE * abs(expected_float)
    return type(expected) is type(actual) and expected == actual


def row_signature(row: list[object]) -> tuple[object, ...]:
    """Bucket rows by exact non-numeric cells before matching numeric cells."""
    return tuple(("number",) if is_number(value) else (type(value).__name__, value) for value in row)


def row_sort_key(row: list[object]) -> tuple[tuple[str, object], ...]:
    key: list[tuple[str, object]] = []
    for value in row:
        if is_number(value):
            key.append(("number", float(value)))
        elif value is None:
            key.append(("none", ""))
        else:
            key.append((type(value).__name__, str(value)))
    return tuple(key)


def row_matches(expected: list[object], actual: list[object]) -> bool:
    return len(expected) == len(actual) and all(
        values_match(expected_value, actual_value)
        for expected_value, actual_value in zip(expected, actual, strict=True)
    )


def mismatch_detail(expected: list[object], actual: list[object]) -> dict[str, object]:
    if len(expected) != len(actual):
        return {"reason": "column_count", "expected": len(expected), "actual": len(actual)}
    for column, (expected_value, actual_value) in enumerate(zip(expected, actual, strict=True)):
        if values_match(expected_value, actual_value):
            continue
        detail: dict[str, object] = {
            "reason": "value",
            "column": column,
            "expected": expected_value,
            "actual": actual_value,
        }
        if is_number(expected_value) and is_number(actual_value):
            absolute_error = abs(float(actual_value) - float(expected_value))
            detail["absolute_error"] = absolute_error
            detail["relative_error"] = (
                absolute_error / abs(float(expected_value))
                if float(expected_value) != 0
                else None
            )
        return detail
    return {"reason": "unknown"}


def compare_rows(expected: list[list[object]], actual: list[list[object]]) -> dict[str, object]:
    if len(expected) != len(actual):
        subset = rows_are_subset(expected, actual) if len(expected) < len(actual) else False
        return {
            "match": False,
            "reason": "row_count",
            "expected_row_count": len(expected),
            "actual_row_count": len(actual),
            "published_rows_subset_of_local": subset,
        }

    expected_buckets: dict[tuple[object, ...], list[list[object]]] = defaultdict(list)
    actual_buckets: dict[tuple[object, ...], list[list[object]]] = defaultdict(list)
    for row in expected:
        expected_buckets[row_signature(row)].append(row)
    for row in actual:
        actual_buckets[row_signature(row)].append(row)

    if expected_buckets.keys() != actual_buckets.keys():
        return {"match": False, "reason": "non_numeric_values"}

    for signature in sorted(expected_buckets, key=repr):
        expected_group = sorted(expected_buckets[signature], key=row_sort_key)
        actual_group = sorted(actual_buckets[signature], key=row_sort_key)
        if len(expected_group) != len(actual_group):
            return {
                "match": False,
                "reason": "row_multiplicity",
                "signature": repr(signature),
                "expected": len(expected_group),
                "actual": len(actual_group),
            }
        for row_index, (expected_row, actual_row) in enumerate(
            zip(expected_group, actual_group, strict=True)
        ):
            if row_matches(expected_row, actual_row):
                continue
            return {
                "match": False,
                "reason": "values",
                "bucket_row": row_index,
                "detail": mismatch_detail(expected_row, actual_row),
            }
    return {"match": True, "reason": "matched"}


def rows_are_subset(expected: list[list[object]], actual: list[list[object]]) -> bool:
    actual_buckets: dict[tuple[object, ...], list[list[object]]] = defaultdict(list)
    for row in actual:
        actual_buckets[row_signature(row)].append(row)

    for expected_row in expected:
        candidates = actual_buckets.get(row_signature(expected_row), [])
        match_index = next(
            (index for index, actual_row in enumerate(candidates) if row_matches(expected_row, actual_row)),
            None,
        )
        if match_index is None:
            return False
        candidates.pop(match_index)
    return True


def restore_denormals(meta: list[dict[str, str]], rows: list[list[object]]) -> None:
    replacements = {"inf": math.inf, "-inf": -math.inf, "nan": math.nan}
    for row in rows:
        for index, column in enumerate(meta):
            if column["type"].startswith("Float") and row[index] in replacements:
                row[index] = replacements[str(row[index])]


def execute(sess: Any, sql: str) -> tuple[list[dict[str, str]], list[list[object]]]:
    payload = json.loads(str(sess.query(sql, "JSONCompact")))
    restore_denormals(payload["meta"], payload["data"])
    return payload["meta"], payload["data"]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    benchmark = load_json(args.repo / "vendor/cube/text_to_sql_benchmark.json")
    questions = {int(question["id"]): question for question in benchmark["questions"]}
    reference_dir = args.repo / "vendor/cube/published-runs" / RUN_ID / "reference"
    if len(questions) != 100:
        raise SystemExit(f"expected 100 questions, found {len(questions)}")

    from chdb import session

    sess = session.Session(str(args.db_dir))
    records: list[dict[str, object]] = []
    started = time.monotonic()
    try:
        sess.query("SET max_execution_time = 0")
        sess.query("SET max_threads = 1")
        sess.query("SET output_format_json_quote_denormals = 1")
        runtime_version = str(sess.query("SELECT version()", "CSV")).strip().strip('"')
        for question_id, question in sorted(questions.items()):
            published = load_json(reference_dir / f"q{question_id:02d}.json")
            sql = question["expected_sql"]
            record: dict[str, object] = {
                "question_id": question_id,
                "published_status": "unavailable" if published["error"] else "available",
                "published_row_count": published["row_count"],
                "sql_matches_published": sql.strip().rstrip(";") == published["sql"].strip().rstrip(";"),
            }
            query_started = time.monotonic()
            try:
                meta, rows = execute(sess, sql)
            except Exception as error:
                record.update(
                    {
                        "status": "local_execution_error",
                        "local_error": str(error),
                        "local_row_count": None,
                    }
                )
            else:
                record["local_row_count"] = len(rows)
                record["local_columns"] = [column["name"] for column in meta]
                if published["error"]:
                    record["status"] = "published_unavailable_local_success"
                else:
                    comparison = compare_rows(published["rows"], rows)
                    record["comparison"] = comparison
                    record["status"] = "matched" if comparison["match"] else "mismatch"
            record["elapsed_seconds"] = round(time.monotonic() - query_started, 3)
            records.append(record)
            print(
                f"Q{question_id:02d} {record['status']} "
                f"published={record['published_row_count']} local={record.get('local_row_count')} "
                f"{record['elapsed_seconds']:.3f}s",
                flush=True,
            )
    finally:
        sess.close()

    counts: dict[str, int] = defaultdict(int)
    for record in records:
        counts[str(record["status"])] += 1
    output = {
        "run_id": RUN_ID,
        "runtime": {
            "chdb_clickhouse_version": runtime_version,
            "max_threads": 1,
            "max_execution_time": 0,
            "relative_tolerance": RELATIVE_TOLERANCE,
        },
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "counts": dict(sorted(counts.items())),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["counts"], ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
