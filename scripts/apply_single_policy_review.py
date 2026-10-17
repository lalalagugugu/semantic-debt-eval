#!/usr/bin/env python
"""Apply the user's 2026-10-17 reference-policy and prompt-review ruling."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from apply_t05b_reference_corrections import round_projections
from build_refs import effective_rules

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / 'audit/2026-10-17-single-policy-review.json'

TEXT = {
    'Q07': ('最贵的前10款产品是哪些？', 'What are the 10 most expensive products?', '约定9；删除已定义的产品标价提示，保留前10参数'),
    'Q36': ('将客户划分为活跃、有流失风险和已流失。', 'Classify customers as active, at risk or churned.', '约定13；删除按最近购买时间分层的定义提示'),
    'Q45': ('哪些门店的销售坪效最高？', 'Which stores have the highest sales density?', 'L1坪效；删除括号中销售额除以面积的定义'),
    'Q50': ('2009年同店销售总额比2008年增长了多少？', 'How much did same-store total sales grow in 2009 compared with 2008?', '约定15；用同店一词替代两年均有销售的定义，保留年份'),
    'Q66': ('2009年各季度累计提供了多少折扣金额？', 'What was the total discount amount in each quarter of 2009?', '约定10；删除排除无折扣交易的定义提示'),
    'Q85': ('2009年各门店的销售目标达成率是多少？列出最高和最低的各5家门店。', 'What were store sales target attainment rates in 2009? Show the highest and lowest five stores.', '约定12；删除实际销售额除以目标销售额的公式，保留年份及两端前5'),
    'Q89': ('将客户分为活跃、有流失风险和已流失，计算各组客户的平均消费额和平均购买产品种类数。', 'For active, at-risk and churned customers, calculate average spending and average product count in each group.', '约定13及L1产品数；删除分层和去重的定义提示'),
    'Q111': ('截至2009年9月底，各门店同期销售目标达成率和全年销售目标完成率分别是多少？', 'By September 2009, what were each store\'s year-to-date and full-year sales target attainment rates?', '约定12及L1目标达成率；改用指标名，保留两种目标期间参数'),
}

SCORING_NOTES = {
    'Q10':'按L1门店状态On判定在营业；关店日期2090-12-31是未关店哨兵，不是SQL NULL。',
    'Q20':'按L1先取每个门店×产品最近快照，再按题面产品粒度汇总当前库存和安全库存后比较；不混入门店×产品预警清单。名称左连接，保留产品键与缺失名称。',
    'Q49':'只保留各级组织的完整汇总展示；同级汇总不混加父子合计。',
    'Q69':'平均折扣比例遵守L1折扣率：折扣金额合计÷折扣前原价合计，不把成交行折扣率简单平均作为另一业务口径。',
}
LABEL_NOTES = {
    'Q10':'L1门店状态On表示营业；CloseDate的2090-12-31是未关店哨兵，不接受SQL NULL替代营业判据。',
    'Q20':'L1当前库存先按门店×产品取最新快照，再按题面产品粒度汇总后与安全库存比较。',
    'Q49':'计划实际场景、收入科目；自指父键是根，向祖先汇总并列出各级，不另留仅顶层展示。',
    'Q65':'全渠道事实；按DimStore.EmployeeKey关联经理姓名，缺映射保留NULL姓名及门店；返回全部超500万美元门店。',
    'Q69':'按L1折扣率定义取折扣金额合计/折扣前原价合计，排除无折扣；按营收而非折扣深度排序。',
    'Q86':'按子品类计算相关性；依约定10排除无折扣；相关方法和样本下限的未定义默认另列缺口。',
    'Q87':'当前库存按每个门店×产品最新快照后汇总；最后90个日历日为窗口，日均销量分母遵守L1有销售天数。',
}


def main():
    if AUDIT.exists():
        raise ValueError('one-shot ruling already applied; rebuild references instead')
    paths = [ROOT/f'questions/{name}.yaml' for name in ('cube_100','new')]
    documents = [json.loads(p.read_text()) for p in paths]
    before = deepcopy(sum([d['questions'] for d in documents], []))
    if len(before) != 122 or sum(len(q['refs']) for q in before) != 165:
        raise ValueError('expected the reviewed 122-question/165-reference baseline')
    archive = ROOT/'audit/reviews/2026-10-17-before-single-policy.json'
    archive.write_text(json.dumps({'questions':before,'manifest':json.loads((ROOT/'refs/MANIFEST.json').read_text())}, ensure_ascii=False,indent=2)+'\n')
    optional = json.loads((ROOT/'audit/optional-product-group-refs.json').read_text())
    empty_paths = {r['result_path'] for item in optional['records'] for r in item['additions']}
    empty_paths.update(path for item in optional['records'] for path in item.get('existing_optional_references',[]))
    assert len(empty_paths) == 13
    fixed = {
        'refs/new/Q114-2.csv': '口径歧义：L1新客数已明确[T-89,T]，删另一端点',
        'refs/cube/Q65-1.csv': '展示方式：用户指定只留姓名标识',
        'refs/cube/Q10-2.csv': '口径歧义：L1 DimStore.Status定义On营业，CloseDate未关店为2090哨兵而非NULL',
        'refs/cube/Q10-3.csv': '口径歧义：同上，不用NULL或On并集替代已定义营业状态',
        'refs/cube/Q20-1.csv': '口径歧义：题面按产品，L1当前库存及安全库存跨店可加，保留产品汇总后比较；不混入门店产品预警清单',
        'refs/cube/Q69-2.csv': '口径歧义：L1折扣率为折扣金额/折扣前原价；不保留行折扣率简单平均',
        'refs/cube/Q49-1.csv': '展示方式：只留覆盖各级组织的完整层级展示，不另留仅顶层的示例',
    }
    questions = sum([d['questions'] for d in documents], [])
    removed = []
    text_audit = []
    extras = []
    for question, old in zip(questions,before,strict=True):
        qid = question['id']
        kept = []
        for ref in question['refs']:
            path = ref['result_path']
            reason = ('口径歧义：左连接孤儿关系，只保留含空品类行的参考' if path in empty_paths else
                      '口径歧义：所有行均算交易，删除正销量购买事件参考' if '购买事件=SalesQuantity>0' in ref['interpretation'] else fixed.get(path))
            if reason:
                removed.append({'question_id':qid,'reference':path,'reason':reason})
            else:
                ref['rules'] = deepcopy(effective_rules(question,ref))
                ref['interpretation'] = ref['interpretation'].replace('全部行／正销量（结果相同）','全部行（含纯退货行）')
                kept.append(ref)
        if not kept:
            raise ValueError('ruling removed every reference: '+qid)
        question['refs'] = kept
        question['rules'] = deepcopy(kept[0]['rules'])
        # Remove obsolete active acceptance instructions; historical audit files remain.
        notes = question['scoring_notes'].split('\n')
        question['scoring_notes'] = '\n'.join(line for line in notes if not any(term in line for term in ('购买事件双解','空产品属性组裁决')))
        question['scoring_notes']=question['scoring_notes'].replace('购买事件若有歧义仍保留全部行与正销量两种参考，相同量化结果共用参考；时间窗口以题干及逐参考解读为准。','购买事件统一为全部行（含纯退货）；日期窗口按冻结定义或题目明确参数，不另增业务口径解读。').replace('合理统计／日期解读须声明且计算一致；不把不完整随访当完整90天，不把除零报0。','业务口径按冻结约定及2026-10-17裁决；题目参数与问法歧义按逐参考说明。')
        if qid in SCORING_NOTES:question['scoring_notes']=SCORING_NOTES[qid]
        if qid in LABEL_NOTES:question['labels']['semantic_dependency']['notes']=LABEL_NOTES[qid]
        if qid=='Q86':question['scoring_notes']=question['scoring_notes'].replace('须声明是否含无折扣、样本下限和前N；','按约定10不含无折扣促销；样本下限只是声明的示例参数，不给题目增设前N；')
        if qid=='Q87':question['scoring_notes']=question['scoring_notes'].replace('原库存、90天日均销量及可售天数计算不变。','当前库存按每店产品最近快照；90天为题目窗口，日均销量分母按L1有销售天数。')
        for ref in kept:
            sql = ref['sql']
            if qid == 'Q34':
                sql = sql.replace('FROM retail.FactOnlineSales', 'FROM retail.FactSales')
            if qid == 'Q65':
                sql = sql.replace('SELECT StoreManager,StoreName,', 'SELECT s.EmployeeKey AS manager_key,StoreName,').replace('GROUP BY StoreManager,StoreName','GROUP BY s.EmployeeKey,StoreName').replace('toInt32OrNull(s.StoreManager)=e.EmployeeKey','s.manager_key=e.EmployeeKey')
            if qid == 'Q87':
                sql = sql.replace('SUM(SalesQuantity) / 90.0 AS avg_daily_qty','SUM(SalesQuantity) / countDistinct(DateKey) AS avg_daily_qty')
            if qid == 'Q86':
                sql = sql.replace('p.DiscountPercent IS NOT NULL','p.DiscountPercent IS NOT NULL AND p.PromotionKey <> 1')
            if qid in {'Q27','Q45','Q79','Q85','Q87'}:
                aliases = {'Q27':{'margin_pct'},'Q45':{'sales_per_sqft'},'Q79':{'attainment_pct'},'Q85':{'attainment_pct'},'Q87':{'days_of_coverage','avg_daily_qty'}}[qid]
                for start,end,expression,name in reversed(list(round_projections(sql))):
                    if name in aliases:
                        sql = sql[:start]+'('+expression+')'+sql[end:]
            ref['sql'] = sql
        if qid in TEXT:
            question['text_zh'], english, reason = TEXT[qid]
            if question['source']=='new':
                question['text_en']=english
        elif qid == 'Q114':
            reason = '用户明确要求题面不改；保留截止日及90日首购措辞，参考仅[T-89,T]全部行'
        else:
            reason = '仅指标名／题目参数／输出标签，无内嵌已定义业务公式；保留'
        text_audit.append({'question_id':qid,'changed':question['text_zh']!=old['text_zh'] or question['text_en']!=old['text_en'],
                           'old_text_zh':old['text_zh'],'new_text_zh':question['text_zh'],'old_text_en':old['text_en'],'new_text_en':question['text_en'],'reason':reason})
        for ref in old['refs'][1:]:
            path = ref['result_path']
            if path in {'refs/cube/Q65-2.csv','refs/cube/Q49-2.csv'}:
                kind, rationale = '展示方式','保留该完整／姓名展示，删除原第一份；该题仍仅一份'
            elif path in empty_paths or '购买事件=SalesQuantity>0' in ref['interpretation'] or path in fixed or path=='refs/cube/Q20-2.csv':
                kind, rationale = '口径歧义','遵守已定义L1／本轮裁决，只保留规范参考'
            else:
                kind, rationale = '问法歧义','问法未指定分析维度／范围／方法，不以额外业务定义伪造多解；未定默认另列缺口'
            extras.append({'question_id':qid,'reference':path,'interpretation':ref['interpretation'],'category':kind,'retained':path in {r['result_path'] for r in kept},'reason':rationale})
    assert len(extras)==43 and len(removed)==32
    for path,document in zip(paths,documents,strict=True):
        path.write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n')
    for ref in removed:
        (ROOT/ref['reference']).unlink()
    main = Path(os.environ['SEMDEBT_MAIN_DIR'])
    result = {'decision':'user 2026-10-17; supersedes prior business-policy alternatives','baseline_questions':122,'baseline_references':165,'final_references':sum(len(q['refs']) for q in questions),
              'source_sha256':{name:hashlib.sha256((main/'semantic'/name).read_bytes()).hexdigest() for name in ('conventions.md','source.yaml')},
              'removed_references':removed,'extra_reference_inventory':extras,'question_text_review':text_audit,
              'precision_questions':['Q27','Q45','Q79','Q85','Q87'],'Q79_release':'recompute current members and bind updated reference hashes; do not hardcode count'}
    AUDIT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'extra_references_reviewed':len(extras),'removed':len(removed),'final_references':result['final_references'],'changed_texts':[r['question_id'] for r in text_audit if r['changed']]},ensure_ascii=False))


if __name__=='__main__':main()
