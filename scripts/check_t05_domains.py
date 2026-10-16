#!/usr/bin/env python
"""Serial SQL fixtures for the approved second-round temporal/statistic domains."""
import csv
import json
import math
import os
from pathlib import Path

from chdb import session
from check_purchase_event_impact import positive_sql

REPO = Path(__file__).resolve().parent.parent


def main():
    db = Path(os.environ['SEMDEBT_DATA_DIR']) / 'chdb-eval'
    if not db.is_dir():
        raise SystemExit('chdb-eval must exist')
    questions = json.loads((REPO / 'questions/new.yaml').read_text())['questions']
    by_id = {q['id']: q for q in questions}
    sess = session.Session(str(db))
    try:
        sess.query('SET max_threads=1')
        sess.query('SET max_execution_time=0')
        sql = by_id['Q122']['refs'][0]['sql']
        fixture = "WITH baskets AS (SELECT 'a' AS SalesOrderNumber,[1,2] AS products UNION ALL SELECT 'b',[1] UNION ALL SELECT 'c',[2,3] UNION ALL SELECT 'd',CAST([],'Array(Int32)'))" + sql[sql.index(',\nfirst_product'):]
        rows = json.loads(str(sess.query(fixture,'JSONCompact')))['data']
        pairs = {(r[0],r[1]):r[2:] for r in rows}
        assert pairs == {(1,2):[0.25,0.5,0.5,1.0],(1,3):[0,0,0,0],(2,3):[0.25,0.5,1.0,2.0]}, pairs
        print('PASS: support/all-order denominator, directional confidence, lift and zero pairs')
        online = "values('SalesOrderNumber String,ProductKey Int32,SalesQuantity Int32,DateKey Date',('a',1,1,'2009-01-01'),('a',2,0,'2009-01-01'),('b',1,1,'2009-01-01'),('c',2,1,'2009-01-01'),('c',3,1,'2009-01-01'),('d',4,0,'2009-01-01'))"
        product = "values('ProductKey Int32,BrandName String',(1,'Contoso'),(2,'Contoso'),(3,'Contoso'),(4,'Contoso'))"
        results = []
        for candidate in [sql, positive_sql('Q122',{'sql':sql})]:
            fixture=candidate.replace('retail.FactOnlineSales',online).replace('retail.DimProduct',product)
            results.append({(r[0],r[1]):r[2:] for r in json.loads(str(sess.query(fixture,'JSONCompact')))['data']})
        assert len(results[0])==6 and results[0][(1,2)]==[0.25,0.5,0.5,1.0]
        assert results[1]=={(1,2):[0,0,0,0],(1,3):[0,0,0,0],(2,3):[0.25,1.0,1.0,4.0]}, results
        print('PASS: both purchase definitions; return-only products excluded only from positive baskets; all four orders retained')

        for ref in by_id['Q121']['refs']:
            sql = ref['sql']
            fixture = "WITH monthly AS (SELECT toInt32(1) AS category_key,CAST('a','Nullable(String)') AS category,toUInt8(1) AS m,toFloat64(12) AS sales_amount UNION ALL SELECT 2,'zero',1,0),\n"+sql[sql.index('categories AS'):]
            rows = {r[0]:r[1:] for r in json.loads(str(sess.query(fixture,'JSONCompact')))['data']}
            expected = math.sqrt(11) if 'stddevPop' in sql else math.sqrt(12)
            assert rows['a'][0] == 1 and math.isclose(rows['a'][1],expected,rel_tol=1e-12)
            assert rows['zero'] == [0,None], rows
        print('PASS: twelve-month zero padding; population/sample CV; zero mean NULL')
        sql = by_id['Q113']['refs'][0]['sql']
        fixture = "WITH monthly AS (SELECT 1 AS StoreKey,'s1' AS StoreName,toUInt8(arrayJoin([1,2,3,5,6,7,8,10,12])) AS m,0 AS sales_amount,1 AS quota_amount),\n"+sql[sql.index('under AS'):]
        rows = json.loads(str(sess.query(fixture,'JSONCompact')))['data']
        assert {tuple(r) for r in rows} == {('s1',1,3,3),('s1',5,8,4)}, rows
        print('PASS: maximal consecutive intervals; isolated/non-adjacent months excluded')
        print('2009 nonpositive sales-quantity lines:',str(sess.query('SELECT countIf(SalesQuantity<=0) FROM retail.FactOnlineSales WHERE toYear(DateKey)=2009','CSV')).strip())
    finally:
        sess.close()
    with (REPO / 'refs/new/Q112-1.csv').open() as stream:
        managers = list(csv.DictReader(stream))
    assert any(float(r['EmployeeKey']) == 245 and r['manager'] == '\\N' for r in managers)
    with (REPO / 'refs/new/Q122-1.csv').open() as stream:
        pairs = list(csv.DictReader(stream))
    keys = {int(r[name]) for r in pairs for name in ('product1_key','product2_key')}
    assert len(pairs) == len(keys)*(len(keys)-1)//2
    assert all(int(r['product1_key'])<int(r['product2_key']) for r in pairs)
    assert any(float(r['support_ratio'])==0 for r in pairs)
    print(f'PASS: manager245 retained; {len(keys)} products / {len(pairs)} complete unordered pairs')


if __name__ == '__main__':
    main()
