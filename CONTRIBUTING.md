# 贡献 / Contributing

欢迎改进正文提取、通用服务适配器、模板、恢复逻辑与中英文文档。 / Improvements to extraction, generic adapters, templates, recovery, and bilingual documentation are welcome.

1. 保持发现、抓取、富化与输出契约清晰。 / Keep discovery, fetching, enrichment, and export contracts explicit.
2. 使用虚构或可以再使用的素材；不要提交密钥、私有接口地址、来源清单、真实运行记录或业务数据。 / Use fictional or reusable material; never commit credentials, private endpoints/registries, real runtime records, or business data.
3. 服务适配器应提供本机模拟测试，检查响应映射、失败和预算，不依赖真实付费 API。 / Adapters need local mock tests for mapping, failures, and limits, without real paid APIs.
4. 影响用户配置的变化同步更新中英文指南。 / Update both language guides when changing user configuration.

```bash
python3 -m unittest discover -s tests -v
python3 -m gkp validate examples/demo.json
python3 -m gkp run examples/demo.json --workspace runtime/contribution-demo
```

项目采用 [Apache-2.0](LICENSE)。提交贡献时请确认你有权提供相关代码和素材，并保留适用声明。 / The project uses Apache-2.0. Ensure you have the right to contribute code and material, and preserve applicable notices.
