# Your first information table, with source evidence

[简体中文](walkthrough.zh-CN.md) · [Project overview](../README.en.md)

**Run a complete offline case before connecting your own sources or APIs.** You need Python 3.9+, a browser, and about five minutes. No third-party Python package, account, or API key is required.

![Recorded offline walkthrough, at 2× speed](demo.gif)

[Watch the full recording](demo.mp4) · [Bilingual subtitles](demo.srt)

The GIF is a compact 2× preview; the MP4 follows the actual steps with English and Chinese captions, with long navigation waits removed. The pages and numbers come from a real run of the included fictional fixtures. The video browses the generated results; it does not show real internet searches or model performance.

## What this case demonstrates

| You provide | The pipeline produces |
| --- | --- |
| A fictional listing, RSS feed, and preset keyword-search results | Four discovered candidates |
| Local article files and a field template | Three records, with one exact-body duplicate merged |
| Preset enrichment results | Two records passing structural/excerpt checks and one requiring review |
| A second run with the same workspace | Saved results reused, with zero additional fixture enrichment calls |

All names, URLs, articles, and enrichment are fictional. Extraction, deduplication, validation, persistence, and export actually run. Search and enrichment use local fixtures, not real services. `validated` does not mean a claim is factually verified.

## 1. Download and create the walkthrough

```sh
git clone https://github.com/workstonedai-collab/global-knowledge-crawl-pipeline.git
cd global-knowledge-crawl-pipeline
python3 examples/make_walkthrough.py
```

On Windows, use `py` or `python` if `python3` is not available. Run from the project directory.

The helper executes the same demo twice and builds a visual page from the actual exported CSV and run reports. It checks the expected result and makes no real search or model calls. It preserves existing state: if the workspace already contains files, choose another directory:

```sh
python3 examples/make_walkthrough.py --workspace runtime/visual-demo-2
```

## 2. Open the generated page

Open `runtime/visual-demo/output/walkthrough.html` in your browser. If you supplied another workspace, use that directory instead. No web server is needed for normal use.

- **Inputs:** the included sources, keyword, and target fields. Expand the actual configuration if you want to inspect it.
- **Results:** the table, counters, download links, and the review reason.
- **Evidence:** the pipeline's existing `evidence.html`, containing fields, source quotations, and article text.
- **Reuse:** a comparison of the first and second run reports.

![Actual generated information table](walkthrough-table.png)

## 3. Confirm the expected results

| Check | Expected |
| --- | --- |
| Candidates discovered on the first run | 4 |
| Exported records | 3 |
| Exact-body duplicate | 1 |
| Records passing structure and excerpt checks | 2 |
| Record requiring review | 1 |
| HTTP requests on both runs | 0 |
| First-run fixture enrichment calls | 3 |
| Second-run fixture enrichment calls | 0 |

The keyword-search counter can show one **fixture** invocation even though HTTP requests are zero. Likewise, `ai_calls` counts fixture enrichment calls in this offline example. Neither counter represents a request to a real service here.

Open the Excel link or `table.xlsx` with your spreadsheet application. The browser table is a view of the exported CSV, not a replacement for Excel.

## 4. Review the deliberately incomplete record

The **Field Lab** battery record has no required summary, so it is marked `needs_review` with `summary:required_missing`. Inspect the evidence page and the source text before deciding how to resolve it.

![Evidence and the review reason](walkthrough-review.png)

The source describes an early laboratory experiment. The workflow retains that context; it does not establish performance in consumer products or the correctness of a model's interpretation.

## 5. Inspect the generated files

```text
runtime/visual-demo/output/
  walkthrough.html         Visual case overview
  evidence.html            Fields, quotations, text and changes
  table.xlsx               Spreadsheet export
  table.csv                CSV export
  records.jsonl            Full records and provenance
  review.json              Records needing review
  duplicates.json          Exact-duplicate relationships
  first-run-report.json    Original first-run counters
  second-run-report.json   Reuse counters
```

Runtime files remain in the ignored workspace. No example output or local state needs to be committed.

## Move to real sources and services

Create your own configuration with [the local builder](configuration-builder.md), then follow [the adapter guide](adapters.md). Replace placeholder sources and endpoints, choose a field template, and set credentials in your local environment. Start with a small budget.

The builder makes configuration files; the CLI performs collection. The generated walkthrough uses the offline fixture configuration, not the configuration you download from the builder. Keep those two exercises separate while learning.

Do not record or publish credentials, private endpoints, client data, or internal source lists. Real AI quality and source compatibility require their own verification.

## Give this task to your agent

> Clone Global Knowledge Crawl Pipeline into a new folder and verify Python 3.9+. First run examples/make_walkthrough.py using a new workspace. Give me the path to walkthrough.html, table.xlsx, and evidence.html. Confirm 4 candidates, 3 records, 1 duplicate, 1 review item, and zero additional fixture enrichment calls on the second run. Explain the incomplete record. Do not request any credentials for this offline case. After it works, guide me through configuring my own sources, field template, search API, and enrichment API; keep credentials local and start with a small budget.

## Verification

Recorded on 2026-10-06 using the 0.2.0 pipeline. The example, both reuse reports, the generated CSV, and the review reason were checked. The existing suite passed 35 tests. This is a local fictional-case demonstration; it does not verify arbitrary live websites or actual model output.
