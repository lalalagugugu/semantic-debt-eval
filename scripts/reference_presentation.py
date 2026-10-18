"""Declared reference presentation transforms; no question-specific branches."""
from collections import defaultdict
from datetime import date


def apply_presentation(meta, rows, policy, spec):
    meta = [dict(c) for c in meta]
    rows = [list(row) for row in rows]
    grouped_specs = defaultdict(list)
    for rank in spec.get('ranks', []):
        grouped_specs[rank['name']].append(rank)
    for name, variants in grouped_specs.items():
        output = [None] * len(rows)
        for rank in variants:
            groups = defaultdict(dict)
            members = []
            for pos,row in enumerate(rows):
                if not all(row[c['column']] == c['equals'] for c in rank['where']):
                    continue
                group = tuple(row[i] for i in rank['group_columns'])
                obj = tuple(row[i] for i in rank['object_columns'])
                key = tuple(policy.quantize_tie(row[k['column']], policy.infer_value_kind(meta[k['column']]['name'],meta[k['column']]['type'])) for k in rank['order_by'])
                if obj in groups[group] and groups[group][obj] != key:
                    raise ValueError('rank object has inconsistent order keys')
                groups[group][obj] = key
                members.append((pos,group,obj,key))
            def better(left,right):
                for a,b,order in zip(left,right,rank['order_by'],strict=True):
                    if a == b:
                        continue
                    if a is None or b is None:
                        return b is None
                    return a > b if order['descending'] else a < b
                return False
            for pos,group,obj,key in members:
                if output[pos] is not None:
                    raise ValueError('rank variants overlap')
                output[pos] = 1 + sum(better(other,key) for other in groups[group].values())
        if any(value is None for value in output):
            raise ValueError('rank variants must cover every output row')
        existing = next((i for i,c in enumerate(meta) if c['name']==name), None)
        for row,value in zip(rows,output,strict=True):
            if existing is None:row.append(value)
            else:row[existing]=value
        if existing is None:meta.append({'name':name,'type':'UInt64'})
        else:meta[existing]['type']='UInt64'
    for period in spec.get('periods', []):
        i=period['column']
        if period['kind']=='quarter_label':
            for row in rows:
                value=int(row[i]);assert 1<=value<=4
                row[i]=f'Q{value}'
            meta[i]['type']='String'
        elif period['kind']=='calendar_month':
            for row in rows:
                day=date.fromisoformat(str(row[i])[:10]);row[i]=day.month;row.append(day.year)
            meta[i]['type']='UInt8'
            meta.append({'name':period['year_name'],'type':'UInt16'})
        else:
            raise ValueError('unknown period kind')
    return meta,rows


def ranking_domains(meta, rows, spec, *, population_blocks=None):
    """Persist complete tie blocks and object identities for rank comparison."""
    by_name = defaultdict(list)
    for rank in spec.get('ranks', []) + spec.get('existing_ranks', []):
        by_name[rank['name']].append(rank)
    result = []
    for name, variants in by_name.items():
        column = next(i for i,c in enumerate(meta) if c['name']==name)
        first = variants[0]
        if any(v['group_columns'] != first['group_columns'] or v['object_columns'] != first['object_columns'] for v in variants):
            raise ValueError('rank variants must share identity columns')
        groups = defaultdict(lambda:defaultdict(set))
        for row in rows:
            group = tuple(row[i] for i in first['group_columns'])
            obj = tuple(row[i] for i in first['object_columns'])
            groups[group][int(row[column])].add(obj)
        blocks = []
        for group, ranks in sorted(groups.items(),key=lambda pair:repr(pair[0])):
            for dense,(rank,objects) in enumerate(sorted(ranks.items()),1):
                blocks.append({'group':list(group),'rank':rank,'dense':dense,'size':len(objects)})
        if first.get('population'):
            if population_blocks is None:
                raise ValueError('complete ranking population missing')
            blocks = population_blocks
        result.append({'column':column,'group_columns':first['group_columns'],
                       'object_columns':first['object_columns'],
                       'prefix':not first.get('population',False),'blocks':blocks})
    return result
