# Changelog / 更新记录

## 0.2.0 — configure, refresh and review / 配置、更新与证据复核

- Offline bilingual browser configuration builder with product, policy and research presets. / 离线双语配置器，提供产品、政策与研究字段预设。
- Opt-in refresh of stored URLs with a persisted rotation cursor, normalized-text change history and selective re-enrichment. / 显式轮转刷新已存网址，记录正文变化，只重新富化受影响条目。
- Local HTML evidence report and JSON revision export. / 本地 HTML 证据页与 JSON 变化日志。
- Duplicate relationships are recalculated after refresh; failed refreshes preserve saved results. / 刷新后重新计算重复关系；抓取失败保留已有结果。
- Three fictional offline scenarios and expanded Chinese/English guides. / 三种虚构离线场景与扩充的中英文教程。

## 0.1.1 — naming and documentation update / 名称与介绍更新

- Renamed the project to Global Knowledge Crawl Pipeline (by GKN), including repository links, package metadata, CLI help and run reports. The `gkp` command and processing behavior are unchanged. / 项目更名为 Global Knowledge Crawl Pipeline (by GKN)，同步仓库链接、安装包元数据、命令行帮助和运行报告；`gkp` 命令及处理功能不变。
- Expanded the opening introductions in Chinese and English, including agent-assisted deployment and deep-search API configuration. / 扩充中英文开篇介绍，说明可由 agent 协助部署，以及深度搜索 API 的接入方式。

## 0.1.0 — initial release / 首个版本

- Website/listing/RSS/Atom discovery and configurable HTTP keyword search.
- HTML body extraction and optional Playwright rendering adapter.
- Custom field templates, metadata mapping, types, enums, required fields and excerpts.
- Fixture, Chat Completions and HTTP JSON enrichment adapters.
- SQLite incremental stages, saved-result recovery, exact URL/body deduplication and retries.
- CSV, Excel and JSONL snapshots, review/failure/duplicate outputs and run reports.
- Request limits and conservative token reservations.
- Fully offline fictional demonstration, local mock API tests and Chinese/English documentation.

Licensed under Apache-2.0. / 采用 Apache-2.0 许可证。
