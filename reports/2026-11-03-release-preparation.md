# 题库发布准备复查（2026-11-03）

基点：`d91d66963f0f08ae523bf171deaa278fe60ab576`（最新 main，含 PR #25 的三份 L1+ 复核记录）。本次只准备 PR，不改仓库可见性、不改写历史、不移动标签；模型 API 调用 **0**。

## 许可与当前文件

- 根 `LICENSE` 与主仓库 `LICENSE` 逐字节一致，为 MIT 全文，版权人保留 Yu HUANG。
- 新增 `LICENSE-CONTENT.md`，承接原根许可的范围说明，与主仓库采用相同的代码 MIT / 原创内容 CC BY 4.0 分层方式，按题库实际内容说明新题、中文化与改写、参考答案和文档的原创贡献。题库与主仓库目录不同，内容范围说明没有照抄主仓库目录表。
- Cube 改写内容保留来源要求；`vendor/cube/NOTICE.md`、上游材料和底层数据的权利边界沿用原说明。既有 `LICENSES/` 全文不变。
- `README.md` 的范围说明链接改指 `LICENSE-CONTENT.md`。
- 以下当前文件各替换一处真实本机主目录前缀为 `<home>`，其余字节不变：`audit/rules-impact.json`、`audit/rules-final-impact.json`、`audit/orphan-group-impact.json`。

上述三个文件在 10 月 31 日准备中曾因存在哈希引用而保留路径；此次按用户明确要求清理当前版本。旧报告及哈希声明仍指向当时的历史字节，不作为本次脱敏文件的哈希；可从对应历史提交恢复核验。没有改写旧报告、原始结果、其他哈希字段或 Git 历史。

## Gitleaks：全部分支

使用已安装的 Gitleaks **8.30.1**，没有新增忽略项或自定义放行规则。fetch refspec 为 `+refs/heads/*:refs/remotes/origin/*`；成功获取全部远端 heads 后，与 GitHub 分支列表核对，25 个分支（不计 origin/HEAD）。本地不是只扫描 main，`--all` 纳入本地分支、远端跟踪分支和标签的可达历史。

实际执行用户指定的命令：

```sh
gitleaks detect --source . --log-opts="--all" --redact
```

另以相同范围加 `--report-format json --report-path <临时文件>` 保存脱敏机器结果，结果为 `[]`。两次均退出 0：**77 commits scanned，约 230.89 MB，no leaks found**。Git 可达提交总数为 103；77 是 Gitleaks 自身报告的差异扫描计数，不将其误称为 Git 提交总数。

逐条判定：**0 条候选，0 条真阳性，0 条误报**，没有待判定项。报告不收录密钥值，也没有测试凭据有效性。零命中只说明本次工具和规则未检出密钥。

明确覆盖：

- `origin/scorer-v2-check`：`f7000ae7bfbb356964c33c477b63d26678bd2dfa`。
- `origin/codex/l1plus-review-records`：`fff57e6c50e606901600485450045494d99716a2`，已被 main 包含。
- 三份新增复核文件：`audit/2026-10-24-l1plus-92b7723-review.md`、`audit/2026-10-24-l1plus-b97cf93-review.md`、`audit/2026-10-24-l1plus-d398d76-review.md`。

## 个人信息复查

对 `git rev-list --objects --all` 枚举的 **2,521 个唯一文件对象**与当前跟踪文件检查主目录路径、邮箱、带 phone/mobile/telephone/电话/手机字段上下文的号码，以及 RFC 1918 内网 IPv4；另检查 `git log --all` 的作者、提交者及提交信息。只输出位置与类别，不输出具体值。main 与 scorer-v2-check 文件树未发现常见 `.env`、私钥或 credentials 文件名。

| 类别 | 判定与处置 |
|---|---|
| 当前本机主目录路径 | 三个残留处已改为 `<home>`；复扫无真实用户名路径命中。通用 `~/...` 示例及检测表达式不是本机身份值。 |
| 历史及其他分支中的本机路径 | 真实身份暴露面，位置如下表；按“只改当前文件，不改历史”保留。`scorer-v2-check` 中也保留有旧报告和脚本路径，扫描已覆盖，不等于已替其他分支脱敏。 |
| 四份上游 q08 结果中的邮箱形式值 | 确认为第三方结果字段，当前仍存在；不是凭据误报，不推断为真实联系人或合成值。保留上游原始材料和来源声明。 |
| Git 元数据与提交信息 | 作者/提交者共 2 个邮箱身份（其中 1 个为 noreply）；含提交信息共检出 3 个不同邮箱形式值。真实身份或归属信息暴露面，保留历史，不输出值。 |
| 电话、内网 IP | 上述检测规则 0 候选；不能据此断言无任意形式个人信息。 |
| 姓名、性别、职业及客户/员工标识 | 参考结果和业务审计含这些属性，属于发布内容中的个人属性暴露面。10 月 31 日来源核验见既有发布准备报告，本次未重新执行源数据比对；不能将其推断为现实个人或保证匿名。 |
| 新合并的 L1+ 复核记录 | 逐份检查：业务对象与题号层面的复核叙述，未出现上述邮箱、真实主目录、电话或内网 IP 候选。 |

### 全分支历史中的主目录路径位置

