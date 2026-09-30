# 发布候选审阅 / Release candidate review

项目 / Project: **Global Knowledge Pipeline (by GKN)｜GKN全球信息采集程序**

候选版本 / Candidate: **0.1.0**

计划仓库 / Intended repository: `workstonedai-collab/global-knowledge-pipeline`

状态 / Status: 本地实现与验收，许可证待选择；尚未创建公开仓库。 / Implemented and verified locally, license pending; no public repository created yet.

## 仓库主页介绍 / Proposed About description

GKN全球信息采集程序：网页/RSS与关键词发现→自定义AI字段富化→CSV/Excel/JSONL，支持来源追溯、增量与失败恢复。 Global Knowledge Pipeline (by GKN): discover web/RSS and search results, enrich custom fields with your APIs, export reviewable tables with provenance and resumable runs.

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
- Python 3.9 的提取与校验测试通过；完整流程与本机接口验证使用 Python 3.11。CI 矩阵已准备，尚未在 GitHub 执行。 / Extraction/validation tests passed on Python 3.9; the full suite ran on 3.11. CI is configured but has not run on GitHub.
- 动态网页适配器是可选实现，尚未完成真实动态网站验收；真实付费搜索/模型服务没有调用。 / Browser adapter is optional and unaccepted against real dynamic sites; no real paid search/model service was called.
- 已构建并安装 wheel；在项目目录以外通过安装后的命令完成验证、首次离线运行和恢复运行。 / Built and installed the wheel, then ran validation, a first offline run and a resumed run outside the project directory using the installed command.
- 41 个跟踪文件的敏感模式检查无命中，运行目录未加入 Git；10 个 Markdown 文件的本地链接完整。 / No sensitive-pattern findings in 41 tracked files; runtime is not tracked. Local links in ten Markdown files resolve.

## 公开前剩余步骤 / Remaining publication steps

1. 所有者选择许可证，补入 LICENSE 与各语言文档。 / Owner selects the license; add its text and update guides.
2. 对最终发布文件与新的 Git 历史再检查敏感信息。 / Recheck the final files and new history for sensitive material.
3. 创建公开仓库、上传、设置双语介绍与主题，核对线上文件。 / Create the public repository, upload, set bilingual About/topics, and verify remote files.

`scripts/release_check.py` 提供已跟踪文件的敏感模式检查；不等同于完整的凭据或产权审计。 / The script checks tracked files for sensitive patterns; it is not an exhaustive credential or ownership audit.
