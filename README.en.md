# Global Knowledge Crawl Pipeline (by GKN)
# GKN全球信息采集程序

Global Knowledge Crawl Pipeline is a simple but useful tool for tracking and crawling information on the web. It can crawl the website section or listing URLs you provide, or automatically search the internet using your keywords and collect the information it finds. After collection, you can connect additional APIs to generate summaries, analyze the information, and add tags. Search can also connect to deep-search APIs.

Use it as part of an automated information monitoring workflow to track and collect online information and trending topics.

If you are not familiar with programming, you can give this project to your AI agent and ask it to deploy the program for you. Follow your agent's guidance to provide website URLs, search keywords, API credentials, and other configuration needed to run it.

[Bilingual overview](README.md) · [中文](README.zh-CN.md)

Keeping an information table up to date often means repeatedly visiting sites, searching keywords, copying article text, extracting fields, and deciding which findings are duplicates or need checking. **Global Knowledge Crawl Pipeline connects those steps: you define the sources, fields, and services; the program handles recurring intake and retains the processing trail.**

Use it for product developments, public policy, industry updates, or research material. A product template might collect a title, organization, update category, and summary. A policy template could collect the issuing body, effective date, affected groups, and policy summary.

This release is a standalone command-line project for individuals and small teams. Its stage boundaries and recovery approach draw on GKN workflow experience. The general implementation uses independent code, fictional fixtures, and a separate repository boundary.

## What you can do

- **Combine discovery channels:** direct URLs, RSS/Atom feeds, links from listing pages, and keyword searches share a candidate pool.
- **Keep provenance:** normalize URL tracking parameters and merge identical article bodies while retaining related sources and a duplicate report.
- **Define your table:** configure field names, types, extraction instructions, enums, required fields, and evidence requirements. Chinese field names are supported.
- **Choose services:** configure search and enrichment independently. Use a Chat Completions-compatible service or a configurable HTTP JSON adapter.
- **Run incrementally and recover:** candidates, fetched text, and enrichment results are persisted separately. Failed stages can be retried; saved successful results are reused.
- **Inspect reviewable results:** missing required fields, type mismatches, and invalid excerpts become `needs_review` with reasons.
- **Export useful formats:** CSV and Excel follow the template order. JSONL retains text, evidence, and processing metadata.

## Run the offline demo

Requires Python 3.9+. JSON configuration, the offline demo, and CSV/Excel/JSONL export use only the standard library. No package installation is needed.

From the project directory:

```bash
python3 -m gkp validate examples/demo.json
python3 -m gkp run examples/demo.json
```

The demo includes fictional listing HTML, RSS, keyword search results, article bodies, and simulated enrichment. The program parses these files and executes the processing chain, but calls neither a network nor a real model. It does not contact the fictional `example.*` URLs.

The first run discovers four candidates. One has the same body at another URL, leaving three output records: two validated records and one deliberately missing a summary that enters the review queue.

```text
runtime/fictional_updates/
├── state.sqlite              Incremental and stage state
└── output/
    ├── table.xlsx            Readable spreadsheet
    ├── table.csv             Importable table
    ├── records.jsonl         Article text, fields, evidence, provenance
    ├── review.json           Complete records needing review
    ├── failures.json         Failed records and safe error codes
    ├── duplicates.json       Duplicate relationships and reasons
    └── run-report.json       Run statistics and budgets
```

Run the same command again to reuse saved enrichment results. The second run makes zero simulated AI calls. Exports replace the current dataset snapshot; they do not append duplicate rows on every run.

## Install the command

Optionally install the package to use `gkp`:

```bash
python3 -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install .
gkp run examples/demo.json
```

For YAML configuration, install `python -m pip install '.[yaml]'`. For optional browser article rendering, install `python -m pip install '.[browser]'`, then `python -m playwright install chromium`.

## Define your information table

An AI field in the [product template](examples/product-template.json) looks like this:

```json
{
  "name": "organization",
  "type": "string",
  "instruction": "Extract the explicitly named organization. Return null if unknown.",
  "evidence_required": true
}
```

Map original fields directly with `source`, such as `metadata.title`. Describe AI fields using `instruction`. The program validates `required`, `enum`, and `evidence_required`. Missing evidence should produce null; null does not establish that a fact is absent.

Supported types are `string`, `integer`, `number`, `boolean`, `array`, and `object`. Arrays can declare `items_type`. Names must be valid identifiers, including Chinese names. Names beginning with an underscore are reserved for system columns. Template order determines column order.

Changing the template keeps fetched text but triggers enrichment under the new contract. Earlier contract results remain in SQLite. Changes to the template, service configuration, or output token cap change the enrichment signature.

Excel output is a newly generated, single-sheet workbook with a frozen header and a filter. This release does not fill complex existing workbooks or preserve their formulas and styles.

