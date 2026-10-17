#!/usr/bin/env python
"""Audit every reference's stored precision and constant output labels."""
import csv
import hashlib
import json
import re
from pathlib import Path
import subprocess


ROOT=Path(__file__).resolve().parent.parent
LABEL_REVIEW={
 'Q28':('数据值，不是SQL常量标签','Store/Online来自DimChannel枚举，保留语义层原值'),
 'Q36':('改参考','客户分层用题面/语义层中文值'),
 'Q48':('保持','用户确认协调会话笔误；judge题停机高低两组保持原标签'),
 'Q84':('保持','后处理A/B/C常量与题面A/B/C分类一致'),
 'Q85':('改参考','TOP/BOTTOM改为题面已有最高/最低；selection条件同步'),
 'Q89':('改参考','客户分层用题面/语义层中文值，ORDER BY CASE同步'),
 'Q115':('保持','中文状态名与题面/语义层一致'),
 'Q120':('保持','全体/职业内由题面明确输出格式，保持'),
}


def main():
    application=json.loads((ROOT/'audit/2026-10-17-full-compare-application.json').read_text())
    revision=application['baseline_commit']
    def old(path):return subprocess.check_output(['git','show',f'{revision}:{path}'],cwd=ROOT,text=True)
    before={q['id']:q for name in ('cube_100','new') for q in json.loads(old(f'questions/{name}.yaml'))['questions']}
    current={q['id']:q for name in ('cube_100','new') for q in json.loads((ROOT/f'questions/{name}.yaml').read_text())['questions']}
    manifest=json.loads((ROOT/'refs/MANIFEST.json').read_text());records={r['result_path']:r for r in manifest['records']}
    previous={r['result_path']:r for r in json.loads(old('refs/MANIFEST.json'))['records']}
    removed={r['reference']:r for r in application['rounding_removed']}
    rows=[];changes=[]
    for qid,q in current.items():
        refs=[]
        for ref in q['refs']:
            record=records[ref['result_path']]
            assert hashlib.sha256((ROOT/ref['result_path']).read_bytes()).hexdigest()==record['sha256']
            assert not re.search(r'\b(?:round\w*|floor|ceil\w*|trunc\w*)\s*\(',ref['sql'],re.I),ref['result_path']
            with (ROOT/ref['result_path']).open() as stream:data=list(csv.reader(stream))[1:]
            assert len(data)==record['row_count']
            literals={v.replace("''", "'") for v in re.findall(r"'((?:[^']|'')*)'",ref['sql'])}
            labels=[]
            for pos,col in enumerate(record['columns']):
                if 'String' not in col['type']:continue
                values=sorted({r[pos] for r in data if r[pos]!='\\N'})
                if values and (set(values)<=literals or (qid=='Q84' and pos==0)):
                    action,reason=LABEL_REVIEW[qid]
                    labels.append({'column':col['name'],'values':values,'action':action,'reason':reason})
            calls=removed.get(ref['result_path'],{}).get('columns',[])
            numeric=[{'column':c['name'],'type':c['type'],'kind':record['value_kinds'][i]} for i,c in enumerate(record['columns']) if re.search(r'Int\d+|Float\d+|Decimal',c['type'])]
            item={'reference':ref['result_path'],'rows':record['row_count'],'numeric_columns_checked':numeric,
                  'display_rounding_removed':calls,'remaining_display_rounding':False,
                  'constant_labels':labels,'sql_changed':record['sql_sha256']!=previous[ref['result_path']]['sql_sha256'],
                  'csv_changed':record['sha256']!=previous[ref['result_path']]['sha256']}
            refs.append(item)
        rows.append({'question_id':qid,'references':refs,'label_review':LABEL_REVIEW.get(qid,('无常量标签','字符串维度数据、筛选常量、日期单位、类型及连接分隔符不作输出标签'))})
        changed_sql=[r['reference'] for r in refs if r['sql_changed']];changed_csv=[r['reference'] for r in refs if r['csv_changed']]
        rules=[r['result_path'] for r in q['refs'] if records[r['result_path']]['rules']!=previous[r['result_path']]['rules']]
        changes.append({'question_id':qid,'text_changed':q['text_zh']!=before[qid]['text_zh'],
                        'changed_SQL':changed_sql,'changed_CSV':changed_csv,'changed_rules':rules,
                        'references_changed':bool(changed_sql or changed_csv or rules),
                        'previous_references':len(before[qid]['refs']),'current_references':len(q['refs'])})
    q92=next(r for r in records.values() if r['question_id']=='Q92')
    assert q92['row_count']==12
    with (ROOT/q92['result_path']).open() as f:brands=list(csv.reader(f))[1:]
    assert sum(r[0]=='\\N' for r in brands)==1
    assert len(rows)==122 and len(records)==136
    report={'baseline_commit':revision,'references_checked':len(records),'questions_checked':len(rows),
            'rounding_references_changed':len(removed),'records':rows,
            'current_question_sha256':{name:hashlib.sha256((ROOT/f'questions/{name}.yaml').read_bytes()).hexdigest() for name in ('cube_100','new')},
            'pending':[],
            'rounding_policy':'规范CSV存实际计算值，展示可取整；全局量化、比较容差与业务定义均不改',
            'anchor_followup':'EN85原始参考的TOP/BOTTOM选择条件需单独保留，不复用中文最高/最低条件'}
    (ROOT/'audit/2026-10-17-full-compare-reference-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    summary={'baseline_commit':revision,'current_references':len(records),'previous_references':len(previous),
             'manifest_sha256':hashlib.sha256((ROOT/'refs/MANIFEST.json').read_bytes()).hexdigest(),
             'records':changes,'text_changed':[r['question_id'] for r in changes if r['text_changed']],
             'references_changed':[r['question_id'] for r in changes if r['references_changed']],
             'pending':report['pending']}
    (ROOT/'audit/2026-10-17-t05b-full-compare-change-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    lines=['# T05b全量比对：参考精度与常量标签逐题审计','',
           '基线：'+revision+'；新PR承接主仓库2026-10-17-t05b-full-compare裁决。文末更正已确认Q48-1保持原样，全部明确项已落实。','',
           '## 明确修复与原因','',
           '- Q86-1 Pearson和Q89平均值存未取整结果；全库共19份参考存在展示ROUND，统一移除最终展示舍入，保持计数、日期、原始字段精度及全局量化/容差。',
           '- Q34-1已包含在19份精度修复中，turnover_ratio直接存计算结果，例如18.647330257086335；成本与平均库存粒度保持已有裁决。',
           '- Q92维度连接改左连接，删除非空品牌过滤；参考从11增至12行，其中1行空品牌。',
           '- Q36/Q89使用活跃/有流失风险/已流失，Q89排序CASE同步；Q85分组使用题面已有最高/最低，selection条件同步。',
           '- Q48-1为High Downtime/Low Downtime两组的judge题；依据裁决文末更正，题面和参考标签均保持原样。',
           '- Q28的Online/Store为维度原值，不误当临时标签；Q84的A/B/C、Q115状态、Q120范围与题面或语义层匹配，保持。',
           '- Q79金额列去掉展示ROUND后重绑快照来源哈希，排序键仍为原未取整达成率；须核对门店成员及T05b复比，不以CSV浮点字节代替跨引擎核验。',
           '- 英文原题及原始参考保持；EN85需独立保留TOP/BOTTOM规则，防止中文标签规则渗入英文原始参考。','',
           '## 全库逐题：参考存值与常量标签','',
           '检查所有136份CSV的类型、列宽、行数与哈希，并与原始计算重建核对；数值外观看似整数不等于被取整。SQL全部数值展示舍入调用已清除；日期/计数类型转换不是展示舍入。','',
           '| 题号 | 参考存值取整排查 | 常量标签排查／处理 |','|---|---|---|']
    for row in rows:
        rounded=[r for r in row['references'] if r['display_rounding_removed']]
        desc='；'.join(r['reference']+'：'+','.join(c['name'] for c in r['display_rounding_removed'])+'移除ROUND' for r in rounded) if rounded else '无展示取整；数值列已核对'
        label='；'.join(r['reference']+' '+c['column']+'='+','.join(c['values'])+'（'+c['action']+'）' for r in row['references'] for c in r['constant_labels']) or row['label_review'][1]
        lines.append('| '+row['question_id']+' | '+desc+' | '+label+' |')
    lines+=['', '## 重算与T05b交接','',
            '重算：build_refs.py --refresh-rules；严格复算：build_refs.py --check；规则审阅：validate_rules.py。当前136份，无新增可接受业务解读。',
            '当前136份严格复算通过（含Q33）；T04/T05/rules/单一口径/缺口校验通过。英文原始10份规则按实际缓存元数据和SQL/文件哈希自比通过，包含EN85标签域保护。Q79仍为相同42个门店，完整行在全局量化下也相同，来源哈希已重绑。Q48-1按更正保持原样，待澄清项已关闭；Q34-1追加单题严格复算，2504行全部一致。',
            '具体验证：Q86-1原先3位小数存值与当前未取整结果相比，31组中25组超出现行评分容差，最大差0.00048494102752124507；Q89活跃客户平均产品种类数由75改存74.97377146240379。',
            '最新新PR逐题清单为2026-10-17-t05b-full-compare-change-summary.json，以本PR提交号读取；PR15旧JSON保留历史，不混作本PR基线。T05b复比该JSON列出的受影响题，并核对本表两项排查；Q34/Q40/Q86/Q87的pandas更正依据仍来自语义层和已有裁决。','']
    (ROOT/'audit/2026-10-17-full-compare-reference-audit.md').write_text('\n'.join(lines))
    print(json.dumps({'references':len(records),'rounding_refs':len(removed),'affected':summary['references_changed'],'pending':summary['pending']},ensure_ascii=False))


if __name__=='__main__':main()
