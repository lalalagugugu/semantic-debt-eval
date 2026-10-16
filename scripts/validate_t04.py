#!/usr/bin/env python
"""Validate T04 artifacts and approved exact-boundary behavior without a DB."""
import argparse
import csv
from decimal import Decimal
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re

import yaml

from build_refs import load_unit_policy, exact_percentile, postprocess_reference, validate_questions
from audit_reference_data_quality import inspect_reference

REPO = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures-only", action="store_true", help="run synthetic checks without reading reference artifacts")
    args = parser.parse_args()
    policy, _ = load_unit_policy()
    sample = {"id": "synthetic"}
    ref = {"result_path": "synthetic.csv", "sql": "SELECT sum(f.SalesAmount) FROM retail.FactSales f JOIN retail.DimProduct p ON f.ProductKey=p.ProductKey"}
    assert inspect_reference(sample, ref, "fixture")["fact_product_inner_exposure"]
    ref["sql"] = ref["sql"].replace("JOIN retail.DimProduct", "LEFT JOIN retail.DimProduct")
    assert not inspect_reference(sample, ref, "fixture")["fact_product_inner_exposure"]
    ref["sql"] = "SELECT sum(f.SalesAmount) FROM retail.DimProduct p JOIN retail.FactSales f ON f.ProductKey=p.ProductKey"
    assert inspect_reference(sample, ref, "fixture")["fact_product_inner_exposure"]
    ref["sql"] = "SELECT count() FROM retail.DimEmployee"
    assert not inspect_reference(sample, ref, "fixture")["fact_employee_inner_exposure"]
    ref["sql"] = "SELECT sum(f.SalesAmount) FROM retail.FactSales f JOIN retail.DimStore s ON f.StoreKey=s.StoreKey JOIN retail.DimEmployee e ON s.EmployeeKey=e.EmployeeKey"
    assert inspect_reference(sample, ref, "fixture")["fact_employee_inner_exposure"]
    assert exact_percentile([Decimal(0), Decimal(10)]) == Decimal(9)
    assert exact_percentile([Decimal(0), Decimal(10), Decimal(20)]) == Decimal(18)
    assert exact_percentile([Decimal(7)]) == Decimal(7)
    revenue_meta = [{"name": "ProductKey", "type": "Int32"}, {"name": "revenue", "type": "Float64"}]
    _, rows, _ = postprocess_reference("abc_groups", revenue_meta, [[1, 60], [2, 15], [3, 15], [4, 10]], policy)
    assert [(r[0], r[1], r[2]) for r in rows] == [("A", 3, 90.0), ("B", 1, 10.0)]
    _, rows, _ = postprocess_reference("abc_groups", revenue_meta, [[1, 79], [2, 11], [3, 6], [4, 4]], policy)
    assert [(r[0], r[1]) for r in rows] == [("A", 2), ("B", 1), ("C", 1)]
    assert policy.quantize_tie(Decimal("1.005"), "amount") == Decimal("1.00")
    power_meta = [{"name": name, "type": typ} for name, typ in [("customer_name", "String"), ("orders", "UInt64"), ("avg_order_amount", "Float64"), ("lifetime_value", "Float64")]]
    _, rows, details = postprocess_reference("power_customers", power_meta, [["a", 1, 10, 10], ["b", 2, 20, 40], ["c", 3, 30, 90], ["d", 3, 30, 90]], policy)
    assert [r[0] for r in rows] == ["c", "d"]
    assert Decimal(details["orders_p90"]) == 3
    store_meta = [{"name": name, "type": typ} for name, typ in [("StoreKey", "Int32"), ("StoreName", "String"), ("ProductName", "Nullable(String)"), ("product_sales", "Float64"), ("pct_of_store", "Float64"), ("ProductKey", "Int32")]]
    domain = [[1, "s1", str(i), amount, 0, i] for i, amount in enumerate([100, 90, 80, 80, 70])]
    domain += [[2, "s2", "a", 10, 0, 1], [2, "s2", "b", 9, 0, 2]]
    _, rows, details = postprocess_reference("store_top3", store_meta, domain, policy)
    assert len(rows) == 6 and sum(row[0] == "s1" for row in rows) == 4
    assert details["groups"] == 2
    orphan_domain = [[1, "s1", None, 100, 40, 10], [1, "s1", "named", 90, 36, 20], [1, "s1", None, 80, 32, 30], [1, "s1", "tied", 80, 32, 40]]
    orphan_meta, rows, details = postprocess_reference("store_top3", store_meta, orphan_domain, policy)
    assert len(rows) == 4 and len({row[-1] for row in rows}) == 4
    assert orphan_meta[-1]["name"] == "ProductKey"
    assert details["orphan_topn_member_count"] == 2
    assert {row["ProductKey"] for row in details["orphan_topn_members"]} == {10, 30}
    assert all(row["minimum_orphans_in_any_valid_selection"] == 1 for row in details["orphan_topn_members"])
    try:
        postprocess_reference("store_top3", store_meta, orphan_domain + [orphan_domain[0]], policy)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate product identity must fail")
    if args.fixtures_only:
        print("PASS: synthetic data-quality paths, product identities and exact-boundary fixtures; no reference/DB validation claimed")
        return

    questions = yaml.safe_load((REPO / "questions/cube_100.yaml").read_text())["questions"]
    validate_questions(questions)
    source = json.loads((REPO / "vendor/cube/text_to_sql_benchmark.json").read_text())["questions"]
    schema = json.loads((REPO / "questions/schema.json").read_text())
    pattern = schema["properties"]["questions"]["items"]["properties"]["refs"]["items"]["properties"]["result_path"]["pattern"]
    for q, original in zip(questions, source, strict=True):
        assert q["text_en"] == original["question"], q["id"]
        assert q["text_zh"] and q["split"] is None
        assert q["labels"]["q_level"] in {"Q1", "Q2", "Q3"}
        assert q["labels"]["persona"] in {"管理层", "分析师"}
        for label in ("complexity_source", "semantic_dependency"):
            assert q["labels"][label]["primary"] in q["labels"][label]["items"]
        for ref in q["refs"]:
            assert re.fullmatch(pattern, ref["result_path"]), ref["result_path"]
    review = (REPO / "audit/reviews/2026-10-15-user-review.md").read_text()
    assert len(re.findall(r"^- \[x\] Q\d+ 中文通过$", review, re.M)) == 91
    assert len(re.findall(r"^- \[x\] Q\d+ 接受建议", review, re.M)) == 22
    current_review = (REPO / "audit/translation_flags.md").read_text()
    approved_lines = re.findall(r"^- \[[ x]\] Q\d+ (?:中文通过|接受建议).*", review, re.M)
    assert all(line in current_review for line in approved_lines)
    assert all(q["text_en"] in current_review and q["text_zh"] in current_review for q in questions)
    for qid in ("Q46", "Q97"):
        assert "不是封闭白名单" in questions[int(qid[1:]) - 1]["scoring_notes"]
    for qid in ("Q28", "Q30", "Q45", "Q49", "Q50", "Q69"):
        assert f"- [x] {qid} " in current_review.split("## 本轮仅需补确认的项目")[1]
    q40 = questions[39]
    assert q40["scoring"] == "judge"
    assert "s.CurrencyKey = er.CurrencyKey" not in q40["refs"][0]["sql"]
    assert "s.SalesAmount * er.EndOfDayRate" in q40["refs"][0]["sql"]
    assert all(value in q40["scoring_notes"] for value in ("31", "1065", "部分答案"))
    assert not yaml.safe_load((REPO / "audit/audit_decisions.yaml").read_text())["pending_user_decision"]
    with (REPO / "refs/cube/Q40-1.csv").open() as stream:
        eur = list(csv.DictReader(stream))
    assert len(eur) == 1 and Decimal(eur[0]["sales_eur"]) > 0
    manifest = json.loads((REPO / "refs/MANIFEST.json").read_text())
    assert manifest["chdb_version"] == version("chdb")
    refs = [ref for q in questions for ref in q["refs"]]
    cube_records = [record for record in manifest["records"] if record["result_path"].startswith("refs/cube/")]
    assert {ref["result_path"] for ref in refs} == {record["result_path"] for record in cube_records}
    for record in cube_records:
        path = REPO / record["result_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        with path.open(newline="") as stream:
            reader = csv.reader(stream)
            assert next(reader) == [column["name"] for column in record["columns"]]
            assert sum(1 for _ in reader) == record["row_count"]
    for qid in ("Q74", "Q87", "Q97"):
        question = next(q for q in questions if q["id"] == qid)
        for ref in question["refs"]:
            assert "LEFT JOIN retail.DimProduct" in ref["sql"]
            with (REPO / ref["result_path"]).open() as stream:
                rows = list(csv.DictReader(stream))
            assert rows and "ProductKey" in rows[0]
            assert all(row["ProductKey"] != "\\N" for row in rows)
    for number in (65, 67, 75, 80, 82, 92, 94):
        assert not re.search(r"\bLIMIT\b", questions[number - 1]["refs"][0]["sql"], re.I)
    records = {record["result_path"]: record for record in manifest["records"]}
    with (REPO / "refs/cube/Q84-1.csv").open() as stream:
        abc = list(csv.DictReader(stream))
    assert sum(int(row["product_count"]) for row in abc) == records["refs/cube/Q84-1.csv"]["postprocess_details"]["domain_rows"]
    with (REPO / "refs/cube/Q83-1.csv").open() as stream:
        cohort = next(csv.DictReader(stream))
    assert int(cohort["cohort_size_2007"]) >= int(cohort["returned_2008"]) >= int(cohort["returned_2008_and_2009"])
    with (REPO / "refs/cube/Q44-1.csv").open() as stream:
        growth = list(csv.DictReader(stream))
    assert next(row for row in growth if row["year"] == "2007")["growth_pct"] == "\\N"
    print(f"PASS: exact-boundary fixtures; 100 questions; {len(refs)} reference hashes, headers and counts; original user review retained")


if __name__ == "__main__":
    main()
