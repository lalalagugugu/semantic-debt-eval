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
from importlib.metadata import version as package_version
import io
import json
import os
from pathlib import Path
import re
import sys
from collections import defaultdict
from decimal import Decimal
import difflib
import subprocess

from reference_presentation import apply_presentation, ranking_domains

from chdb import session
import yaml

REPO = Path(__file__).resolve().parent.parent



def load_unit_policy():
    main_dir = os.environ.get("SEMDEBT_MAIN_DIR")
    if not main_dir:
        raise SystemExit("SEMDEBT_MAIN_DIR must be set")
    path = Path(main_dir) / "harness/value_units.py"
    spec = importlib.util.spec_from_file_location("reference_value_units", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, hashlib.sha256(path.read_bytes()).hexdigest()


def load_selection_policy():
    main_dir = os.environ.get("SEMDEBT_MAIN_DIR")
    if not main_dir:
        raise SystemExit("SEMDEBT_MAIN_DIR must be set")
    sys.dont_write_bytecode = True
    sys.path.insert(0, main_dir)
    from harness import selection
    from harness.scorer import _parse_rules
    return selection, _parse_rules


def effective_rules(question, ref):
    return ref["rules"] if "rules" in ref else question["rules"]


def has_final_order_by(sql):
    # Ignore nested queries, quoted identifiers/literals and SQL comments.
    tokens = re.findall(r"--[^\n]*|/\*[\s\S]*?\*/|'(?:''|\\.|[^'])*'|\"(?:\"\"|[^\"])*\"|`(?:``|[^`])*`|[()]|[A-Za-z_]+", sql)
    depth = 0
    previous = None
    for token in tokens:
        if token.startswith(("--", "/*")):
            continue
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
        elif depth == 0 and previous == "ORDER" and token.upper() == "BY":
            return True
        previous = token.upper() if depth == 0 else None
    return False


def validate_questions(questions, source="cube"):
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
            if not {"interpretation", "sql", "result_path"} <= set(ref) or set(ref) - {"interpretation", "sql", "result_path", "postprocess", "rules"} or not all(ref.values()):
                raise ValueError(f"{question['id']}: invalid reference")
            if question["source"] != source:
                raise ValueError(f"{question['id']}: wrong source file")
            rules = effective_rules(question, ref)
            if set(rules) - {"ordered", "top_n", "tie_columns", "value_kinds", "value_types", "selection", "order_by", "required_columns", "unordered_pairs", "identifier_columns", "rank_columns", "rankings"} or not {"ordered", "top_n", "tie_columns", "value_kinds", "value_types"} <= set(rules):
                raise ValueError(f"{question['id']}: invalid scoring rules")
            if rules['ordered'] and not rules.get('order_by'):
                raise ValueError(f"{question['id']}: ordered bank references require explicit order_by")
            _, parse_rules = load_selection_policy()
            parse_rules(rules)
            if rules["ordered"] and not has_final_order_by(ref["sql"]):
                raise ValueError(f"{question['id']}: ordered result requires final SQL ordering")
            if not isinstance(rules["value_kinds"], list) or not rules["value_kinds"] or len(rules["value_types"]) != len(rules["value_kinds"]):
                raise ValueError(f"{question['id']}: references require complete kinds/types")
            if ref.get("postprocess") not in {None, "abc_groups", "abc_groups_after", "power_customers", "store_top3", "selection", "baseline_top_decile", "product_rank_competition", "product_rank_dense"}:
                raise ValueError(f"{question['id']}: invalid postprocess")
            if not re.fullmatch(r"refs/[A-Za-z0-9/_-]+\.csv", ref["result_path"]):
                raise ValueError("invalid reference path")
            paths.append(ref["result_path"])
    if len(set(ids)) != len(ids) or len(set(paths)) != len(paths):
        raise ValueError("duplicate question ID or result path")
    start = 1 if source == "cube" else 101
    expected = 100 if source == "cube" else len(questions)
    if not questions or [f"Q{i:02d}" for i in range(start, start + expected)] != ids:
        raise ValueError(f"expected ordered {source} question IDs starting at Q{start:02d}")


def reference_value_kinds(question, ref, meta, inferred):
    rules = effective_rules(question, ref)
    declared = rules["value_kinds"]
    if len(declared) != len(meta):
        raise ValueError(f"{question['id']}: value_kinds length differs from output columns")
    if rules["value_types"] != [column["type"] for column in meta]:
        raise ValueError(f"{question['id']}: value_types differ from query output types")
    if question["source"] != "new":
        if declared != inferred:
            raise ValueError(f"{question['id']}: persisted inference differs; review and rebuild rules explicitly")
        return declared, []
    mismatches = []
    for position, (column, explicit, heuristic) in enumerate(zip(meta, declared, inferred, strict=True), 1):
        if explicit != heuristic:
            warning = {"question_id": question["id"], "column_position": position, "column_name": column["name"], "declared": explicit, "inferred": heuristic}
            print("VALUE_KIND_MISMATCH " + json.dumps(warning, ensure_ascii=False), file=sys.stderr, flush=True)
            mismatches.append(warning)
    return declared, mismatches


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


def postprocess_reference(method, meta, rows, policy, *, append_total=False):
    """Apply explicitly declared, user-approved rules to SQL aggregate domains.

    All membership decisions use the shared Decimal quantizer. The SQL supplies
    current data, never embedded answer literals. Pandas must recompute these
    rules independently in T05b rather than importing this implementation.
    """
    if method in {None, "selection"}:
        return meta, rows, None
    positions = {column["name"]: i for i, column in enumerate(meta)}
    def value(row, name):
        return row[positions[name]]
    def quantized(row, name):
        column = meta[positions[name]]
        return policy.quantize_tie(value(row, name), policy.infer_value_kind(name, column["type"]))
    if method == "baseline_top_decile":
        boundary = exact_percentile([quantized(row, "base_sales") for row in rows])
        selected = [row for row in rows if quantized(row, "base_sales") >= boundary]
        amount = sum(value(row, "sales_amount") for row in selected)
        total = value(rows[0], "total_sales")
        output = [[amount, amount * 100.0 / total if total else None]]
        output_meta = [meta[positions[name]] for name in ("sales_amount", "share_pct")]
        if append_total:
            output_meta.append(meta[positions['total_sales']])
            for row in output: row.append(total)
        return output_meta, output, {"domain_rows": len(rows), "selected_products": len(selected), "base_sales_p90": str(boundary), "percentile_method": "exact linear interpolation at (n-1)*0.9", "selected_product_keys": [value(row, "ProductKey") for row in selected]}
    if method in {"product_rank_competition", "product_rank_dense"}:
        amounts = {}
        for row in rows:
            key = value(row, "ProductKey")
            amount = quantized(row, "global_sales")
            if key in amounts and amounts[key] != amount:
                raise ValueError("product global sales inconsistent across stores")
            amounts[key] = amount
        groups = defaultdict(list)
        for key, amount in amounts.items():
            groups[amount].append(key)
        ranks = {}
        offset = 1
        for dense_rank, (_, keys) in enumerate(sorted(groups.items(), reverse=True), 1):
            for key in keys:
                ranks[key] = dense_rank if method == "product_rank_dense" else offset
            offset += len(keys)
        keep = [i for i, column in enumerate(meta) if column["name"] != "global_sales"]
        output = []
        for row in rows:
            row = list(row)
            row[positions["global_rank"]] = ranks[value(row, "ProductKey")]
            output.append([row[i] for i in keep])
        return [meta[i] for i in keep], output, {"domain_rows": len(rows), "products": len(amounts), "rank_method": method, "quantized_ranking": True, "rank_blocks": [
            {"group": [], "rank": 1 + sum(len(v) for amount,v in groups.items() if amount > value),
             "dense": dense, "size": len(keys)}
            for dense,(value,keys) in enumerate(sorted(groups.items(),reverse=True),1)]}
    if method in {"abc_groups", "abc_groups_after"}:
        groups = defaultdict(list)
        for row in rows:
            groups[quantized(row, "revenue")].append(row)
        total = sum((revenue * len(members) for revenue, members in groups.items()), Decimal(0))
        if total <= 0:
            raise ValueError("ABC requires positive total revenue")
        buckets = {name: [0, Decimal(0)] for name in ("A", "B", "C")}
        cumulative = Decimal(0)
        for revenue, members in sorted(groups.items(), reverse=True):
            if method == "abc_groups_after":
                cumulative += revenue * len(members)
                name = "A" if cumulative <= total * Decimal("0.8") else "B" if cumulative <= total * Decimal("0.95") else "C"
            else:
                name = "A" if cumulative < total * Decimal("0.8") else "B" if cumulative < total * Decimal("0.95") else "C"
            buckets[name][0] += len(members)
            buckets[name][1] += revenue * len(members)
            if method == "abc_groups":
                cumulative += revenue * len(members)
        columns = [{"name": "abc_class", "type": "String"}, {"name": "product_count", "type": "UInt64"}, {"name": "revenue", "type": "Float64"}, {"name": "pct_of_revenue", "type": "Float64"}]
        output = [[name, count, float(revenue), float(revenue * 100 / total)] for name, (count, revenue) in buckets.items() if count]
        if append_total:
            columns.append({'name':'total_revenue_amount','type':'Float64'})
            for row in output: row.append(float(total))
        return columns, output, {"domain_rows": len(rows), "same_amount_groups": len(groups), "quantized_total_revenue": str(total)}
    if method == "power_customers":
        order_p90 = exact_percentile([quantized(row, "orders") for row in rows])
        amount_p90 = exact_percentile([quantized(row, "avg_order_amount") for row in rows])
        selected = [row for row in rows if quantized(row, "orders") >= order_p90 and quantized(row, "avg_order_amount") >= amount_p90]
        return meta, selected, {"domain_rows": len(rows), "orders_p90": str(order_p90), "avg_order_amount_p90": str(amount_p90), "percentile_method": "exact linear interpolation at (n-1)*0.9"}
    if method == "store_top3":
        if not {"StoreKey", "ProductKey", "ProductName"} <= positions.keys():
            raise ValueError("store_top3 requires stable store/product keys and nullable product names")
        groups = defaultdict(list)
        for row in rows:
            groups[value(row, "StoreKey")].append(row)
        selected = []
        orphan_members = []
        for store, members in sorted(groups.items()):
            keys = [value(row, "ProductKey") for row in members]
            if len(keys) != len(set(keys)):
                raise ValueError("store_top3 domain repeats a store/product identity")
            members.sort(key=lambda row: json.dumps(row, ensure_ascii=False))
            members.sort(key=lambda row: quantized(row, "product_sales"), reverse=True)
            boundary = quantized(members[min(3, len(members)) - 1], "product_sales")
            winners = [row for row in members if quantized(row, "product_sales") >= boundary]
            selected.extend(winners)
            strict_orphan_count = sum(value(row, "ProductName") is None and quantized(row, "product_sales") > boundary for row in winners)
            orphan_boundary_count = sum(value(row, "ProductName") is None and quantized(row, "product_sales") == boundary for row in winners)
            non_orphan_boundary_count = sum(value(row, "ProductName") is not None and quantized(row, "product_sales") == boundary for row in winners)
            remaining_slots = min(3, len(members)) - sum(quantized(row, "product_sales") > boundary for row in winners)
            for row in winners:
                if value(row, "ProductName") is None:
                    orphan_members.append({
                        "StoreKey": store, "StoreName": value(row, "StoreName"),
                        "ProductKey": value(row, "ProductKey"),
                        "product_sales": value(row, "product_sales"),
                        "pct_of_store": value(row, "pct_of_store"),
                        "selection_role": "strict_prefix" if quantized(row, "product_sales") > boundary else "boundary",
                        "minimum_orphans_in_any_valid_selection": strict_orphan_count + max(0, remaining_slots - non_orphan_boundary_count),
                        "orphan_boundary_members": orphan_boundary_count,
                    })
        keep = [i for i, column in enumerate(meta) if column["name"] != "StoreKey"]
        return [meta[i] for i in keep], [[row[i] for i in keep] for row in selected], {"domain_rows": len(rows), "groups": len(groups), "top_n_per_store": 3, "complete_boundary": True, "product_identity": "ProductKey", "missing_product_name": "NULL; retain and disclose ProductKey", "orphan_topn_members": orphan_members, "orphan_topn_member_count": len(orphan_members), "stores_with_orphan_topn_members": len({row["StoreKey"] for row in orphan_members})}
    raise ValueError(f"unsupported postprocess: {method}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--question", action="append", help="recompute only these IDs; preserve all other manifest records")
    parser.add_argument("--refresh-rules", action="store_true", help="persist external-column inference and actual return types for review")
    args = parser.parse_args()
    if args.check and args.refresh_rules:
        parser.error("--check cannot change rules; omit --refresh-rules")
    data_dir = os.environ.get("SEMDEBT_DATA_DIR")
    if not data_dir:
        raise SystemExit("SEMDEBT_DATA_DIR must be set")
    db = Path(data_dir) / "chdb-eval"
    if not db.is_dir():
        raise SystemExit("chdb-eval does not exist; rebuild it from Parquet first")
    policy, policy_hash = load_unit_policy()
    selection_policy, _ = load_selection_policy()
    presentation_path = REPO / 'refs/PRESENTATION.json'
    presentation = json.loads(presentation_path.read_text()) if presentation_path.exists() else {}
    previous_manifest=json.loads(subprocess.check_output(['git','show',presentation['baseline']+':refs/MANIFEST.json'],cwd=REPO)) if presentation else json.loads((REPO/'refs/MANIFEST.json').read_text())
    old_records = {r['result_path']:r for r in previous_manifest['records']}
    input_paths = [REPO / filename for filename in ("questions/cube_100.yaml", "questions/new.yaml", "refs/MANIFEST.json", "refs/PRESENTATION.json")]
    input_hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in input_paths if path.exists()}
    questions = yaml.safe_load((REPO / "questions/cube_100.yaml").read_text())["questions"]
    validate_questions(questions)
    new_path = REPO / "questions/new.yaml"
    if new_path.exists():
        new_questions = yaml.safe_load(new_path.read_text())["questions"]
        validate_questions(new_questions, "new")
        questions += new_questions
    all_questions = questions
    if args.question:
        wanted = set(args.question)
        if not wanted <= {question["id"] for question in questions}:
            raise ValueError("unknown --question ID")
        questions = [question for question in questions if question["id"] in wanted]
    records = []
    pending_writes = []
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
                rules = effective_rules(question, ref)
                n = rules["top_n"]
                if n is not None:
                    sql, replacements = re.subn(rf"\bLIMIT\s+{n}\s*;?\s*$", "", sql, flags=re.I)
                    if replacements != 1:
                        raise ValueError(f"{question['id']}: cannot extend boundary")
                try:
                    payload = json.loads(str(sess.query(sql, "JSONCompact")))
                except Exception as error:
                    raise RuntimeError(f"{question['id']} {ref['result_path']}: reference execution failed; build aborted and session closed") from error
                meta, rows = payload["meta"], payload["data"]
                display = presentation.get('references',{}).get(ref['result_path'],{})
                meta, rows, postprocess_details = postprocess_reference(ref.get("postprocess"), meta, rows, policy, append_total=display.get('append_postprocess_total',False))
                count_aliases = {m.group(1).lower() for m in re.finditer(r"(?:\bSELECT\s+|,)\s*(?:count|countDistinct|countIf|uniqExact)\s*\([^)]*\)\s+(?:AS\s+)?([A-Za-z_]\w*)", sql, re.I)}
                kinds = ["count" if c["name"].lower() in count_aliases else policy.infer_value_kind(c["name"], c["type"]) for c in meta]
                selection_checks = None
                if rules.get("selection") is not None:
                    rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False))
                    rows, selection_checks = selection_policy.complete_selection(rows, rules["selection"], kinds)
                elif n is not None:
                    columns = rules["tie_columns"]
                    if not columns:
                        raise ValueError(f"{question['id']}: Top-N requires tie_columns")
                    key = lambda row: tuple(policy.quantize_tie(row[i], kinds[i]) for i in columns)
                    # Ranking direction comes from the declared reference SQL.
                    descending = not bool(re.search(r"\bASC\s*(?:LIMIT\s+\d+)?\s*;?\s*$", ref["sql"], re.I))
                    rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False))
                    rows.sort(key=key, reverse=descending)
                    if len(rows) < n:
                        raise ValueError(f"{question['id']}: insufficient ranked rows")
                    cut = n
                    while cut < len(rows) and key(rows[cut]) == key(rows[n - 1]):
                        cut += 1
                    rows = rows[:cut]
                elif not rules["ordered"]:
                    rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False))
                meta, rows = apply_presentation(meta, rows, policy, display)
                kinds = ["count" if c['name'].lower() in count_aliases else policy.infer_value_kind(c['name'],c['type']) for c in meta]
                inferred_kinds=kinds[:]
                if args.refresh_rules:
                    if question['source']=='new':
                        declared=presentation.get('declared_new_value_kinds',{}).get(ref['result_path'],{})
                        missing_declarations=[c['name'] for c in meta if c['name'] not in declared]
                        if missing_declarations:raise ValueError('new reference kinds must be explicitly declared: '+str(missing_declarations))
                        kinds=[declared[c['name']] for c in meta]
                    original=old_records.get(ref['result_path'])
                    required=presentation.get('base_required_columns',{}).get(ref['result_path'],rules.get('required_columns'))
                    if presentation and original:
                        old_names=[c['name'] for c in original['columns']]
                        current_names=[c['name'] for c in meta]
                        required_names={old_names[i] for i in required or range(len(old_names))}
                        required=[i for i,name in enumerate(current_names) if name in required_names or name not in old_names]
                        required=presentation.get('overrides',{}).get(ref['result_path'],required)
                        required=sorted(set(required+presentation.get('existing_required_columns',{}).get(ref['result_path'],[])))
                    rules={**rules,'value_kinds':kinds,'value_types':[c['type'] for c in meta]}
                    if required is not None:rules['required_columns']=required
                    for field,key in [('identifier_columns','identifier_column_names'),('rank_columns','rank_column_names')]:
                        names=presentation.get(key,{}).get(ref['result_path'],[])
                        indexes=[i for i,c in enumerate(meta) if c['name'] in names]
                        if indexes:rules[field]=indexes
                        else:rules.pop(field,None)
                    ref['rules']=rules
                rankings = ranking_domains(meta,rows,display,population_blocks=(postprocess_details or {}).get('rank_blocks'))
                if rankings:
                    rules={**rules,'rankings':rankings}
                    if args.refresh_rules:ref['rules']=rules
                kinds, kind_warnings = reference_value_kinds(question, ref, meta, inferred_kinds)
                contents = csv_bytes(meta, rows)
                path = REPO / ref["result_path"]
                if args.check:
                    if not path.is_file() or path.read_bytes() != contents:
                        raise ValueError(f"reference changed: {ref['result_path']}")
                else:
                    pending_writes.append((path, contents))
                records.append({"question_id": question["id"], "result_path": ref["result_path"], "sql_sha256": hashlib.sha256(ref["sql"].encode()).hexdigest(), "row_count": len(rows), "columns": meta, "value_kinds": kinds, "ordered": rules["ordered"], "top_n": n, "tie_column": rules["tie_columns"][0] if len(rules["tie_columns"]) == 1 else None, "postprocess": ref.get("postprocess"), "postprocess_details": postprocess_details, "sha256": hashlib.sha256(contents).hexdigest()})
                records[-1].update(value_types=rules["value_types"], value_kind_source="declared" if question["source"] == "new" else "inferred", value_kind_warnings=kind_warnings, rules=rules, selection_checks=selection_checks)
                if display:
                    records[-1]['presentation_sha256']=hashlib.sha256(json.dumps(display,sort_keys=True).encode()).hexdigest()
                print(f"{question['id']} {ref['result_path']} {len(rows)} rows", flush=True)
    finally:
        sess.close()
    manifest = {"chdb_version": package_version("chdb"), "clickhouse_version": version, "max_threads": 1, "max_execution_time": 0, "unit_policy_sha256": policy_hash, "tie_quantization": "Decimal ROUND_HALF_EVEN; amount=2; percentage /100 then 6; ratio/other=6", "csv_null": "\\N", "reference_review": "provisional; T05b independent pandas recomputation required", "records": records}
    if presentation:
        manifest['presentation_sha256']=hashlib.sha256(presentation_path.read_bytes()).hexdigest()
    path = REPO / "refs/MANIFEST.json"
    if args.question:
        previous = json.loads(path.read_text())
        if previous.get("presentation_sha256") != manifest.get("presentation_sha256"):
            old_presentation_bytes = subprocess.check_output(['git', 'show', 'HEAD:refs/PRESENTATION.json'], cwd=REPO)
            if hashlib.sha256(old_presentation_bytes).hexdigest() != previous.get("presentation_sha256"):
                raise ValueError("targeted build requires the previous presentation in HEAD")
            selected_paths = {ref["result_path"] for question in questions for ref in question["refs"]}
            def unselected_presentation(spec):
                return {key: {path: value for path, value in section.items() if path not in selected_paths}
                        if isinstance(section, dict) else section for key, section in spec.items()}
            if unselected_presentation(json.loads(old_presentation_bytes)) != unselected_presentation(presentation):
                raise ValueError("targeted build cannot change unselected presentation rules")
        runtime_keys = set(previous) | set(manifest)
        runtime_keys -= {"records", "presentation_sha256"}
        if any(previous.get(key) != manifest.get(key) for key in runtime_keys):
            raise ValueError("targeted build cannot mix runtime or quantization versions")
        replacements = {record["result_path"]: record for record in records}
        expected = {ref["result_path"] for question in all_questions for ref in question["refs"]}
        previous_paths = {record["result_path"] for record in previous["records"]}
        if previous_paths - expected or expected - previous_paths - replacements.keys():
            raise ValueError("targeted build cannot remove references or add unselected references; use a full build")
        manifest["records"] = [replacements.get(record["result_path"], record) for record in previous["records"]]
        manifest["records"].extend(record for record in records if record["result_path"] not in previous_paths)
    content = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if path.read_text() != content:
            difference = list(difflib.unified_diff(path.read_text().splitlines(), content.splitlines(), fromfile="stored manifest", tofile="recomputed manifest"))
            raise ValueError("reference manifest changed:\n" + "\n".join(difference[:40]))
    else:
        for input_path, digest in input_hashes.items():
            if hashlib.sha256(input_path.read_bytes()).hexdigest() != digest:
                raise RuntimeError(f"concurrent edit detected: {input_path.name}; no reference files written")
        for result_path, contents in pending_writes:
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_bytes(contents)
        path.write_text(content)
    if args.refresh_rules:
        for source,filename in [('cube','cube_100'),('new','new')]:
            source_questions=[q for q in all_questions if q['source']==source]
            for question in source_questions:
                reference_rules=[effective_rules(question,ref) for ref in question['refs']]
                question['rules']=reference_rules[0]
                for ref,rule in zip(question['refs'],reference_rules,strict=True):
                    if rule==question['rules']:ref.pop('rules',None)
                    else:ref['rules']=rule
            (REPO/f'questions/{filename}.yaml').write_text(json.dumps({'questions':source_questions},ensure_ascii=False,indent=2)+'\n')
    print(f"{'Verified' if args.check else 'Built'} {len(records)} references for {len(questions)} questions")


if __name__ == "__main__":
    main()
