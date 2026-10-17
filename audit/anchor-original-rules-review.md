# 英文原始参考rules交接：不含接线变更

T11的主仓库报告已交Codex补EN13、14、20、74、83、87；本轮保留事实ProductKey后另有EN21、EN34。此次Q66删除未问的第三列后，补EN66原始三列规则。下面9份rules对应外部原始SQL及T11已实际执行保存的列meta，不覆盖中文修订参考、不修改harness接线。T11应按vendor_id及SQL哈希选择整份rules；勿将下表塞进中文refs作为额外可接受解读。

量纲策略SHA256：`7413327151dc85b9ff08233a191ce238dfe6722058b0c1fa71c0649facc540db`。自动推断沿用固定reference_value_kinds及infer_value_kind，不能按列值猜量纲。原始返回类型逐字保留Nullable，比较结构时按裁决剥Nullable；count整数守卫由底层类型判断。

全部99道英文原始参考仍由T11维护。这里仅核对已存在原始payload的SQL/文件哈希、真实列类型和9份规则自比，不宣称重新执行99份SQL。T05b仍须独立核验。

| 原题／锚点 | 原始行数 | 类型及量纲 |
|---|---:|---|
| Q13／EN13 | 306 | StoreName: String / other；total_sales: Float64 / amount；avg_order_value: Float64 / other；num_transactions: UInt64 / count |
| Q14／EN14 | 18869 | FirstName: String / other；LastName: String / other；total_spent: Float64 / amount |
| Q20／EN20 | 3969 | ProductName: String / other；OnHandQuantity: Int32 / other；SafetyStockQuantity: Int32 / other |
| Q21／EN21 | 561293 | StoreName: String / other；ProductName: String / other；OnHandQuantity: Int32 / other |
| Q34／EN34 | 2220 | ProductName: String / other；total_cogs: Float64 / amount；avg_inventory: Float64 / other；turnover_ratio: Nullable(Float64) / ratio |
| Q66／EN66 | 4 | quarter: UInt8 / other；total_discount: Float64 / amount；discounted_orders: UInt64 / count |
| Q74／EN74 | 9 | StoreName: String / other；ProductName: String / other；product_sales: Float64 / amount；pct_of_store: Nullable(Float64) / percentage |
| Q83／EN83 | 1 | cohort_size_2007: Nullable(UInt64) / count；returned_2008: UInt64 / count；retention_2008_pct: Nullable(Float64) / percentage；returned_2008_and_2009: UInt64 / count；retention_2009_pct: Nullable(Float64) / percentage |
| Q87／EN87 | 20 | ProductName: String / other；on_hand: Int64 / other；avg_daily_qty: Float64 / other；days_of_coverage: Float64 / other |

## EN13

原始SQL SHA256：`5adf128792e63087c516cb8548afce747d55a2424d6e95515519e29ee3a57224`；payload SHA256：`b5ca247b9896ee47a7eca5b6965cb545fbb77fc97646d040f7df7aaacd6c444e`。

```json
{
  "ordered": false,
  "top_n": null,
  "tie_columns": [],
  "value_kinds": [
    "other",
    "amount",
    "other",
    "count"
  ],
  "value_types": [
    "String",
    "Float64",
    "Float64",
    "UInt64"
  ]
}
```

## EN14

原始SQL SHA256：`7f57be7ba98a21b56e30a8efdbc380d2cecc86aedd7db2c9b195fe12df42c853`；payload SHA256：`c7016bb0adbcf74372995a4ff6c8955de95261351dbcfb4acf78622f9150091e`。

```json
{
  "ordered": false,
  "top_n": null,
  "tie_columns": [],
  "value_kinds": [
    "other",
    "other",
    "amount"
  ],
  "value_types": [
    "String",
    "String",
    "Float64"
  ]
}
```

## EN20

原始SQL SHA256：`71a80dbed2892a8a96d0f8d646c19be4170f7dd00ed3ea22ee51eb30895daa8d`；payload SHA256：`cfba475c9e09d14eb01f74b8c8307d5aa39a9adc462b556fa4c601096f939140`。

```json
{
  "ordered": false,
  "top_n": null,
  "tie_columns": [],
  "value_kinds": [
    "other",
    "other",
    "other"
  ],
  "value_types": [
    "String",
    "Int32",
    "Int32"
  ]
}
```

## EN21

原始SQL SHA256：`afa6a35774d75fd5bc43c8b51327d04010f939921d250ddd5750d073f031891d`；payload SHA256：`a4b906791fdd686d2ab8381862b649b477d78c6e2efd6c02ee50b8bf400cbf7c`。

