# 三种离线场景 / Three offline scenarios

所有机构、网址、文章和模型结果均为虚构；运行不请求网络、不需要密钥，也不调用真实 AI。程序实际执行正文提取、模板校验、去重和导出，富化结果由本地 fixture 提供。 / All organizations, URLs, articles and model results are fictional. No network, keys or real AI are used. The pipeline performs extraction, validation, deduplication and export; enrichment comes from local fixtures.

| 场景 / Scenario | 命令 / Command | 预期 / Expected |
| --- | --- | --- |
| 产品与服务动态 / Product updates | `python3 -m gkp run examples/demo.json` | 3 条记录，1 条待复核；1 个重复正文 / 3 records, 1 review item, 1 exact duplicate |
| 政策试点 / Policy proposal | `python3 -m gkp run examples/policy-demo.json` | 1 条通过结构与摘录检查；保留拟议状态 / 1 record passing checks, retaining proposal status |
| 初步研究 / Preliminary research | `python3 -m gkp run examples/research-demo.json` | 1 条通过检查；保留样本与未复现限制 / 1 record passing checks, retaining sample and replication limits |

打开 `runtime/<dataset>/output/evidence.html` 对照字段与原文。重复运行应复用富化结果。 / Open `runtime/<dataset>/output/evidence.html` to compare fields with source text. Repeated runs reuse enrichment.

## 体验同址更新 / Try an update at the same URL

1. 先运行产品示例。 / Run the product demo.
2. 在独立副本的 `examples/fixtures/library.html` 中，把 `four-week` 改成 `six-week`。 / In your own copy, replace `four-week` with `six-week` in `examples/fixtures/library.html`.
3. 运行 `python3 -m gkp run examples/demo.json --no-discovery --refresh-existing`。 / Run the refresh command.
4. 查看 `changes.json` 与证据页中的前后差异。旧模拟 AI 结果仍引用 four-week，因此该字段会被标记待复核。只有这条变化记录重新富化。 / Inspect `changes.json` and the evidence diff. The fixture result still quotes four-week, so that field needs review. Only the changed record is re-enriched.

这些示例展示的是流程，不代表实际模型质量。实际运行前请替换来源、选择服务并按 [配置指南](../docs/configuration-builder.md) 设置环境凭据。 / These scenarios demonstrate workflow, not model quality. Replace sources and services and follow the [builder guide](../docs/configuration-builder.md) before live use.