## Connect your sources and APIs

Copy [live.example.json](examples/live.example.json) and replace sources, service endpoints, and the model. Search responses can use your provider's structure: map their result array and fields with `items_path` and `fields`.

Deep-search APIs can use the same search adapter: configure the request parameters and map returned web results to URLs, titles, and snippets. Services requiring asynchronous polling or custom signing, or returning only a research report without web results, need additional adapter logic.

| Enrichment adapter | Use |
| --- | --- |
| `fixture` | Local simulated results for demos and tests |
| `chat_completions` | A service implementing the compatible request and response format |
| `http_json` | Your existing HTTP JSON service with configurable request and response paths |

Credentials come from environment variables. Configuration contains only variable names, such as `GKP_SEARCH_API_KEY` and `GKP_ENRICH_API_KEY`. The program does not automatically load `.env`. Article text and field instructions are sent to your configured enrichment service; choose services and sources appropriate to your data boundaries.

The endpoint, protocol, authentication, and JSON structure must match the service. Changing a URL alone cannot make every API compatible. Custom signing, automatic pagination, and streaming require an adapter extension.

See [service adapters](docs/adapters.md) for request placeholders, nested response paths, and custom-service examples.

## Incremental runs, retries, and review

```bash
# Separate state and output location
python3 -m gkp run examples/demo.json --workspace runtime/my-demo

# Continue saved candidates without new discovery
python3 -m gkp run examples/demo.json --workspace runtime/my-demo --no-discovery

# Explicitly retry failed stages after fixing the service or configuration
python3 -m gkp run examples/demo.json --workspace runtime/my-demo --retry-failed

# Re-enrich only current needs_review results; this can incur new API charges
python3 -m gkp run examples/demo.json --workspace runtime/my-demo --retry-review

# Export persisted results without contacting services
python3 -m gkp export examples/demo.json --workspace runtime/my-demo
```

Incremental checkpoints are tracked per source or query. A default 24-hour overlap, combined with URL deduplication, reduces misses from delayed results. Unknown publication dates stay unknown. A failed or item-limited discovery job does not advance its checkpoint.

Transient network and certain service failures are retried on a later run, with at most three failed attempts per stage by default. There is no immediate retry loop. Persisted successful enrichment is reused. Exactly-once remote execution is not guaranteed if a process crashes after a service succeeds but before the result is saved locally.

`validated` means type, required-field, enum, and excerpt checks passed. An excerpt appearing in the article does not prove the model's interpretation is correct or complete. Review consequential information yourself. The project does not automatically publish to a website or data platform.

## Budgets and run status

Set limits for new/processed items, search requests, HTTP requests, AI calls, and output tokens. Total token reservation uses a conservative input-byte estimate plus the output cap, and separately records provider-reported usage. It is not exact tokenization or a guaranteed billing cap. A custom HTTP service must actually honor its mapped output limit.

Exit codes: `0` completed, possibly with review items; `1` configuration or local error; `2` partial failure; `3` paused by a budget; `130` interrupted by the user. The report contains the detailed reason.

## Scope and limitations

- Basic HTML, RSS/Atom, and listing-link discovery are supported; automatic compatibility with every website is not promised.
- Listings use links and an optional URL regex. External links are excluded by default. General pagination is not implemented.
- Deduplication uses canonical URLs or identical bodies. There is no multilingual semantic deduplication or automatic removal of approximate rewrites.
- Previously stored URLs are not automatically refetched. The current workflow discovers new links; change detection at existing URLs is a future extension.
- Browser rendering is optional. Current acceptance covers standard HTML and local mock APIs, not arbitrary dynamic production websites.
- PDFs, authenticated pages, paywall bypass, complex workbook filling, and distributed jobs are outside this release.
- robots.txt is respected by default; it does not substitute for permission to use the content.
- Private/local addresses are rejected by default. `allow_private_network: true` can enable services you control. This check is not complete network isolation against malicious configuration.

## Tests and contributions

```bash
python3 -m unittest discover -s tests -v
```

Tests cover offline end-to-end runs, template changes, deduplication, recovery, retries, limits, field/evidence validation, and local mock search/enrichment APIs. Test servers listen only on loopback and need no external accounts or credentials.

Contributions to extraction, adapters, templates, and recovery are welcome. Use fictional or reusable fixtures; never submit credentials, private source registries, or actual business data. See [Contributing](CONTRIBUTING.md).

**License:** [Apache-2.0](LICENSE). Use, modification, and commercial reuse are permitted under its conditions. Preserve the license and applicable notices when distributing, and identify modifications as required. See [NOTICE](NOTICE) and the full license text.

**Repository:** [workstonedai-collab/global-knowledge-crawl-pipeline](https://github.com/workstonedai-collab/global-knowledge-crawl-pipeline).
