"""T05b step 1 of main decisions/2026-10-18-reference-columns-asked-only.md:
mark, for every reference of the frozen bank (eval-v1), its required columns
(0-based positions in the reference output), from the question wording only.

Required = the quantities the question asks for + the identifier column of the
objects it asks to list. Ranking keys, filter values and other unasked columns
are not required. Identifier: one display form per object (main
decisions/2026-10-17-one-convention-one-answer.md section 2); the name when it
identifies every row (no NULL, no shared name), otherwise the key. Judge
questions are skipped.

Usage: uv run python scripts/required_columns.py --eval-dir "$SEMDEBT_DATA_DIR/eval-ro-eval-v1" [--version N]
Writes audit/T05b-required-columns.json (version 1), or audit/T05b-required-columns.vN.json:
- v2: revised per main decisions/2026-10-18-judge-stratum-and-t12-audit.md section 5
  (identifiers always by name) and section 3 (a placeholder-only name is no identifier);
- v3: v2 plus Q75 off the missing-column list (shared names are the section 5 case; user, 2026-10-18).
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# ref file -> (required positions, {position: role of a non-required column}, note)
# Roles: rank_key / filter_value / not_asked / alt_identifier / grouping_detail.
A = {
    "Q01-1": ([0], {}, ""),
    "Q02-1": ([0], {}, ""),
    "Q03-1": ([0], {}, ""),
    "Q04-1": ([0], {}, ""),
    "Q05-1": ([0, 1], {}, ""),
    "Q06-1": ([0], {}, ""),
    "Q07-1": ([0], {1: "rank_key"}, ""),
    "Q08-1": ([0, 1], {}, ""),
    "Q09-1": ([0], {}, ""),
    "Q10-1": ([0], {}, ""),
    "Q11-1": ([0, 1], {}, ""),
    "Q12-1": ([0, 1], {}, ""),
    "Q13-1": ([1, 2, 3, 4], {0: "alt_identifier"}, ""),
    "Q14-1": ([0], {}, ""),
    "Q15-1": ([0, 1], {}, ""),
    "Q16-1": ([0, 1], {}, ""),
    "Q17-1": ([0, 2], {1: "not_asked"}, "题目问比例，销售额不是所问"),
    "Q18-1": ([0, 1], {}, ""),
    "Q19-1": ([0, 1], {}, ""),
    "Q20-2": ([0], {1: "alt_identifier", 2: "filter_value", 3: "filter_value"},
              "标识取产品键：61 行产品名为 NULL"),
    "Q21-1": ([1, 2], {0: "alt_identifier"}, ""),
    "Q22-1": ([0, 3], {1: "alt_identifier", 2: "alt_identifier", 4: "rank_key", 5: "rank_key"},
              "标识取客户键：姓名多为 Not Provided，不能区分客户；国家是分组"),
    "Q23-1": ([0, 2], {1: "not_asked"}, "题目问累计值，当月值不是所问"),
    "Q24-1": ([0, 3], {1: "not_asked", 2: "not_asked"}, ""),
    "Q25-1": ([0], {1: "rank_key"}, ""),
    "Q26-1": ([0, 1], {}, ""),
    "Q27-1": ([0], {1: "not_asked", 2: "not_asked", 3: "rank_key"}, ""),
    "Q28-1": ([0, 1], {}, ""),
    "Q29-1": ([0], {}, ""),
    "Q30-1": ([0, 2], {1: "not_asked"}, ""),
    "Q31-1": ([0, 1, 2], {}, ""),
    "Q32-1": ([1], {0: "not_asked"}, ""),
    "Q34-1": ([3, 4], {0: "alt_identifier", 1: "not_asked", 2: "not_asked"},
              "标识取产品键：284 行产品名为 NULL"),
    "Q35-1": ([0, 1, 3, 4], {2: "not_asked"}, ""),
    "Q36-1": ([0, 1], {}, ""),
    "Q37-1": ([0, 1, 2], {}, ""),
    "Q38-2": ([0, 3], {1: "not_asked", 2: "not_asked"},
              "题目未要求按品类，参考按品类给出；品类列作为行的标识计入必答"),
    "Q41-1": ([0], {}, ""),
    "Q43-1": ([0, 1], {}, ""),
    "Q43-2": ([0, 1], {}, ""),
    "Q47-1": ([0, 1], {}, ""),
    "Q49-2": ([0, 2], {1: "alt_identifier"}, "标识取实体键：有 2 个实体名各对应 2 个键"),
    "Q50-1": ([2], {0: "not_asked", 1: "not_asked"}, "缺列：题目问增长了多少，参考没有增长额"),
    "Q51-1": ([0], {}, ""),
    "Q52-1": ([0], {}, ""),
    "Q53-1": ([0], {}, ""),
    "Q54-1": ([0], {}, ""),
    "Q55-1": ([0], {}, ""),
    "Q56-1": ([0], {}, ""),
    "Q57-1": ([0], {}, ""),
    "Q58-1": ([0], {}, ""),
    "Q59-1": ([0], {}, ""),
    "Q60-1": ([0], {}, ""),
    "Q61-1": ([0], {1: "filter_value"}, ""),
    "Q62-1": ([0, 1, 2], {}, "销量既是所问又是筛选依据，计入必答"),
    "Q63-1": ([0, 1], {2: "not_asked"}, ""),
    "Q64-1": ([0, 1, 2], {}, ""),
    "Q65-2": ([0, 1], {2: "filter_value"}, "参考按门店逐行给出经理与门店，两列都计入必答"),
    "Q66-1": ([0, 1], {}, ""),
    "Q67-1": ([0], {1: "rank_key", 2: "filter_value"}, ""),
    "Q68-1": ([0, 1, 2], {}, ""),
    "Q69-1": ([0, 3], {1: "rank_key", 2: "not_asked"}, ""),
    "Q70-1": ([0, 1, 2], {3: "not_asked"}, ""),
    "Q71-1": ([0, 1, 2], {}, ""),
    "Q72-1": ([0, 1, 3], {2: "not_asked"}, ""),
    "Q73-1": ([0], {1: "not_asked", 2: "not_asked", 3: "rank_key"}, ""),
    "Q74-1": ([0, 1, 3], {2: "rank_key", 4: "alt_identifier"}, ""),
    "Q75-1": ([0, 1], {2: "filter_value", 3: "filter_value", 4: "filter_value"},
              "参考缺唯一标识：只有姓名，47 行与其他行同名，参考没有客户键"),
    "Q76-1": ([0, 1], {}, ""),
    "Q76-2": ([0, 1], {}, ""),
    "Q77-1": ([0, 3], {1: "not_asked", 2: "not_asked"}, ""),
    "Q78-1": ([0, 3], {1: "rank_key", 2: "rank_key"}, "名次由 order_by 检查，名次列本身不计入必答"),
    "Q79-1": ([0], {1: "not_asked", 2: "not_asked", 3: "rank_key"}, ""),
    "Q80-1": ([0, 2], {1: "not_asked"}, ""),
    "Q81-1": ([0, 1, 2], {3: "not_asked"}, ""),
    "Q82-1": ([0, 2, 3], {1: "not_asked"}, ""),
    "Q83-1": ([1, 2], {0: "not_asked"}, "题目问 2008、2009 两个人数，未问 2007 群体人数"),
    "Q84-1": ([0, 1], {2: "not_asked", 3: "not_asked"}, ""),
    "Q84-2": ([0, 1], {2: "not_asked", 3: "not_asked"}, ""),
    "Q85-1": ([0, 1, 4], {2: "not_asked", 3: "not_asked"}, "最高 / 最低分组列计入必答"),
    "Q87-1": ([3, 4], {0: "alt_identifier", 1: "not_asked", 2: "not_asked"},
              "标识取产品键：20 行产品名全为 NULL；可售天数既是所问又是排序键，计入必答"),
    "Q88-1": ([0], {1: "rank_key"}, ""),
    "Q89-1": ([0, 2, 3], {1: "not_asked"}, ""),
    "Q90-1": ([0, 1, 2, 3, 4, 5], {}, ""),
    "Q92-1": ([0], {1: "not_asked", 2: "not_asked", 3: "rank_key"}, ""),
    "Q94-1": ([0], {1: "filter_value", 2: "filter_value", 3: "rank_key"}, ""),
    "Q96-1": ([0, 3], {1: "not_asked", 2: "not_asked"}, ""),
    "Q98-1": ([0], {1: "rank_key", 2: "not_asked"}, "所依赖的季度未明确问到，不计入必答"),
    "Q98-2": ([0, 1], {2: "rank_key", 3: "not_asked"}, "年份是该解读的分组，计入必答"),
    "Q99-1": ([0, 3], {1: "not_asked", 2: "not_asked"},
              "缺列：题目问高多少，参考只有百分比，没有差额（与 Q50 同型）"),
    "Q100-1": ([0], {1: "filter_value", 2: "filter_value", 3: "not_asked"},
               "参考缺唯一标识：只有姓名，108 行中 107 行与其他行同名（多为 Not Provided），参考没有客户键"),
    "Q101-1": ([0], {}, ""),
    "Q102-1": ([0, 1], {}, ""),
    "Q103-1": ([0, 1], {}, ""),
    "Q104-1": ([0, 1, 2], {}, ""),
    "Q105-1": ([0], {}, ""),
    "Q106-1": ([0], {}, ""),
    "Q107-1": ([0], {}, ""),
    "Q108-1": ([0, 1, 2], {}, ""),
    "Q109-1": ([0, 1], {}, ""),
    "Q110-1": ([0, 1, 2], {}, ""),
    "Q111-1": ([0, 1, 2], {}, ""),
    "Q112-1": ([0, 2, 3], {1: "alt_identifier"}, "标识取员工键：1 行经理名为 NULL"),
    "Q113-1": ([0, 1, 2, 3], {}, ""),
    "Q114-1": ([0, 1], {}, ""),
    "Q115-1": ([0, 1, 2], {}, ""),
    "Q116-1": ([0, 1], {}, ""),
    "Q117-1": ([1, 2, 3, 4, 5], {0: "alt_identifier"}, ""),
    "Q118-1": ([0, 1], {}, ""),
    "Q119-1": ([1, 3, 5], {0: "alt_identifier", 2: "alt_identifier", 4: "not_asked"}, ""),
    "Q120-1": ([0, 1, 2, 3], {}, ""),
    "Q121-1": ([0, 1, 2], {}, ""),
    "Q121-2": ([0, 1, 2], {}, ""),
    "Q122-1": ([1, 3, 4, 5], {0: "alt_identifier", 2: "alt_identifier"}, ""),
}

# Questions whose reference lacks a column the question asks for.
MISSING = {
    "Q50": "增长额（题目问增长了多少；参考只有两年金额与增长率）",
    "Q99": "周末日与工作日日均销售额之差（题目问高多少；参考只有两项均值与百分比）",
    "Q75": "客户唯一标识（只有姓名，47 行重名）",
    "Q100": "客户唯一标识（只有姓名，107 行重名）",
}

# v2 (judge-stratum ruling, sections 3 and 5): ref -> replacement entry.
V2 = {
    "Q20-2": ([1], {0: "alt_identifier", 2: "filter_value", 3: "filter_value"},
              "v2：标识一律取名称（产品名）；原版取产品键"),
    "Q22-1": ([1, 2, 3], {0: "alt_identifier", 4: "rank_key", 5: "rank_key"},
              "v2：标识一律取名称（名、姓两列）；原版取客户键。国家是分组"),
    "Q34-1": ([0, 3], {1: "not_asked", 2: "not_asked", 4: "alt_identifier"},
              "v2：标识一律取名称（产品名）；原版取产品键"),
    "Q49-2": ([1, 2], {0: "alt_identifier"}, "v2：标识一律取名称（实体名）；原版取实体键"),
    "Q87-1": ([0, 3], {1: "not_asked", 2: "not_asked", 4: "alt_identifier"},
              "v2：标识一律取名称（产品名）；原版取产品键。可售天数既是所问又是排序键，计入必答"),
    "Q112-1": ([1, 2, 3], {0: "alt_identifier"}, "v2：标识一律取名称（经理名）；原版取员工键"),
    "Q100-1": ([1, 2], {0: "placeholder_name", 3: "not_asked"},
               "v2：姓名列全为占位值，不是标识，不必答；只比订单数、客单价两列的多重集。参考无客户键"),
}
MISSING_V2 = {k: v for k, v in MISSING.items() if k != "Q100"}

# v3: Q75 lacks no asked column; its shared names are the section 5 case.
V3 = {
    "Q75-1": ([0, 1], {2: "filter_value", 3: "filter_value", 4: "filter_value"},
              "v3：不缺列。标识取名称（名、姓两列），47 行与其他行同名，属第五节的重名情形，按多重集比对"),
}
MISSING_V3 = {k: v for k, v in MISSING_V2.items() if k != "Q75"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", required=True)
    ap.add_argument("--version", type=int, choices=[1, 2, 3], default=1)
    args = ap.parse_args(argv)
    v = args.version
    ann = {**A, **(V2 if v >= 2 else {}), **(V3 if v >= 3 else {})}
    E = Path(args.eval_dir)
    sha = subprocess.run(["git", "-C", str(E), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    refs, seen = [], set()
    for f in ("questions/cube_100.yaml", "questions/new.yaml"):
        for q in yaml.safe_load((E / f).read_text())["questions"]:
            for r in q["refs"]:
                key = Path(r["result_path"]).stem
                with open(E / r["result_path"], newline="") as fh:
                    header = next(csv.reader(fh))
                entry = {"question_id": q["id"], "ref": r["result_path"], "scoring": q["scoring"], "columns": header}
                if q["scoring"] == "judge":
                    entry["skipped"] = "judge"
                else:
                    req, roles, note = ann[key]
                    seen.add(key)
                    assert all(0 <= i < len(header) for i in req), key
                    assert set(req).isdisjoint(roles) and set(req) | set(roles) == set(range(len(header))), key
                    entry["required_columns"] = req
                    entry["non_required"] = [{"position": i, "column": header[i], "role": roles[i]} for i in sorted(roles)]
                    if note:
                        entry["note"] = note
                refs.append(entry)
    assert seen == set(A), set(A) - seen
    roles = {"rank_key": "排序键（Top-N 或排名依据）", "filter_value": "筛选依据的值", "not_asked": "题目没问的量",
             "alt_identifier": "同一对象的另一种标识（键或名称，只留一份）"}
    basis = "main decisions/2026-10-18-reference-columns-asked-only.md sections 2-3; question wording only"
    if v >= 2:
        roles["placeholder_name"] = "名称列全为占位值，不是标识"
        basis += "; revised per main decisions/2026-10-18-judge-stratum-and-t12-audit.md sections 3 and 5"
    if v >= 3:
        basis += "; Q75 off the missing-column list (user ruling 2026-10-18, section 5 shared-name case)"
    out = {"eval_tag": "eval-v1", "eval_commit": sha, "basis": basis, "roles": roles,
           "counts": {"references": len(refs), "annotated": sum("required_columns" in r for r in refs),
                      "judge_skipped": sum("skipped" in r for r in refs)},
           "missing_asked_columns": {1: MISSING, 2: MISSING_V2, 3: MISSING_V3}[v], "references": refs}
    if v >= 2:
        out = {"version": v, **out}
    name = f"T05b-required-columns.v{v}.json" if v >= 2 else "T05b-required-columns.json"
    (ROOT / "audit" / name).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(out["counts"])


if __name__ == "__main__":
    main()
