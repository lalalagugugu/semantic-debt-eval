#!/usr/bin/env python
"""Serial, read-only checks of T05 zero-result domains and basket SQL fixture."""
import json
import os
from pathlib import Path

from chdb import session

REPO = Path(__file__).resolve().parent.parent


def main():
    db = Path(os.environ['SEMDEBT_DATA_DIR']) / 'chdb-eval'
    if not db.is_dir():
        raise SystemExit('chdb-eval must exist')
    questions = json.loads((REPO / 'questions/new.yaml').read_text())['questions']
    basket_sql = next(q for q in questions if q['id'] == 'Q122')['refs'][0]['sql']
    prefix, remaining = basket_sql.split('), marginal AS (', 1)
    fixture = 'WITH baskets AS (SELECT 1 AS order_id,[1,2] AS cats UNION ALL SELECT 2,[1] UNION ALL SELECT 3,[2,3]), marginal AS (' + remaining
    sess = session.Session(str(db))
    try:
        sess.query('SET max_threads=1')
        rows = json.loads(str(sess.query(fixture, 'JSONCompact')))['data']
        assert sorted(row[2] for row in rows) == [0, 1, 1], rows
        assert sorted(row[3] for row in rows) == [2, 3, 3], rows
        assert sorted(row[4] for row in rows) == [0, 1/3, 0.5], rows
        print('PASS: synthetic basket intersection/union/Jaccard fixture')
        print('max categories per order, multi-category orders, orders:')
        print(sess.query(prefix + ') SELECT max(length(cats)),countIf(length(cats)>1),count() FROM baskets', 'CSV'))
        print('lifetime acquisition year, customers:')
        print(sess.query('SELECT toYear(first_date),count() FROM (SELECT CustomerKey,min(DateKey) AS first_date FROM retail.FactOnlineSales GROUP BY CustomerKey) GROUP BY toYear(first_date) ORDER BY toYear(first_date)', 'CSV'))
    finally:
        sess.close()


if __name__ == '__main__':
    main()
