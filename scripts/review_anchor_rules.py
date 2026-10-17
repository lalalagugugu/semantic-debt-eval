#!/usr/bin/env python
"""Prepare original-reference rules for T11; do not change harness wiring.

Uses T11's already executed original anchor payloads and verifies their hashes
and SQL provenance. --check validates the review text without rewriting it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from copy import deepcopy

from build_refs import effective_rules, has_final_order_by, load_selection_policy, load_unit_policy
from check_rules_impact import contract_domain, verdict_only
from backfill_order_keys import reference_order

ROOT=Path(__file__).resolve().parent.parent
REPORT=ROOT/'audit/anchor-original-rules-review.md'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    policy,policy_hash=load_unit_policy()
    _,parse_rules=load_selection_policy()
    from scripts.validate_scorer import reference_value_kinds
    questions={int(q['id'][1:]):q for q in json.loads((ROOT/'questions/cube_100.yaml').read_text())['questions']}
    public={int(q['id']):q for q in json.loads((ROOT/'vendor/cube/text_to_sql_benchmark.json').read_text())['questions']}
    folder=Path(os.environ['SEMDEBT_DATA_DIR'])/'anchor-refs/paper-2026-04-22'
    manifest=json.loads((folder/'MANIFEST.json').read_text())
    by_id={int(r['vendor_id']):r for r in manifest['records']}
    rows=[]
    label_review=(ROOT/'audit/2026-10-17-full-compare-application.json')
    english_bucket_rules=None
    if label_review.exists():
        baseline=json.loads(label_review.read_text())['baseline_commit']
        previous=json.loads(subprocess.check_output(['git','show',f'{baseline}:questions/cube_100.yaml'],cwd=ROOT,text=True))
        english_bucket_rules=next(q['rules'] for q in previous['questions'] if q['id']=='Q85')
    normalize=lambda typ:re.sub(r'^Nullable\((.*)\)$',r'\1',typ)
    for qid,q in sorted(questions.items()):
        if qid==33 or q['scoring']=='judge':
            continue
        record=by_id[qid]
        sql=public[qid]['expected_sql']
        data=(folder/f'q{qid:02d}.json').read_bytes()
        if hashlib.sha256(data).hexdigest()!=record['sha256'] or hashlib.sha256(sql.strip().rstrip(';').encode()).hexdigest()!=record['sql_sha256']:
            raise ValueError(f'EN{qid:02d}: original payload/SQL hash mismatch')
        payload=json.loads(data)
        if not payload['rows']:
            continue
        columns=payload['meta']
        if columns!=record['columns'] or len(payload['rows'])!=record['row_count']:
            raise ValueError(f'EN{qid:02d}: original manifest metadata differs')
        types=[c['type'] for c in columns]
        if any([normalize(t) for t in effective_rules(q,r)['value_types']]==[normalize(t) for t in types] for r in q['refs']) and not (qid==85 and english_bucket_rules):
            continue
        rules={k:v for k,v in q['rules'].items() if k!='selection'}
        rules.update(value_kinds=reference_value_kinds(sql,columns),value_types=types,ordered=q['rules']['ordered'] and has_final_order_by(sql))
        if qid==74:
            _,rules=contract_domain(qid,sql,q)
            rules.update(value_kinds=reference_value_kinds(sql,columns),value_types=types)
        if qid==85 and english_bucket_rules:
            rules=deepcopy(english_bucket_rules)
            rules.update(value_kinds=reference_value_kinds(sql,columns),value_types=types)
        if rules['ordered']:
            rules['order_by'],_=reference_order(sql,columns,rules.get('selection',{}).get('output_order'))
        parse_rules(rules)
        result=verdict_only(payload['rows'],[payload['rows']],rules)
        if result.outcome!='correct':
            raise ValueError(f'EN{qid:02d}: original self-match failed: {result.reason}')
        rows.append((qid,record,columns,rules))
    expected={13,14,20,21,34,66,74,83,87}|({85} if english_bucket_rules else set())
    if {qid for qid,*_ in rows}!=expected:
        raise ValueError('unexpected structure-difference cohort; review before publishing rules')
    lines=['# 英文原始参考rules交接：不含接线变更','',
    'T11的主仓库报告已交Codex补EN13、14、20、74、83、87；本轮保留事实ProductKey后另有EN21、EN34。此次Q66删除未问的第三列后，补EN66原始三列规则。下面9份rules对应外部原始SQL及T11已实际执行保存的列meta，不覆盖中文修订参考、不修改harness接线。T11应按vendor_id及SQL哈希选择整份rules；勿将下表塞进中文refs作为额外可接受解读。',
    '',f'量纲策略SHA256：`{policy_hash}`。自动推断沿用固定reference_value_kinds及infer_value_kind，不能按列值猜量纲。原始返回类型逐字保留Nullable，比较结构时按裁决剥Nullable；count整数守卫由底层类型判断。',
    '', '全部99道英文原始参考仍由T11维护。这里仅核对已存在原始payload的SQL/文件哈希、真实列类型和9份规则自比，不宣称重新执行99份SQL。T05b仍须独立核验。',
    '', '| 原题／锚点 | 原始行数 | 类型及量纲 |','|---|---:|---|']
    for qid,record,columns,rules in rows:
        lines.append(f"| Q{qid:02d}／EN{qid:02d} | {record['row_count']} | "+'；'.join(f"{c['name']}: {c['type']} / {k}" for c,k in zip(columns,rules['value_kinds'],strict=True))+' |')
    for qid,record,columns,rules in rows:
        lines += ['',f'## EN{qid:02d}', '',f"原始SQL SHA256：`{record['sql_sha256']}`；payload SHA256：`{record['sha256']}`。",'', '```json',json.dumps(rules,ensure_ascii=False,indent=2),'```']
    if english_bucket_rules:
        lines=[line.replace('下面9份rules','下面10份rules').replace('和9份规则自比','和10份规则自比') for line in lines]
        lines.insert(2,'本轮追加EN85：中文Q85标签改为最高/最低，英文原始参考仍为TOP/BOTTOM；显式保存原始选择条件，避免同结构规则复用造成标签域不一致。原SQL/原值及harness接线保持。')
    lines+=['','EN74的选择元数据仅按原始4列重映射为门店／产品／销售额／占比，保持外部原始渠道、连接与数值，不偷换成中文修订6列参考。T11仍须按既有Top-N完整边界要求核对原始截断是否丢并列；EN87同理。EN97仍为judge且不在确定性结构不同的9份之内；不以补规则扩大确定性题集合。',
    '', 'T11接入这些rules后可评数量预计由当前修订题库的79增为87，另12道judge；此处只是规则交接，是否可评以T11接线后的自比及完整边界检查为准。复现：`uv run python scripts/review_anchor_rules.py --check`。','']
    text='\n'.join(lines)
    if args.check:
        if REPORT.read_text()!=text:
            raise ValueError('anchor rules review is stale')
    else:
        REPORT.write_text(text)
    print(f'PASS: {len(rows)} original anchor rules, actual cached metadata and SQL/payload hashes; harness wiring unchanged')


if __name__=='__main__':
    main()
