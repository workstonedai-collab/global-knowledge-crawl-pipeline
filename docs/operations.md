# 运行、恢复与输出 / Operations and recovery

## 运行 / Run

```bash
python3 -m gkp run examples/demo.json --workspace runtime/demo
python3 -m gkp run examples/demo.json --workspace runtime/demo --no-discovery
python3 -m gkp export examples/demo.json --workspace runtime/demo
```

同一个 workspace 使用进程锁，避免两个任务同时写状态和输出。不同数据集必须使用不同 workspace；即使参数不同，同一 workspace 的两个运行也不会并发执行。 / A workspace lock prevents overlapping state/export writes. Different datasets need separate workspaces; even differently configured runs cannot overlap within one workspace.

状态位于 `state.sqlite`。导出是整个数据集在当前模板下的快照；文件分别原子替换，进程中断时可重新执行 export 恢复一致的文件集。 / State is stored in SQLite. Exports are current-contract snapshots of the dataset. Files are atomically replaced individually; rerun export after interruption to regenerate a consistent set.

## 状态 / Record and run status

| 记录状态 / Record | 含义 / Meaning |
| --- | --- |
| `pending` | 已发现，尚未完成当前模板下的处理 / Discovered but unfinished under the current contract |
| `validated` | 通过自动结构与摘录检查 / Passed automated structural and excerpt checks |
| `needs_review` | 字段缺失、错误、证据不足或正文截断 / Missing/invalid fields, insufficient excerpts, or truncated text |
| `failed` | 正文或服务处理失败 / Fetch or enrichment failure |

正文重复关系单独保存在 `duplicates.json`；代表记录保留关联来源。 / Exact-body duplicates are reported separately; representative records retain related origins.

运行状态为 `completed`、`completed_with_review`、`partial`、`paused`。部分来源失败不会取消其他来源已完成的结果。预算暂停保留阶段进度，后续运行可继续。 / Runs can complete, complete with review, partially fail, or pause. A failing source does not discard another source's results. Budget pauses preserve stage progress.

## 重试 / Retry

```bash
python3 -m gkp run examples/demo.json --workspace runtime/demo --retry-failed
python3 -m gkp run examples/demo.json --workspace runtime/demo --retry-review
```

瞬时网络错误、408/425/429、5xx 等在下次运行可自动重试，默认最多 3 次失败尝试。配置、权限、过短正文等非瞬时错误需要修复后显式 retry。 / Transient network errors, selected retryable HTTP statuses, and server errors can retry on later runs, by default up to three failures. Configuration, permissions, short bodies, and other permanent errors need repair and explicit retry.

`--retry-failed` 重置失败的抓取尝试和当前签名的失败富化；`--retry-review` 只删除当前签名下的待复核富化结果。两者都保留已通过校验的结果。 / Failed retry resets fetch failures and failed enrichment for the current signature. Review retry removes only review results for that signature. Validated results are retained.

缺少环境变量属于配置错误；补入凭据后使用 `--retry-failed`。不要删除全部状态来修复一条错误。 / Missing credentials are configuration errors; set them and retry failed stages rather than deleting all state.

## 增量边界 / Incremental boundaries

发现进度只有在该来源的候选已保存且遍历完成后才前移；正文或 AI 失败的候选保留在队列。默认的 24 小时重叠窗口只能减少迟到信息漏收，不保证补回所有历史记录。 / Discovery checkpoints advance only after candidates are saved and enumeration completes. Failed later stages remain queued. The default overlap reduces late-arrival misses but cannot guarantee historical completeness.

未知时区、未知发布时间不用于时间过滤；记录保持未知。搜索提供者可能不支持时间参数，单次响应和无分页限制也可能导致漏收。 / Unknown times/zones are not used for date cutoffs. Search capability and the single-response/no-pagination limit can cause misses.

当前记录标识基于规范化 URL；相同 URL 的网页更新不会自动生成新版本。新的模板签名重新使用已保存的正文，不等于重新抓取网页。 / Identity is based on canonical URL. Content updates at the same URL do not create a new version automatically. A new schema reuses stored text rather than refreshing the page.

## 预算与错误 / Budgets and errors

`run-report.json` 包含调用计数、token 预留和提供者返回的用量。离线 fixture 富化也计入 `ai_calls`，但没有付费调用。 / Reports include request counts, token reservation, and provider-supplied usage. Fixture enrichment counts as an AI call for budgeting but is not a paid request.

常见错误 / Common errors:

| 错误码 / Code | 处理 / Action |
| --- | --- |
| `missing_credential_env` | 配置环境变量，再重试失败项 / Set the environment variable, retry failures |
| `invalid_api_json` | 核对 API 返回格式 / Check API response format |
| `api_redirect_blocked` | 使用最终 API 地址 / Configure the final API URL |
| `robots_disallowed` | 使用允许的来源或取得合适访问方式 / Use an allowed source or appropriate authorized access |
| `robots_unavailable` | 检查来源可达性，避免静默忽略规则 / Check reachability instead of silently ignoring rules |
| `private_address_blocked` | 仅自己控制的内网服务可显式启用 / Explicitly allow only private services you control |
| `body_too_short` | 检查页面是否为正文，必要时改采集适配器 / Check article extraction or switch adapter |
| `budget_*` | 调整预算或在下次运行继续 / Adjust budget or continue next run |
| `workspace_already_running` | 等待已有任务结束 / Wait for the existing run |

程序不会记录原始 API 错误正文。运行目录包含正文和采集信息，可能是私有数据；默认忽略，不加入 Git。 / Raw provider error bodies are not logged. Runtime state contains collected text and can be private; it is ignored by Git.

## 定时运行 / Scheduling

将 `gkp run` 接入用户自己的任务调度器即可。先执行单次小预算验收，再设置频率；调度器应区分退出码 2 和 3，避免立即无限重试。锁机制会拒绝同一 workspace 的重叠运行。 / Connect the run command to your scheduler after a small-budget acceptance run. Treat partial failure and budget pause separately rather than immediately retrying forever. The workspace lock rejects overlapping jobs.

项目不附带机器专有的任务文件，也不调整系统全局环境。 / No machine-specific scheduler files or global environment changes are included.
