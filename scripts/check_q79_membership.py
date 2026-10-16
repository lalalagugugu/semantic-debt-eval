#!/usr/bin/env python
"""Compare Q79 boundary members under historical and current validation code.

Run with the eval uv environment and SEMDEBT_MAIN_DIR/SEMDEBT_DATA_DIR set.
Raw row snapshots stay outside the repositories. A reconstruction only proves a
historical member comparison when its raw digest matches the historical record.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import types

from chdb import session

REPO = Path(__file__).resolve().parent.parent


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(source: str, path: Path, name: str):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def member_counts(rows, kinds, policy):
    # Quantize cells using the shared cross-engine contract, preserving duplicate
    # rows. Compare these members directly; a raw JSON hash is not this test.
    return Counter(tuple(policy.quantize_tie(cell, kind) for cell, kind in zip(row, kinds, strict=True)) for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-results", type=Path, required=True)
    parser.add_argument("--new-results", type=Path, required=True)
    parser.add_argument("--old-main-ref", required=True)
    parser.add_argument("--old-snapshot", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    main_dir = Path(os.environ["SEMDEBT_MAIN_DIR"]).resolve()
    db_dir = Path(os.environ["SEMDEBT_DATA_DIR"]) / "chdb-eval"
    output_dir = args.output_dir.resolve()
    if any(output_dir.is_relative_to(root) for root in (REPO, main_dir)):
        raise ValueError("row snapshots must be stored outside both repositories")
    output_dir.mkdir(parents=True, exist_ok=False)

    old_results = json.loads(args.old_results.read_text())
    new_results = json.loads(args.new_results.read_text())
    old_check = next(c for c in old_results["boundary_checks"] if c["question_id"] == 79)
    new_check = next(c for c in new_results["boundary_checks"] if c["question_id"] == 79)
    policy_path = main_dir / "harness/value_units.py"
    old_policy = subprocess.run(["git", "show", f"{args.old_main_ref}:harness/value_units.py"], cwd=main_dir, check=True, capture_output=True).stdout
    current_policy = policy_path.read_bytes()
    old_policy_hash, current_policy_hash = digest(old_policy), digest(current_policy)
    policy_versions = {
        "old_recorded_unit_policy_sha256": old_results.get("unit_policy_sha256"),
        "new_recorded_unit_policy_sha256": new_results.get("unit_policy_sha256"),
        "old_source_unit_policy_sha256": old_policy_hash,
        "new_source_unit_policy_sha256": current_policy_hash,
        "source_policies_equal": old_policy == current_policy,
    }
    print(json.dumps(policy_versions, ensure_ascii=False), flush=True)
    if old_policy != current_policy:
        raise ValueError("unit policies differ; reconstruct each version separately before comparing members")
    spec = importlib.util.spec_from_file_location("q79_unit_policy", policy_path)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    validator_path = main_dir / "scripts/validate_scorer.py"
    old_source = subprocess.run(["git", "show", f"{args.old_main_ref}:scripts/validate_scorer.py"], cwd=main_dir, check=True, capture_output=True, text=True).stdout
    old_validator = load_module(old_source, validator_path, "q79_old_validator")
    new_validator = load_module(validator_path.read_text(), validator_path, "q79_new_validator")
    policy_versions.update(
        old_boundary_policy_sha256=digest(old_source.encode()),
        new_boundary_policy_sha256=digest(validator_path.read_bytes()),
        serialization_version="json-compact-utf8-v1",
    )
    questions = json.loads((REPO / "vendor/cube/text_to_sql_benchmark.json").read_text())["questions"]
    sql = next(q["expected_sql"] for q in questions if int(q["id"]) == 79)
    snapshots = []
    for label, validator, expected in (("old_code_reconstruction", old_validator, old_check), ("new_code_reconstruction", new_validator, new_check)):
        sess = session.Session(str(db_dir))
        try:
            sess.query("SET max_execution_time = 30")
            sess.query("SET max_threads = 1")
            rules = validator.question_rules(79, sql)
            rows, check, _ = validator.stable_reference(sess, sql, 79, rules)
        finally:
            sess.close()
        snapshot = {"question_id": 79, "unit_policy_sha256": current_policy_hash, "boundary_policy_sha256": policy_versions["old_boundary_policy_sha256" if label.startswith("old_") else "new_boundary_policy_sha256"], "serialization_version": "json-compact-utf8-v1", "value_kinds": rules["value_kinds"], "row_count": len(rows), "sha256": check["sha256"], "rows": rows}
        (output_dir / f"{label}.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
        snapshots.append(snapshot)
    old_snapshot, new_snapshot = snapshots
    if args.old_snapshot:
        old_snapshot = json.loads(args.old_snapshot.read_text())
        if old_validator.reference_digest(old_snapshot["rows"]) != old_check["sha256"]:
            raise ValueError("old snapshot does not match the historical raw digest")
    old_members = member_counts(old_snapshot["rows"], old_snapshot["value_kinds"], policy)
    new_members = member_counts(new_snapshot["rows"], new_snapshot["value_kinds"], policy)
    old_recovered = old_validator.reference_digest(old_snapshot["rows"]) == old_check["sha256"]
    new_recovered = new_validator.reference_digest(new_snapshot["rows"]) == new_check["sha256"]
    members_equal = old_members == new_members
    old_ids = Counter(row[0] for row in old_snapshot["rows"])
    new_ids = Counter(row[0] for row in new_snapshot["rows"])
    result = {
        "question_id": 79,
        "policy_versions": policy_versions,
        "old_record_sha256": old_check["sha256"],
        "new_record_sha256": new_check["sha256"],
        "old_row_count": old_snapshot["row_count"],
        "new_row_count": new_snapshot["row_count"],
        "old_snapshot_matches_record": old_recovered,
        "new_snapshot_matches_record": new_recovered,
        "quantized_member_multisets_equal": members_equal,
        "member_id_multisets_equal": old_ids == new_ids,
        "old_unique_member_ids": len(old_ids),
        "new_unique_member_ids": len(new_ids),
        "removed_members": sum((old_members - new_members).values()),
        "added_members": sum((new_members - old_members).values()),
        "historical_member_comparison": "equal" if old_recovered and new_recovered and members_equal else "different" if old_recovered and new_recovered else "unavailable",
        "eval_v1_top_n_gate": "pass" if old_recovered and new_recovered and members_equal else "blocked_different_members" if old_recovered and new_recovered else "blocked_pending_historical_members",
    }
    (output_dir / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
