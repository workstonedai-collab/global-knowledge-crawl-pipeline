# 浏览器配置器 / Browser configuration builder

## 1. 生成并打开 / Generate and open

```bash
python3 -m gkp configure --output runtime/configure.html
```

双击生成文件，使用本地浏览器打开。页面无需服务器，不连接网络。 / Open the generated file in your browser. It needs no server or network connection.

## 2. 填写你的目标 / Describe your workflow

选择场景预设，再修改： / Choose a preset, then adjust:

- 数据集名称：用于独立状态目录，例如 `policy_watch`。 / Dataset name: identifies a separate state directory, e.g. `policy_watch`.
- 来源：列表页、RSS/Atom 或单篇网址；每行一个。同一配置器批次使用一种来源类型，混合类型可下载后编辑配置。 / Sources: listing pages, RSS/Atom or article URLs, one per line. One builder batch uses one source type; edit the generated configuration to mix types.
- 关键词：每行一个检索任务，留空则不使用搜索。 / Keywords: one search task per line; leave blank to disable search.
- 字段：名称、类型和要求。页面预览的是列结构，不是实际采集结果。 / Fields: name, type and extraction instructions. The preview shows columns, not collected data.
- 服务：填写实际 AI 地址与模型；使用关键词时填写搜索地址。 / Services: supply a working AI endpoint and model, and a search endpoint when using queries.

配置器生成 Chat Completions 富化格式；搜索默认使用 HTTP JSON 的 `query`、`since`、`limit` 请求与 `results` 返回映射。其他格式需修改 [API 映射](adapters.md)。来源页仍需允许采集，服务须兼容配置。 / The generated enrichment uses Chat Completions. Search defaults to HTTP JSON with `query`, `since` and `limit` request fields and a `results` array. Adjust [API mappings](adapters.md) for other formats. Source access and provider compatibility still need checking.

## 3. 下载与验证 / Download and validate

分别点击下载配置和模板，保留为同一文件夹内的 `config.json` 与 `template.json`。 / Download configuration and template separately, keeping `config.json` and `template.json` in the same folder.

```bash
python3 -m gkp validate path/to/config.json
python3 -m gkp run path/to/config.json
```

在本地运行环境设置 `GKP_ENRICH_API_KEY`；需要认证搜索时设置 `GKP_SEARCH_API_KEY`。只在环境中提供密钥，页面不要求密钥，项目不会自动加载 `.env`。 / Set `GKP_ENRICH_API_KEY` in your local runtime; set `GKP_SEARCH_API_KEY` when search needs authentication. Keys stay in environment variables. The page does not request keys and the project does not automatically load `.env`.

## 4. 查看和复核 / Inspect and review

打开 `runtime/<dataset>/output/evidence.html`。CSV/Excel 位于同一输出目录。 / Open `runtime/<dataset>/output/evidence.html`. CSV/Excel exports are in the same output folder.

```bash
python3 -m gkp run path/to/config.json --no-discovery --refresh-existing
```

这个命令显式检查旧网址，保存变化并仅重新富化变化正文。首次请保持小预算。未接通服务时，可先运行 [完全离线示例](../examples/README.md)。 / This command explicitly checks saved URLs, retains revisions and enriches changed text. Start with a small budget. Try the [fully offline scenarios](../examples/README.md) before connecting services.
