from __future__ import annotations

import difflib
import html
import json
from pathlib import Path
from urllib.parse import urlsplit

from .exports import atomic_write

STYLE = """body{font:16px/1.65 system-ui,sans-serif;background:#f5f7fa;color:#182432;margin:0}main{max-width:1120px;margin:auto;padding:32px}h1{line-height:1.25}article,section{background:white;border:1px solid #dbe3ed;border-radius:14px;padding:22px;margin:20px 0}table{width:100%;border-collapse:collapse}td,th{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #e5eaf0}th{background:#f0f4f8}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f9;padding:14px;border-radius:8px}blockquote{border-left:3px solid #24776e;margin:12px 0;padding:8px 16px;background:#f1faf7}a{color:#145f91}small{color:#536476}.badge{background:#e7f1fa;border-radius:20px;padding:3px 12px}.needs_review{background:#fff1cd}.empty{padding:20px;color:#536476}@media(max-width:700px){main{padding:16px}td,th{padding:7px}table{font-size:14px}}"""


def escaped(value):
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(value)


def evidence_report(records, changes):
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src \'none\'; base-uri \'none\'">',
             '<title>信息与证据 / Information and evidence</title><style>' + STYLE + '</style><main>',
             '<h1>信息与证据<br><small>Information and evidence</small></h1>',
             '<p>字段、引用与网页变化集中展示，便于人工复核。结构和摘录检查通过不等于事实已确认。<br>Review fields, quotations and page changes. Passing structural and excerpt checks does not establish factual accuracy.</p>']
    if not records:
        parts.append('<section class="empty">暂无记录 / No records yet</section>')
    for record in records:
        metadata = record['metadata']
        result = record.get('enrichment') or {}
        url = metadata.get('url', '')
        href = url if urlsplit(url).scheme in {'https', 'http'} else ''
        title = metadata.get('title') or url or record['id']
        parts.append('<article><h2>' + escaped(title) + '</h2><span class="badge ' + ('needs_review' if record['status'] == 'needs_review' else '') + '">' + escaped(record['status']) + '</span>')
        parts.append('<p><a rel="noreferrer noopener" href="' + escaped(href) + '">' + escaped(url) + '</a></p>')
        parts.append('<small>最近检查 / Last checked: ' + escaped(metadata.get('checked_at', metadata.get('collected_at', ''))) + '</small>')
        parts.append('<table><thead><tr><th>字段 / Field</th><th>结果 / Value</th><th>原文摘录 / Source excerpt</th></tr></thead><tbody>')
        for name, value in result.get('fields', {}).items():
            quotes = result.get('evidence', {}).get(name, [])
            evidence = ''.join('<blockquote>' + escaped(q) + '</blockquote>' for q in quotes) or '<small>元数据或未提供摘录 / Metadata or no excerpt supplied</small>'
            parts.append('<tr><th>' + escaped(name) + '</th><td>' + escaped(value) + '</td><td>' + evidence + '</td></tr>')
        parts.append('</tbody></table>')
        if record.get('issues'):
            parts.append('<p>待核对 / Review: ' + escaped(', '.join(record['issues'])) + '</p>')
        parts.append('<details><summary>查看采集正文 / Collected text</summary><pre>' + escaped(record.get('body') or '') + '</pre></details></article>')
    parts.append('<section><h2>网页变化 / Page changes</h2>')
    if not changes:
        parts.append('<p>暂无已记录的正文变化。使用 --refresh-existing 重新检查已保存的网址。<br>No recorded text changes. Use --refresh-existing to check saved URLs again.</p>')
    for change in changes:
        diff = '\n'.join(difflib.unified_diff(change['old_body'].splitlines(), change['new_body'].splitlines(), fromfile='before', tofile='after', lineterm=''))
        parts.append('<details><summary>' + escaped(change['record_id']) + ' · ' + escaped(change['changed_at']) + ' · v' + str(change['revision']) + '</summary><pre>' + escaped(diff) + '</pre></details>')
    parts.append('</section></main></html>')
    return '\n'.join(parts)


def write_configurator(path: Path):
    content = (Path(__file__).parent / 'assets' / 'configure.html').read_text(encoding='utf-8')
    atomic_write(path, lambda temporary: temporary.write_text(content, encoding='utf-8'))
