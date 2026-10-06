# Global Knowledge Crawl Pipeline (by GKN)
# GKN全球信息采集程序

这是一个简易但好用的网络信息追踪/爬取程序，既支持爬取给定的网址栏目链接，也支持根据给定的关键词自动进行互联网检索并爬取相应信息，爬取后支持接入额外API对信息写摘要、研判、打标签，检索也支持接入深度搜索类的API。

它适合接入自动化信息追踪流程和机制中，辅助你追踪和收集互联网信息和热点。

如果你并不精通编程，可以直接丢给你的agent，让它帮你部署这个程序，你只需要根据你的agent引导提供网址链接、检索关键词、API密钥等，即可运行。

Global Knowledge Crawl Pipeline is a simple but useful tool for tracking and crawling information on the web. It can crawl the website section or listing URLs you provide, or automatically search the internet using your keywords and collect the information it finds. After collection, you can connect additional APIs to generate summaries, analyze the information, and add tags. Search can also connect to deep-search APIs.

Use it as part of an automated information monitoring workflow to track and collect online information and trending topics.

If you are not familiar with programming, you can give this project to your AI agent and ask it to deploy the program for you. Follow your agent's guidance to provide website URLs, search keywords, API credentials, and other configuration needed to run it.

**把分散的网页、订阅源和关键词搜索，整理成你自己的信息表。** 配置来源、目标字段和服务接口，程序会发现候选、提取正文、合并重复内容，再按字段要求进行 AI 富化，输出带来源和复核状态的 CSV、Excel 或 JSONL。

**Turn scattered websites, feeds, and keyword searches into your own information table.** Configure your sources, desired fields, and service endpoints. The pipeline discovers candidates, extracts article text, merges exact duplicates, enriches records with your chosen AI service, and exports CSV, Excel, or JSONL with provenance and review status.

**选择语言 / Choose your guide:** [完整中文说明](README.zh-CN.md) · [Full English guide](README.en.md)

Python 3.9+ · 离线示例无需依赖或密钥 / Offline demo needs no dependencies or keys · v0.2.0

## 看一遍，再自己跑通 / Watch, then reproduce

![Actual offline case · 2× preview / 实际离线案例，2 倍速](docs/demo.gif)

[完整视频 / Full video](docs/demo.mp4) · [中文案例教程](docs/walkthrough.zh-CN.md) · [English walkthrough](docs/walkthrough.en.md)

从来源与字段到信息表、证据页和结果复用。视频展示真实运行的虚构离线案例：不请求真实搜索或 AI，长导航等待已剪除。 / Follow sources and fields through the table, evidence and saved-result reuse. This is an actual run of fictional offline fixtures, with no real search or AI calls; long navigation waits are removed.

```bash
python3 examples/make_walkthrough.py
# 打开 / Open: runtime/visual-demo/output/walkthrough.html
```

## 新增：更快配置，更容易复核 / New: configure faster, review clearly

- **本地配置器 / Local configuration builder**：在浏览器中选来源、关键词和字段，下载配置与模板。无需先手写 JSON。 / Choose sources, keywords and fields in a browser and download your configuration and schema.
- **同址更新追踪 / Updates at existing URLs**：显式重新检查已保存的网址，只对变化正文重新富化；保存前后文本差异。 / Explicitly revisit saved URLs, enrich changed text, and retain before/after differences.
- **可读的证据页 / Readable evidence report**：打开本地 HTML 查看字段、原文摘录、复核原因和网页变化。 / Open a local HTML report to review fields, excerpts, review reasons and page changes.

```bash
python3 -m gkp configure --output runtime/configure.html
# 在浏览器中打开生成的文件 / Open the generated file in your browser
```

配置器不会调用网络，也不要求输入密钥。生成文件需要你填入实际可用的服务地址、模型，并在运行环境中设置凭据。 / The builder makes no network requests and asks for no keys. Supply working service endpoints and a model, then set credentials in your runtime environment.

[配置器使用说明 / Builder guide](docs/configuration-builder.md) · [三种离线场景 / Three offline scenarios](examples/README.md)

## 从信息到表格 / From information to a table

```mermaid
flowchart LR
    A[网页 / Websites] --> C[候选与去重 / Candidates]
    B[RSS + 关键词 / Keyword search] --> C
    C --> D[正文 / Article text]
    D --> E[字段模板 + AI / Schema + AI]
    E --> F[校验 / Validation]
    F --> G[CSV / Excel / JSONL]
    F --> H[待复核 / Needs review]
```

