# 服务接口 / Service adapters

[中文指南](../README.zh-CN.md) · [English guide](../README.en.md)

## 认证与错误 / Authentication and errors

配置中只写 `credential_env`，密钥由当前进程环境提供。`auth_header` 默认 `Authorization`，`auth_prefix` 默认 `Bearer `。使用 `X-API-Key` 的服务通常需要空前缀。程序不加载 `.env`，`.env.example` 仅列出变量名。 / Reference a process environment variable with `credential_env`. The default header is Authorization with a Bearer prefix. X-API-Key services commonly need an empty prefix. `.env` is not automatically loaded; the example documents variable names only.

API 重定向被拒绝，以避免认证头被转发到另一个服务。返回错误使用 HTTP 状态或安全错误码，不把响应正文、密钥或请求头写入报告。 / API redirects are rejected to prevent credential forwarding. Errors are represented by status or safe codes; response bodies, credentials, and request headers are not logged.

## 搜索 / Search

```json
{
  "provider": "http_json",
  "endpoint": "https://api.example.com/search",
  "method": "POST",
  "credential_env": "GKP_SEARCH_API_KEY",
  "queries": ["public product updates"],
  "request": {"q": "$query", "after": "$since", "limit": "$limit"},
  "response": {
    "items_path": "data.items",
    "fields": {"url": "link", "title": "heading", "snippet": "description", "published_at": "published_at"}
  }
}
```

支持 GET 与 POST。GET 的 `request` 转为查询参数；POST 转为 JSON。请求占位符是整个值的 `$query`、`$since`、`$limit`；首轮 `$since` 为 null。 / GET request mappings become query parameters; POST mappings become JSON. Supported placeholders are whole values: query, since, limit. Since is null on the first run.

`items_path` 定位结果数组，`fields` 定位每条结果的字段；路径支持点分字典键和数组下标，例如 `data.items`、`choices.0.message.content`。不支持键名本身含点或 JSONPath 表达式。URL 必须存在；标题、摘要和发布时间可缺失。 / Dot paths address dictionary keys and numeric list indexes. Keys containing dots and JSONPath expressions are unsupported. URL is required; title, snippet, and publication date may be absent.

搜索适配器当前处理一次响应，不自动翻页。如果服务不支持时间筛选，程序仍对已知发布时间做本地筛选并按 URL 去重。搜索日期可能是索引时间而不是原文发布日期，需按提供者语义配置。 / The adapter processes one response without automatic pagination. Local date filtering and URL deduplication still apply if the service lacks time filters. Map provider dates carefully: an index date may differ from publication time.

## Chat Completions 富化 / Chat Completions enrichment

```json
{
  "provider": "chat_completions",
  "endpoint": "https://api.example.com/v1/chat/completions",
  "credential_env": "GKP_ENRICH_API_KEY",
  "model": "your-model-name",
  "json_mode": true,
  "parameters": {"temperature": 0}
}
```

`endpoint` 是完整请求地址，程序不自动追加路径。请求包括 model、messages、max_tokens，可选 JSON mode；读取 `choices.0.message.content`，期待其中是 JSON 字符串。 / The endpoint is the complete request URL. The adapter sends model, messages, max_tokens, and optional JSON mode. It expects a JSON string in the first choice's message content.

并非所有供应商、模型都接受这些参数。可关闭 `json_mode`；若服务需要不同的输出限制参数或响应协议，请使用通用适配器。 / Not every model accepts these parameters. JSON mode can be disabled. Use the generic adapter if a service requires different output-limit parameters or response conventions.

允许的附加参数为 `temperature`、`top_p`、`seed`、`frequency_penalty`、`presence_penalty`，不能通过附加参数覆盖系统提示词和预算。 / Additional parameters are limited to temperature, top_p, seed, frequency_penalty, and presence_penalty. They cannot override prompts or budgets.

## 自定义 HTTP 富化 / Custom HTTP enrichment

将 [custom-enrichment.example.json](../examples/custom-enrichment.example.json) 的内容放入主配置的 `enrichment`，再按服务实际协议修改。 / Place the example adapter object in the main config's enrichment section and adapt it to your service.

```json
{
  "provider": "http_json",
  "endpoint": "https://api.example.com/enrich",
  "credential_env": "GKP_ENRICH_API_KEY",
  "auth_header": "X-API-Key",
  "auth_prefix": "",
  "request": {"document": "$text", "schema": "$schema", "instructions": "$prompt", "max_tokens": "$max_output_tokens"},
  "response_path": "data.result",
  "usage_path": "data.usage.total_tokens"
}
```

占位符支持 `$text`、`$schema`、`$prompt`、`$title`、`$url`、`$model`、`$max_output_tokens`。整个值替换保留 JSON 类型，`$schema` 会作为对象传递；不执行表达式或任意代码。 / Whole-value placeholders preserve JSON types: the schema is an object. No expressions or arbitrary code are evaluated.

`response_path` 指向 `{fields, evidence}` 对象或其 JSON 字符串；空路径使用整个响应。`usage_path` 可选，读取总 token 数。你自己的服务必须执行映射的输出限制，否则本地预留不能保证远端用量。 / The response path selects the fields/evidence object or a JSON string containing it; an empty path uses the entire response. Usage path optionally reads total tokens. The remote service must enforce its configured output limit.

## 可选浏览器 / Optional browser

`fetch.provider: "browser"` 使用 Playwright Chromium 渲染正文，再使用同一 HTML 提取器。默认禁用 service worker，拦截每个网络请求，阻止图片、字体、媒体；导航检查 robots，所有请求计入 HTTP 预算。列表页发现仍使用 HTTP，不会自动滚动或点击。 / Browser mode renders article HTML with Playwright Chromium, then uses the same extractor. Service workers are disabled and requests are gated and budgeted; images, fonts, and media are blocked. Navigation checks robots. Listing discovery remains HTTP without automatic scrolling or clicking.

安装和网站差异可能造成失败，错误为安全代码。当前发布候选尚未对真实动态网站完成浏览器验收。 / Installation and site differences can cause safe-code failures. Browser compatibility with real dynamic sites has not been accepted for this candidate.

适配器 API 参考 / Adapter API reference: [Playwright Python Browser](https://playwright.dev/python/docs/api/class-browser).
