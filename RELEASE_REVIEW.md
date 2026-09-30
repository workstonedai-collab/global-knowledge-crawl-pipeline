# 开源发布记录 / Open-source publication record

这是一个简易但好用的网络信息追踪/爬取程序，既支持爬取给定的网址栏目链接，也支持根据给定的关键词自动进行互联网检索并爬取相应信息，爬取后支持接入额外API对信息写摘要、研判、打标签，检索也支持接入深度搜索类的API。

它适合接入自动化信息追踪流程和机制中，辅助你追踪和收集互联网信息和热点。

如果你并不精通编程，可以直接丢给你的agent，让它帮你部署这个程序，你只需要根据你的agent引导提供网址链接、检索关键词、API密钥等，即可运行。

Global Knowledge Crawl Pipeline is a simple but useful tool for tracking and crawling information on the web. It can crawl the website section or listing URLs you provide, or automatically search the internet using your keywords and collect the information it finds. After collection, you can connect additional APIs to generate summaries, analyze the information, and add tags. Search can also connect to deep-search APIs.

Use it as part of an automated information monitoring workflow to track and collect online information and trending topics.

If you are not familiar with programming, you can give this project to your AI agent and ask it to deploy the program for you. Follow your agent's guidance to provide website URLs, search keywords, API credentials, and other configuration needed to run it.

项目 / Project: **Global Knowledge Crawl Pipeline (by GKN)｜GKN全球信息采集程序**

版本 / Version: **0.1.1**

公开仓库 / Public repository: [workstonedai-collab/global-knowledge-crawl-pipeline](https://github.com/workstonedai-collab/global-knowledge-crawl-pipeline)

状态 / Status: 已公开，默认分支为 main，GitHub 已识别 Apache-2.0。 / Public, default branch main, Apache-2.0 recognized by GitHub.

## 0.1.1 名称更新 / Naming update

项目统一更名为 **Global Knowledge Crawl Pipeline (by GKN)**；仓库与安装包名称为 `global-knowledge-crawl-pipeline`。命令仍为 `gkp`，中文名仍为 GKN全球信息采集程序，处理功能不变。v0.1.0 的下载包保留为历史版本。 / The project is now **Global Knowledge Crawl Pipeline (by GKN)**, with repository and distribution name `global-knowledge-crawl-pipeline`. The `gkp` command and Chinese name remain the same; processing behavior is unchanged. v0.1.0 assets remain historical releases.

## 仓库主页介绍 / About description

GKN全球信息采集程序：简易好用的网页栏目爬取与关键词检索工具，可接深度搜索和AI摘要、研判、标签API，融入自动化追踪，也可交给agent部署。 Global Knowledge Crawl Pipeline (by GKN): track web listings and keyword searches, connect deep-search and AI APIs for summaries, analysis and tags, automate information intake, and let your agent help deploy it.

建议主题 / Suggested topics: `information-extraction`, `web-scraping`, `rss`, `keyword-search`, `data-pipeline`, `ai`, `structured-data`, `python`, `csv`, `excel`.

## 发布文件范围 / Release surface

- 通用 Python 实现、配置与字段模板、虚构离线样例、验证、双语文档与 CI 工作流。 / Generic Python implementation, configuration/templates, fictional offline fixtures, tests, bilingual documentation, and CI workflow.
- 不含真实业务来源、私有接口、密钥、采集结果、生产调度配置或原仓库历史。 / No real business registries, private endpoints, credentials, collected data, production scheduler configuration, or inherited Git history.
- 正文、SQLite 和导出均位于忽略的 runtime 目录。 / Bodies, SQLite, and exports live in ignored runtime directories.

## 本地验证 / Local evidence

- 28 项验证通过：离线链、HTML/RSS/Atom、去重、模板变化与中文自定义 AI 字段、已保存结果的中断恢复、重试、字段与证据、预算，以及本机模拟 API 请求与返回映射。 / 28 passing tests covering offline flow, HTML/feed extraction, deduplication, schema changes and custom Chinese AI fields, saved-stage recovery, retries, field/evidence checks, budgets, and local mock APIs.
- 首次离线演示：4 个候选，3 条输出，2 条 validated，1 条 needs_review，1 条正文重复；HTTP 请求为 0。 / First demo: four candidates, three output records, two validated, one review item, one exact-body duplicate, zero HTTP requests.
- 相同模板再次运行：无新增候选，已保存结果不重复富化。 / Rerun: no new candidates and no repeated enrichment for persisted results.
- CSV/Excel/JSONL 实际输出；Excel 由独立读取库读取，4 行、11 列，包括表头。 / Actual CSV/Excel/JSONL outputs; the workbook was read by an independent library with four rows and eleven columns including the header.
- Python 3.9 的提取与校验测试通过；完整流程与本机接口验证使用 Python 3.11。GitHub 自动验证矩阵覆盖 Linux、Windows、macOS 与 Python 3.9/3.11/3.13，最新结果见 [Tests](https://github.com/workstonedai-collab/global-knowledge-crawl-pipeline/actions/workflows/tests.yml)。 / Extraction/validation tests passed on Python 3.9; the full local suite ran on 3.11. GitHub's matrix covers three systems and three Python versions; see Tests for the latest results.
- 动态网页适配器是可选实现，尚未完成真实动态网站验收；真实付费搜索/模型服务没有调用。 / Browser adapter is optional and unaccepted against real dynamic sites; no real paid search/model service was called.
- 已构建并安装 wheel；在项目目录以外通过安装后的命令完成验证、首次离线运行和恢复运行。 / Built and installed the wheel, then ran validation, a first offline run and a resumed run outside the project directory using the installed command.
- 最终 43 个跟踪文件的敏感模式检查无命中，运行目录未加入 Git；10 个 Markdown 文件的本地链接完整。 / No sensitive-pattern findings in 43 final tracked files; runtime is not tracked. Local links in ten Markdown files resolve.
- Apache-2.0 的 LICENSE、NOTICE 及 SPDX 元数据已包含在重新构建的安装包中。 / Rebuilt installation package includes Apache-2.0 LICENSE, NOTICE and SPDX metadata.

## 发布检查 / Publication checks

1. 已确认 Apache-2.0，已补入 LICENSE、NOTICE、包元数据与各语言文档。 / Apache-2.0 confirmed and added to LICENSE, NOTICE, package metadata and language guides.
2. 对发布文件和独立 Git 历史做敏感模式检查，未发现命中。 / Scanned release files and independent history, with no pattern findings.
3. 已创建公开仓库并上传，双语介绍与 10 个主题已设置；线上 43 个文件的内容哈希与本地发布版本逐项核对。 / Created the public repository, uploaded files, configured bilingual About and ten topics, and compared all 43 remote file hashes with the local version.
4. 首次自动验证发现 Windows 测试读取中文样例的默认编码问题，已改为显式 UTF-8；命令输出也显式使用 UTF-8。 / The initial matrix found default-encoding errors when Windows tests read Chinese fixtures. Tests and CLI output now use explicit UTF-8.

`scripts/release_check.py` 提供已跟踪文件的敏感模式检查；不等同于完整的凭据或产权审计。 / The script checks tracked files for sensitive patterns; it is not an exhaustive credential or ownership audit.
