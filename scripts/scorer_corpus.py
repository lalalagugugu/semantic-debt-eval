"""Lossless JSONL cell codec and streaming reader for scorer corpora."""
import datetime as dt
from decimal import Decimal
import json
import math


def encode(value):
    if isinstance(value, dt.datetime):
        return {'$datetime': value.isoformat()}
    if isinstance(value, dt.date):
        return {'$date': value.isoformat()}
    if isinstance(value, Decimal):
        return {'$decimal': str(value)}
    if isinstance(value, float) and not math.isfinite(value):
        return {'$float': 'nan' if math.isnan(value) else ('inf' if value > 0 else '-inf')}
    if isinstance(value, list):
        return [encode(item) for item in value]
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    return value


def decode(value):
    tags = {'$date': dt.date.fromisoformat, '$datetime': dt.datetime.fromisoformat,
            '$decimal': Decimal, '$float': lambda x: {'nan': float('nan'), 'inf': float('inf'), '-inf': -float('inf')}[x]}
    if len(value) == 1:
        key = next(iter(value))
        if key in tags:
            return tags[key](value[key])
    return value


def reject_constant(value):
    raise ValueError(f'Non-JSON numeric literal: {value}')


def read_corpus(path):
    """Yield decoded cases, preserving dates, datetimes, decimals and nonfinite floats."""
    with open(path, encoding='utf-8') as stream:
        for line in stream:
            yield json.loads(line, object_hook=decode, parse_constant=reject_constant)


def read_reference(path, types):
    import csv
    with open(path, newline='', encoding='utf-8') as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if len(header) != len(types):
            raise ValueError(f'Reference width differs: {path}')
        rows = []
        for cells in reader:
            if len(cells) != len(types):
                raise ValueError(f'Row width differs: {path}')
            row = []
            for cell, kind in zip(cells, types, strict=True):
                base = kind.removeprefix('Nullable(').removesuffix(')')
                if cell == '\\N':
                    value = None
                elif base.startswith(('UInt', 'Int')):
                    value = int(cell)
                elif base.startswith('Float'):
                    value = float(cell)
                elif base.startswith('Decimal'):
                    value = Decimal(cell)
                elif base == 'Date':
                    value = dt.date.fromisoformat(cell)
                elif base.startswith('DateTime'):
                    value = dt.datetime.fromisoformat(cell)
                elif base == 'String':
                    value = cell
                else:
                    raise ValueError(f'Unsupported reference type: {kind}')
                row.append(value)
            rows.append(row)
        return rows
