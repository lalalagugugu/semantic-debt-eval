# 题库公开发布准备核查（2026-10-31）

基点：`2157d39a0fe9ac983300bca27ebebfa2e6801fe9`。用户决定：题库单独公开、保留 Git 历史。本 PR 不执行仓库可见性变更，不改写历史。

## 许可

- 本项目代码：MIT，版权人 Yu HUANG；范围见根 `LICENSE`，全文见 `LICENSES/MIT.txt`。参考答案 SQL 按内容许可处理。
- 本项目新增题、Cube 题目的中文化与改写、参考答案、文档中的原创贡献：CC BY 4.0；全文见 `LICENSES/CC-BY-4.0.txt`。
- 第三方原始内容及源数据保留原有来源和适用条款；本项目不将底层数据或上游原作重新授权。
- `vendor/cube/NOTICE.md` 完全未改；根 `LICENSE` 和 `README.md` 明确上游固定提交 README 声明 MIT，但没有独立 LICENSE 文件。
- 许可文本依据 [OSI 的 MIT 文本](https://opensource.org/license/mit) 与 [Creative Commons 官方 CC BY 4.0 全文](https://creativecommons.org/licenses/by/4.0/legalcode.txt)。CC 全文保留官方文本，仅去除文件末尾多余空白行。

## 当前路径脱敏

仅替换真实绝对路径中的用户主目录前缀为 `<home>`，保留其后路径及其他 JSON 内容，未重排或重新序列化文件。下列五个文件未发现文件内容哈希引用（包括其可恢复的旧版本），已脱敏：

- `audit/T05-final-validation.json`
- `audit/T05-inner-left.json`
- `audit/T05-purchase-events.json`
- `audit/reviews/2026-10-16-orphan-group-impact-pure.json`
- `audit/rules-order-final-impact.json`

以下三个文件因存在哈希引用，保留原字节及路径，未脱敏：

| 保留文件 | 哈希引用位置 |
|---|---|
| `audit/orphan-group-impact.json` | `main:reports/validation/scorer_early_reject_diagnostics.json`；`main:reports/validation/scorer_ordered_ties_600.json` |
| `audit/rules-final-impact.json` | `eval:audit/orphan-group-impact.json`；`eval:audit/reviews/2026-10-16-orphan-group-impact-pure.json`；`eval:audit/rules-order-final-impact.json`；`main:reports/validation/rules_backfill_check.md` |
| `audit/rules-impact.json` | `eval:audit/reviews/2026-10-17-workspace-cleanup.json`；`eval:audit/rules-rebase-comparison.json` |

`eval:`、`main:` 分别表示题库和主仓库中的相对文件名；引用位置包含历史版本。按两库本地引用及 reflog 中文件文本的完整 SHA-256、SHA-1、MD5 与 Git blob ID 查找引用，并对路径命中文件补查各历史版本。Git 提交号对整棵树的绑定未等同为每个文件的独立内容哈希引用；否则任何已提交文件都无法修改。未声称覆盖无法从本地恢复的服务端历史或仓库外清单。

`reports/2026-10-31-open-source-audit.md` 中 `/Users/`、`/home/` 的命中是检测正则代码，不是实际用户名路径；未修改。`~/...` 示例、环境变量路径及临时目录也不作为含用户名的真实主目录路径替换。

`.gitignore` 已新增 `.DS_Store`；未删除已有文件或改写 Git 历史。原工作区已有未跟踪文件未加入 PR。

## refs/ 与 audit/ 个人属性来源结论

结论：当前结构化结果中检查到的非空姓名、性别、职业等个人属性取值均能匹配本地 Contoso 数据；姓名组合可由源数据同一行的名字、姓氏组成。员工、客户标识及经理别名字段也作了补充核对，数字格式差异按数值比较，未发现来源不明的非空取值。没有输出任何取值。

以下是实际命中并完成比对的文件；说明文字、列名声明、作者身份和指标名称不冒充业务数据值参与比对。

| 文件 | 结论 |
|---|---|
| `refs/cube/Q08-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q100-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q19-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q22-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q35-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q63-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q65-2.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q65-3.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q75-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q82-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q82-2.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/cube/Q88-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/new/Q112-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `refs/new/Q120-1.csv` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `audit/T05-reference-data-quality.json` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `audit/T29-b1-results/Q100-b1-1.json` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `audit/T29-b1-results/Q100-existing-1.json` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `audit/T29-b1-results/Q35-b1-1.json` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `audit/T29-b1-results/Q65-b1-1.json` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `audit/T29-b1-results/Q82-b1-1.json` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `audit/T29-b1-results/Q82-b1-2.json` | 非空取值匹配 Contoso；空值不视为个人属性值 |
| `audit/T29-b1-results/Q82-b1-3.json` | 非空取值匹配 Contoso；空值不视为个人属性值 |

`refs/cube/Q65-2.csv`、`refs/cube/Q65-3.csv` 中曾被初检标为未匹配的项是 ClickHouse 空值序列化，不是姓名取值。数值序列化差异经数值比较匹配，不是新增身份。

核查读取 Parquet，没有打开 `chdb` 或 `chdb-eval`，未执行参考 SQL或付费调用。相关源维度 Parquet 字段域及姓名配对与原始 CSV 一致，CSV 字节与下载归档中的同名文件一致；下载归档 SHA-256 与主仓库既有来源记录一致。核对的源文件：

- `DimCustomer.csv`
- `DimEmployee.csv`
- `DimEntity.csv`
- `DimSalesTerritory.csv`
- `DimStore.csv`

标识字段另与 `FactOnlineSales.parquet` 中的源标识取值域比对。上述结论针对当前结构化 CSV/JSON 结果，不将自由文本、历史版本或模型说明文字纳入“所有取值匹配”的断言。它证明所查取值可追溯到项目记录的 Contoso 输入，不推断这些数据是否对应现实个人。

## 变更与验证

- 新增：`LICENSE`、`LICENSES/MIT.txt`、`LICENSES/CC-BY-4.0.txt`、本报告。
- 修改：`README.md`、`.gitignore` 及前述五个审计 JSON。
- `questions/`、`refs/`、全部识别出的被哈希引用文件、`vendor/cube/` 均逐字节保留。
- 验证：保护文件与基点字节对比、五个 JSON 仅主目录前缀替换断言、JSON 解析、路径复扫、`.DS_Store` 忽略规则、许可全文对比（忽略末尾空白行）与 `git diff --check`。未修改运行行为，不运行全量实验。