| 你提供 / You configure | 程序完成 / The pipeline handles |
| --- | --- |
| 网页、RSS、列表页、关键词 / Websites, RSS, listing pages, queries | 发现信息、合并来源、保存增量进度 / Discovery, provenance merging, incremental checkpoints |
| 字段名称、类型、解释、必填项 / Field names, types, instructions, requirements | 按模板富化，校验类型、枚举和证据摘录 / Schema-driven enrichment and validation |
| 搜索与富化接口 / Search and enrichment endpoints | 请求与返回映射，环境变量凭据 / Request/response mapping and environment credentials |
| 条目、请求和 token 预算 / Item, request, and token budgets | 限额暂停，保留已保存的成功结果 / Pause at configured limits and reuse persisted results |

适合行业动态、政策监测、产品更新和公开研究资料的持续收录。字段由你定义，不绑定特定行业或模型供应商。 / Use it for recurring intake of industry developments, policy notices, product updates, and public research. You define the fields; the core does not depend on a particular industry or model vendor.

## 三步试用 / Try it in three steps

在项目目录运行；示例完全离线，不会访问虚构网址。 / Run from the project directory. The demo is fully offline and does not contact its fictional URLs.

```bash
python3 -m gkp validate examples/demo.json
python3 -m gkp run examples/demo.json
python3 -m gkp run examples/demo.json
```

第一次运行的预期结果 / Expected first run:

```text
4 candidates → 3 records + 1 exact-body duplicate
2 validated · 1 needs_review · 0 HTTP requests
```

第二次运行复用已保存的富化结果，模拟 AI 调用次数为 0。示例故意保留一条缺少摘要的记录，让你看到复核队列如何工作。 / The second run reuses persisted enrichment results and makes zero simulated AI calls. One record deliberately lacks a summary so you can inspect the review queue.

打开 `runtime/fictional_updates/output/table.xlsx` 查看表格；`records.jsonl` 保留正文、证据和处理信息，`run-report.json` 解释本次运行结果；`evidence.html` 展示字段与原文摘录，`changes.json` 保存已检测的正文变化。 / Open `runtime/fictional_updates/output/table.xlsx` for the table. `records.jsonl` retains article text, evidence, and processing metadata; `run-report.json` explains the run; `evidence.html` presents fields and excerpts, and `changes.json` retains detected text changes.

## 从演示到实际使用 / Move from demo to your workflow

1. 修改或复制 [字段模板](examples/product-template.json)，也可参考[政策模板](examples/policy-template.json)。 / Adapt the [field template](examples/product-template.json), or start from the [policy template](examples/policy-template.json).
2. 复制 [实际接入配置示例](examples/live.example.json)，替换来源、接口地址和模型名称。 / Copy the [live configuration example](examples/live.example.json) and replace sources, endpoints, and the model name.
3. 在环境变量中设置自己的凭据，先以小预算运行。 / Set your own credentials in environment variables and begin with a small budget.

配置示例中的 `example.*` 地址是占位符，不提供可用服务。 / The `example.*` endpoints are placeholders, not working services.

## 深入使用 / Go further

- [字段与配置 / Templates and configuration](docs/configuration.md)
- [搜索、模型和自定义 API / Service adapters](docs/adapters.md)
- [增量、恢复、输出和限制 / Running and recovering jobs](docs/operations.md)
- [架构与扩展 / Architecture and extension points](docs/architecture.md)
- [贡献 / Contributing](CONTRIBUTING.md)

`validated` 表示通过程序的结构和证据摘录检查，不表示事实已被人工确认。普通网页提取不是对所有网站的支持承诺；可选浏览器适配器需要额外安装。同址更新通过 `--refresh-existing` 显式开启；复杂分页、PDF 和已有复杂 Excel 文件回填不在当前版本范围内。 / `validated` means the record passed structural and excerpt checks, not human fact-checking. Basic HTML extraction does not guarantee compatibility with every site. The optional browser adapter requires additional installation. Use `--refresh-existing` to revisit saved URLs. General pagination, PDFs, and filling complex existing Excel workbooks are outside this release.

**许可证 / License:** [Apache-2.0](LICENSE) · [版权与来源声明 / Notices](NOTICE)

**仓库 / Repository:** [workstonedai-collab/global-knowledge-crawl-pipeline](https://github.com/workstonedai-collab/global-knowledge-crawl-pipeline)
