# Global Knowledge Pipeline (by GKN)
# GKN全球信息采集程序

这是一个简易但好用的网络信息追踪/爬取程序，既支持爬取给定的网址栏目链接，也支持根据给定的关键词自动进行互联网检索并爬取相应信息，爬取后支持接入额外API对信息写摘要、研判、打标签，检索也支持接入深度搜索类的API。

它适合接入自动化信息追踪流程和机制中，辅助你追踪和收集互联网信息和热点。

如果你并不精通编程，可以直接丢给你的agent，让它帮你部署这个程序，你只需要根据你的agent引导提供网址链接、检索关键词、API密钥等，即可运行。

[双语入口](README.md) · [English](README.en.md)

维护一份信息表，往往需要反复打开网站、搜索关键词、复制正文、整理字段，再判断哪些信息重复、哪些结论还需要核实。**GKN全球信息采集程序把这些步骤连接起来：你定义要看哪些来源、要整理哪些字段、使用哪些服务，程序负责持续收录和留下处理依据。**

它可以用于产品动态、公开政策、行业资讯或研究材料。比如，把“链接、发布机构、动态类别、摘要”整理成产品更新表；更换字段模板后，也能整理成“发布机构、生效日期、适用对象、政策摘要”的政策监测表。

当前版本是可独立运行的命令行项目，面向个人和小团队。源于 GKN 工作流的阶段划分与恢复经验，通用实现使用独立代码、虚构样例和新的仓库边界。

## 你可以做什么

- **组合发现渠道**：网页 URL、RSS/Atom、列表页链接和关键词搜索可以进入同一个候选池。
- **保留来源**：同一个 URL 的跟踪参数会被清理；相同正文会合并为代表记录，并保留关联来源与重复报告。
- **自定义收录字段**：字段名称、类型、提取要求、枚举、必填项、证据要求都可配置，中文字段名也可使用。
- **选择自己的服务**：搜索 API 与 AI 富化 API 分开配置；支持兼容 Chat Completions 的接口和通用 HTTP JSON 映射。
- **持续运行与恢复**：候选、正文和富化结果分别持久化；失败可以在后续运行重试，已保存的成功结果会复用。
- **获得可复核结果**：类型不符、必填项缺失或证据摘录不匹配时进入 `needs_review`，并解释原因。
- **导出常用格式**：CSV 和 Excel 按模板列顺序生成；JSONL 保留正文、证据和系统追踪信息。

## 立即运行离线演示

需要 Python 3.9 或更高版本。JSON 配置、离线演示及 CSV/Excel/JSONL 导出只使用 Python 标准库，无需安装第三方包。

在项目目录运行：

```bash
python3 -m gkp validate examples/demo.json
python3 -m gkp run examples/demo.json
```

示例包括虚构的列表页、RSS、关键词搜索、文章正文和模拟富化结果。程序实际解析这些文件并执行处理链，但不会调用网络或真实 AI，也不会访问示例的 `example.*` 网址。

第一次运行会发现 4 个候选：其中一个是其他网址上的完全相同正文，最终输出 3 条记录。2 条通过校验；另 1 条缺少摘要，进入复核队列。

```text
runtime/fictional_updates/
├── state.sqlite              增量与阶段状态
└── output/
    ├── table.xlsx            可直接查看的表格
    ├── table.csv             便于导入其他工具的表格
    ├── records.jsonl         正文、字段、证据与来源
    ├── review.json           待复核完整记录
    ├── failures.json         失败记录与安全错误码
    ├── duplicates.json       重复关系与合并依据
    └── run-report.json       本次运行统计与预算
```

再次运行相同命令，已保存的富化结果会复用；本次模拟 AI 调用次数为 0。输出采用当前数据集的完整快照写入，不是逐次追加重复行。

## 安装为命令

可选安装后使用 `gkp` 命令：

```bash
python3 -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install .
gkp run examples/demo.json
```

希望使用 YAML 配置时安装 `python -m pip install '.[yaml]'`。可选浏览器正文采集使用 `python -m pip install '.[browser]'`，再运行 `python -m playwright install chromium`。

## 定义自己的信息表

[产品模板](examples/product-template.json) 中，一个需要 AI 提取的字段这样定义：

```json
{
  "name": "organization",
  "type": "string",
  "instruction": "Extract the explicitly named organization. Return null if unknown.",
  "evidence_required": true
}
```

原始字段可以直接映射，如 `"source": "metadata.title"`。AI 字段使用 `instruction` 描述要求。设置 `required`、`enum` 和 `evidence_required` 后，程序会校验结果。没有依据时应返回空值，空值不等于事实不存在。

字段模板支持 `string`、`integer`、`number`、`boolean`、`array`、`object`。数组可指定 `items_type`。字段名称支持有效标识符，包括中文；系统字段以下划线开头，不能作为用户字段名。列顺序就是模板中的顺序。

更换模板后，程序会保留已有正文，为新模板重新富化。旧模板结果仍在状态库中；改变模板、服务配置或输出 token 上限会改变富化缓存签名。

Excel 输出是新生成的单工作表，支持冻结表头和筛选。当前不回填复杂 Excel 模板，也不保留现有工作簿的公式与样式。

## 接入真实来源与自己的 API