```json
{
  "ordered": false,
  "top_n": null,
  "tie_columns": [],
  "value_kinds": [
    "other",
    "other",
    "other"
  ],
  "value_types": [
    "String",
    "String",
    "Int32"
  ]
}
```

## EN34

原始SQL SHA256：`bd99a1eb861ea1aa7c038145cefcda69018a885d7c60cb65dfa35718506cdc77`；payload SHA256：`5dc99e1e706edfdfae336ed89abb2db432fc8fb0f78f8706422ffeb92b8bb9e8`。

```json
{
  "ordered": false,
  "top_n": null,
  "tie_columns": [],
  "value_kinds": [
    "other",
    "amount",
    "other",
    "ratio"
  ],
  "value_types": [
    "String",
    "Float64",
    "Float64",
    "Nullable(Float64)"
  ]
}
```

## EN66

原始SQL SHA256：`5ad683444c9e6d545b231cebd25b586d610c97cc6aeccf7a5e8b8313f24a7ac5`；payload SHA256：`60de7c85b19ebaf4ef49079f8ba55fdb8f84914120ef1d9773a967d9648e2e88`。

```json
{
  "ordered": false,
  "top_n": null,
  "tie_columns": [],
  "value_kinds": [
    "other",
    "amount",
    "count"
  ],
  "value_types": [
    "UInt8",
    "Float64",
    "UInt64"
  ]
}
```

## EN74

原始SQL SHA256：`55ad2b090492d0b38b7be885c00c18c9eb1af53a874462c74414d83bacbad4b4`；payload SHA256：`9c36fc1816741fa2f20e5b38487e83e17a6a5c9858bc33ab97600bf1d32400c0`。

```json
{
  "ordered": true,
  "top_n": null,
  "tie_columns": [],
  "value_kinds": [
    "other",
    "other",
    "amount",
    "percentage"
  ],
  "value_types": [
    "String",
    "String",
    "Float64",
    "Nullable(Float64)"
  ],
  "selection": {
    "version": 1,
    "stages": [
      {
        "parent": null,
        "where": [],
        "group_columns": [
          0
        ],
        "object_columns": [
          1
        ],
        "order_by": [
          {
            "column": 2,
            "descending": true
          }
        ],
        "n": 3
      }
    ],
    "output_order": [
      {
        "column": 0,
        "descending": false
      },
      {
        "column": 2,
        "descending": true
      }
    ]
  },
  "order_by": [
    {
      "column": 0,
      "descending": false
    },
    {
      "column": 2,
      "descending": true
    }
  ]
}
```

## EN83

原始SQL SHA256：`684280447347b9d99486bfe3b952b0c3a415380d955437dff7627372b4753f88`；payload SHA256：`04d60880011f9815f6cb39c04f2a0e85907fbf07973101144ec5f0dc5f0741e4`。

```json
{
  "ordered": false,
  "top_n": null,
  "tie_columns": [],
  "value_kinds": [
    "count",
    "count",
    "percentage",
    "count",
    "percentage"
  ],
  "value_types": [
    "Nullable(UInt64)",
    "UInt64",
    "Nullable(Float64)",
    "UInt64",
    "Nullable(Float64)"
  ]
}
```

## EN87

原始SQL SHA256：`432b98fe1d530f55b556e79a38b7d47b4a1d34744e8ad4f0a0ba43fe582f89e9`；payload SHA256：`a31983fc183a131d4c84bb27e359e711e1062bea9bb6461a62a8a1557b31bb24`。

```json
{
  "ordered": true,
  "top_n": 20,
  "tie_columns": [
    3
  ],
  "value_kinds": [
    "other",
    "other",
    "other",
    "other"
  ],
  "value_types": [
    "String",
    "Int64",
    "Float64",
    "Float64"
  ],
  "order_by": [
    {
      "column": 3,
      "descending": false
    }
  ]
}
```

EN74的选择元数据仅按原始4列重映射为门店／产品／销售额／占比，保持外部原始渠道、连接与数值，不偷换成中文修订6列参考。T11仍须按既有Top-N完整边界要求核对原始截断是否丢并列；EN87同理。EN97仍为judge且不在确定性结构不同的9份之内；不以补规则扩大确定性题集合。

T11接入这些rules后可评数量预计由当前修订题库的79增为87，另12道judge；此处只是规则交接，是否可评以T11接线后的自比及完整边界检查为准。复现：`uv run python scripts/review_anchor_rules.py --check`。
