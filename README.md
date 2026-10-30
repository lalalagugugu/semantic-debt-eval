# semantic-debt-eval

`semantic-debt` 的独立题库仓库：题目、参考答案、审计记录和完整设计文档。按项目发布决定，题库单独公开并保留提交历史。它和主仓库是并列的两个仓库，不是子模块。

外部基准的题目与参考 SQL 来自 cubedevinc/semantic-layer-benchmark，在 `vendor/cube/` 保存。上游固定提交的 README 声明 MIT，但没有独立 LICENSE 文件；原有来源及许可声明见 [NOTICE](vendor/cube/NOTICE.md)。本项目不改写该声明。

## 许可

版权人：Yu HUANG。许可范围见 [LICENSE](LICENSE)：

- 本项目代码采用 [MIT](LICENSES/MIT.txt)。
- 本项目新增题、对 Cube 题目的中文化与改写、参考答案及文档中的原创贡献采用 [CC BY 4.0](LICENSES/CC-BY-4.0.txt)，保留上游内容的原有声明。
- `vendor/cube/` 的第三方原始内容及底层 Contoso 数据不由上述本项目许可重新授权。

当前文件中的路径脱敏不改写历史；被文件哈希引用的文件保持原样。跳过清单及个人属性数据核查结论见 [发布准备核查](reports/2026-10-31-public-release-preparation.md)。