复制 [live.example.json](examples/live.example.json)，修改来源、接口地址和模型名称。搜索接口的返回字段不必与示例相同，可以通过 `items_path` 和 `fields` 映射。

深度搜索类 API 可通过同一搜索适配器接入：配置请求参数，并把返回的网页结果映射到 URL、标题和摘要。需要异步轮询、特殊签名，或仅返回研究报告而不含网页结果的服务，需要增加适配逻辑。

富化接口可以选择：

| 适配器 | 用途 |
| --- | --- |
| `fixture` | 本地模拟结果，供演示和测试 |
| `chat_completions` | 接入兼容相应请求/响应格式的聊天模型服务 |
| `http_json` | 接入你已有的 HTTP JSON 富化服务，可配置请求体与返回路径 |

密钥从环境变量读取，配置只填写变量名，如 `GKP_SEARCH_API_KEY`、`GKP_ENRICH_API_KEY`。程序不自动读取 `.env`。正文与字段要求会发送给你配置的富化服务；请按自己的数据边界选择服务和来源。

地址、协议、认证方式和 JSON 结构都需要对应配置；这不是“任何 API 只换 URL 就能接入”的承诺。复杂签名、自动分页和流式协议需要扩展适配器。

[API 接入说明](docs/adapters.md) 给出请求占位符、嵌套响应路径和自定义服务示例。

## 增量、重试和复核

```bash
# 指定独立状态与输出目录
python3 -m gkp run examples/demo.json --workspace runtime/my-demo

# 只继续处理已有候选
python3 -m gkp run examples/demo.json --workspace runtime/my-demo --no-discovery

# 修复配置或服务后，显式重新尝试失败项
python3 -m gkp run examples/demo.json --workspace runtime/my-demo --retry-failed

# 仅重新富化当前模板下的待复核项；可能产生新的 API 费用
python3 -m gkp run examples/demo.json --workspace runtime/my-demo --retry-review

# 从已保存的结果重新导出，不请求任何外部服务
python3 -m gkp export examples/demo.json --workspace runtime/my-demo
```

增量时间窗按来源或关键词保存，默认向前重叠 24 小时，配合 URL 去重减少迟到数据漏收。未知发布时间保持未知，不会被假定为刚发布。来源发现失败或因条目上限被截断时，该来源的进度不前移。

瞬时网络错误和部分服务错误可在下一次运行重试，每个阶段默认最多 3 次失败尝试；没有立即循环重试。已保存的成功富化结果复用，不承诺“远端已经成功、本地尚未保存”这个崩溃间隙也能实现恰好一次调用。

`validated` 仅表示通过类型、必填项、枚举和证据摘录检查。证据摘录在正文中出现，不足以证明模型结论正确或完整；重要信息仍需人工复核。程序不包含自动发布到网站或数据平台的步骤。

## 预算与运行状态

可限制每次新增/处理条目数、搜索请求、HTTP 请求、AI 调用次数和输出 token。总 token 使用保守的输入字节估计加输出上限进行预留，并记录服务返回的用量；它不是精确分词或账单上限保证。自定义 HTTP 服务需真正执行传入的输出限制。

运行返回码：`0` 完成（可以包含待复核项），`1` 配置或本地错误，`2` 部分失败，`3` 因预算暂停，`130` 用户中断。完整原因在运行报告中。

## 当前范围与限制

- 普通 HTML、RSS/Atom 与列表页支持是基础能力；不保证自动适配所有网站。
- 列表页按链接和可选 URL 正则发现文章，默认不跟随外站链接；暂不支持通用分页。
- 去重依据规范化 URL 或相同正文；不做跨语言语义去重，不自动删除近似改写报道。
- 已保存 URL 的正文不会自动重抓，适合持续发现新链接；既有页面的内容变更检测待后续扩展。
- 浏览器适配器为可选路径；当前验收覆盖标准 HTML 和本机模拟 HTTP API，没有验证任意实际动态网站。
- 不支持 PDF、登录内容、付费墙绕过、复杂工作簿回填或多机分布式任务。
- 默认遵守 robots.txt；robots 规则不能代替内容授权。实际来源仍需自行确认使用条件。
- 默认拒绝本机或私有地址；`allow_private_network: true` 可用于自己控制的内网服务。此检查不是针对恶意配置的完整网络隔离机制。

## 验证与贡献

```bash
python3 -m unittest discover -s tests -v
```

验证包含离线端到端、模板变更、去重、断点恢复、重试、调用上限、字段与证据校验，以及本机模拟搜索和富化 API。测试服务器只监听回环地址，不需要外部账号或密钥。

欢迎改进提取质量、适配器、模板和恢复逻辑。请使用虚构或可再使用样例，不提交凭据、私有来源清单或真实业务数据。见 [贡献指南](CONTRIBUTING.md)。

**许可证**：[Apache-2.0](LICENSE)。允许在遵守许可证条件的前提下使用、修改与商业复用。分发时请保留许可证与相关声明，并按要求标明修改；详见 [NOTICE](NOTICE) 和许可证全文。

**项目仓库**：[workstonedai-collab/global-knowledge-pipeline](https://github.com/workstonedai-collab/global-knowledge-pipeline)。