以下为路径级去重清单，含已在 main 历史中脱敏的文件及仅其他分支存在的文件；不收录用户名。

- `audit/T05-final-validation.json`
- `audit/T05-inner-left.json`
- `audit/T05-purchase-events.json`
- `audit/orphan-group-impact.json`
- `audit/reviews/2026-10-16-orphan-group-impact-pure.json`
- `audit/rules-final-impact.json`
- `audit/rules-impact.json`
- `audit/rules-order-final-impact.json`
- `reports/T05b/compare-56ade6c.json`
- `reports/T05b/compare-6234d29.json`
- `reports/T05b/compare-926acdf.json`
- `reports/T05b/compare.json`
- `reports/T05b/pandas-56ade6c/manifest.json`
- `reports/T05b/pandas-v11/manifest.json`
- `reports/T05b/pandas/manifest.json`
- `scripts/recheck_pandas.py`

### 当前仍含邮箱形式字段的上游文件

- `vendor/cube/published-runs/paper-2026-04-22/claude_claude_opus_4_7_semantic/q08.json`
- `vendor/cube/published-runs/paper-2026-04-22/claude_claude_sonnet_4_6_semantic/q08.json`
- `vendor/cube/published-runs/paper-2026-04-22/codex_gpt_5_4_raw/q08.json`
- `vendor/cube/published-runs/paper-2026-04-22/codex_gpt_5_4_semantic/q08.json`

个人信息检查是候选发现与来源分类，不是匿名化保证。历史路径、作者身份以及上游邮箱/业务个人属性仍是公开时会暴露的内容；本 PR 没有将其描述为“已全部清除”。

## 验证与变更范围

- 三个 JSON 均可解析，断言相对 main 仅主目录前缀替换。
- 根 MIT 全文与主仓库逐字节一致；与既有 `LICENSES/MIT.txt` 仅换行差异，按空白分词内容一致。
- `questions/`、`refs/`（含标签与清单）、`vendor/cube/` 相对基点逐字节不变；Git 标签不变。
- `git diff --check` 通过。不运行实验、不打开 chDB、不调用模型 API，不新增依赖。
- 修改文件：`LICENSE`、`README.md`、上述三个审计 JSON；新增 `LICENSE-CONTENT.md`、本报告。

## 扫描时的远端分支快照

| 分支 | 提交 |
|---|---|
| `origin` | `d91d66963f0f08ae523bf171deaa278fe60ab576` |
| `origin/T01a-work` | `ba9ede5c94acf2c001a00980cad91d79ee5443b7` |
| `origin/T02-quantized-tie-handoff` | `f6d554818fda2a393a986ea2d998183e0c4053d0` |
| `origin/T02-scorer-handoff` | `ab28df9edf3f0362f97be847a8a135c1d6c12962` |
| `origin/T03-work` | `3cc4f8b2da4f13545fee38ee9d93f5db291075ea` |
| `origin/T04-work` | `c7410379631511e2160aa7f6378130c74753cece` |
| `origin/T05-explicit-value-kinds` | `80e4ac8a3a1cd778532488fd054af3444f3a6148` |
| `origin/T05-work` | `2c44bb98de353da52ab220a196931546e0089655` |
| `origin/T06-split-freeze` | `9d86778f6eed2395ca4662a03347597c44106faa` |
| `origin/T29-b1` | `50098ef5380fc913692a95d143b9bdce3baca3ad` |
| `origin/codex/chdb-session-q79` | `97f32fc62ad37d8de5b8fd3917fe2bd218687e7f` |
| `origin/codex/eval-v1-1-presentation` | `926acdffcc32523a3f92569f02f1fa489397607d` |
| `origin/codex/eval-v1.3-reference-rulings` | `5b65e0c450ba36d83707c00dc9443be16b08d086` |
| `origin/codex/l1plus-review-records` | `fff57e6c50e606901600485450045494d99716a2` |
| `origin/codex/new-questions-and-order-keys` | `19aafa4f01fe25d02c0894e68b9ca4817d4a719d` |
| `origin/codex/open-source-audit-20261031` | `a5e50211297a96e6ee3a46a653c773fe85d5f865` |
| `origin/codex/public-licenses-20261031` | `2395d2295d0dbc0ab72430e56639844faea87cea` |
| `origin/codex/q79-orphan-references` | `b41b111172b26be152c56413e8e64eaef93d8487` |
| `origin/codex/rules-backfill` | `6979a6efbf7fd4684e22856e504b45e9d7597b87` |
| `origin/codex/selection-audit-ext600` | `4b6c098e8886e437ea031961c2b0b70ef517f421` |
| `origin/codex/t05-finalize` | `2adf976584dfc127e6c28e57325dd3ff07f624e8` |
| `origin/codex/t05b-reference-corrections` | `4acbf94ae663db55b82784d6da95de4e6bff6366` |
| `origin/codex/t05b-reference-values-labels` | `d2d157af586163217cd7baa518f363c9b9469835` |
| `origin/codex/t12-reference-fixes` | `56ade6cd4d78c722a0e3861072ceece0779fcdc0` |
| `origin/main` | `d91d66963f0f08ae523bf171deaa278fe60ab576` |
| `origin/scorer-v2-check` | `f7000ae7bfbb356964c33c477b63d26678bd2dfa` |
