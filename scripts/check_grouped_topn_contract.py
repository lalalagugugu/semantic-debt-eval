#!/usr/bin/env python
"""Expose the existing global Top-N contract's lack of group coverage rules.

Read-only synthetic diagnostic, not a replacement scorer or a proposed fix.
No question data, database, model or network is used.
"""
import os
import csv
from collections import defaultdict
from decimal import Decimal
import math
from pathlib import Path
import sys


def main():
    main_dir = os.environ.get('SEMDEBT_MAIN_DIR')
    if not main_dir:
        raise SystemExit('SEMDEBT_MAIN_DIR must be set')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(main_dir)))
    from harness.scorer import score_detailed

    # Each store has two equal local winners. Exactly one per store is needed.
    complete_boundary = [
        ['store_A', 'product_A1', 100.0],
        ['store_A', 'product_A2', 100.0],
        ['store_B', 'product_B1', 100.0],
        ['store_B', 'product_B2', 100.0],
    ]
    valid = [complete_boundary[0], complete_boundary[2]]
    missing_group = [complete_boundary[0], complete_boundary[1]]
    metadata = {
        'value_kinds': ['other', 'other', 'amount'],
        'value_types': ['String', 'String', 'Float64'],
    }
    unordered = dict(metadata, ordered=False, top_n=None, tie_columns=[])
    global_top = dict(metadata, ordered=True, top_n=2, tie_columns=[2])
    full_set_result = score_detailed(valid, [complete_boundary], unordered)
    global_valid = score_detailed(valid, [complete_boundary], global_top)
    global_missing = score_detailed(missing_group, [complete_boundary], global_top)
    print('Complete unordered reference / valid one-per-store candidate:', full_set_result)
    print('Global top_n=2 / valid one-per-store candidate:', global_valid)
    print('Global top_n=2 / missing store_B candidate:', global_missing)
    assert full_set_result.outcome == 'wrong' and full_set_result.reason == 'row_count'
    assert global_valid.outcome == 'correct'
    assert global_missing.outcome == 'correct'
    print('REPRODUCED: existing global Top-N accepts the wrong group allocation.')
    from harness.value_units import quantize_tie
    groups = defaultdict(list)
    path = Path(__file__).resolve().parent.parent / 'refs/cube/Q74-1.csv'
    with path.open(newline='') as stream:
        for row in csv.DictReader(stream):
            groups[row['StoreName']].append(quantize_tie(Decimal(row['product_sales']), 'amount'))
    winners = [sum(value == max(values) for value in values) for values in groups.values()]
    print('Existing 2009 store/product reference:', {
        'store_groups': len(groups),
        'groups_with_top1_ties': sum(count > 1 for count in winners),
        'max_tied_winners': max(winners),
        'one_winner_result_combinations': math.prod(winners),
    })


if __name__ == '__main__':
    main()
