#!/usr/bin/env python3
"""Build a visual walkthrough from actual offline pipeline output (standard library only)."""
# SPDX-License-Identifier: Apache-2.0
import argparse
import csv
import html
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', default='runtime/visual-demo',
                        help='Use a new empty workspace; existing state is preserved.')
    args = parser.parse_args()
    workspace = Path(args.workspace).expanduser()
    if not workspace.is_absolute():
        workspace = ROOT / workspace
    if workspace.exists() and (not workspace.is_dir() or any(workspace.iterdir())):
        parser.error('Workspace is not empty. Choose another --workspace to preserve existing results. / 请另选一个空目录。')

    def run():
        result = subprocess.run([sys.executable, '-m', 'gkp', 'run',
                                 'examples/demo.json', '--workspace', str(workspace)],
                                cwd=ROOT, check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    first, second = run(), run()
    assert first['offline'] and second['offline']
    assert first['budget']['http_requests'] == second['budget']['http_requests'] == 0
    assert first['counts']['records'] == second['counts']['records'] == 3
    assert first['counts']['needs_review'] == second['counts']['needs_review'] == 1
    assert first['budget']['ai_calls'] == 3 and second['budget']['ai_calls'] == 0
    output = workspace / 'output'
    (output / 'first-run-report.json').write_text(json.dumps(first, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (output / 'second-run-report.json').write_text(json.dumps(second, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (output / 'table.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    config = json.loads((ROOT / 'examples/demo.json').read_text(encoding='utf-8'))
    template = json.loads((ROOT / 'examples/product-template.json').read_text(encoding='utf-8'))
    esc = lambda value: html.escape(str(value), quote=True)
    columns = ['title', 'organization', 'category', 'summary', '_status']
    table = ''.join('<tr>'+''.join('<td>'+esc(row.get(key,''))+'</td>' for key in columns)+'</tr>' for row in rows)
    fields = ', '.join(field['name'] for field in template['fields'])
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'">
<title>Global Knowledge Crawl Pipeline · Offline walkthrough</title>
<style>
body{margin:0;background:#f4f7fa;color:#172b3b;font:16px/1.6 system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:32px}h1{font-size:36px;line-height:1.2;margin:10px 0 18px}
h2{font-size:24px}small{color:#52697a}a{color:#146b65}nav{display:flex;gap:16px;flex-wrap:wrap;margin:20px 0}
.tag{display:inline-block;background:#e2f3ec;color:#185346;border-radius:20px;padding:5px 14px;font-weight:600}
.note{border-left:4px solid #bd872d;background:#fff3d8;padding:14px 18px}
section{background:white;border:1px solid #d9e2e9;border-radius:14px;padding:24px;margin:22px 0;scroll-margin-top:18px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.stat{background:#edf4f6;border-radius:10px;padding:18px}.stat b{display:block;font-size:34px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #dee7ec}th{background:#eef4f7}
pre{white-space:pre-wrap;word-break:break-word;background:#eff4f7;padding:18px;border-radius:10px;font:14px/1.6 monospace}
.compare{display:grid;grid-template-columns:1fr 1fr;gap:18px}.compare div{padding:20px;border-radius:10px;background:#edf5f0}
@media(max-width:700px){main{padding:16px}.stats,.compare{grid-template-columns:1fr 1fr}h1{font-size:28px}.overflow{overflow:auto}}
</style></head><body><main>
<span class="tag">OFFLINE DEMO / 离线演示</span>
<h1>Web &amp; search → your information table<br><small>网页与搜索 → 自定义信息表</small></h1>
<p>Global Knowledge Crawl Pipeline (by GKN)</p>
<p class="note">Fictional sources and preset enrichment. No real search or AI calls.<br>来源和富化结果均为虚构；不请求真实搜索或 AI。下方结果来自程序实际运行。</p>
<nav><a href="#input">1. Inputs / 输入</a><a href="#results">2. Results / 结果</a><a href="evidence.html">3. Evidence / 证据</a><a href="#resume">4. Reuse / 复用</a></nav>
<section id="input"><h2>1. Sources + fields / 来源与字段</h2>
<p>Listing page + RSS + simulated keyword search / 列表页、RSS 与模拟关键词检索</p>
<p>Keyword / 关键词：<code>public product updates</code></p>
<p>Table fields / 表格字段：<strong>FIELDS</strong></p>
<details><summary>View the actual demo configuration / 查看实际示例配置</summary><pre>CONFIG</pre></details></section>
<section id="results"><h2>2. Actual output / 实际输出</h2>
<div class="stats"><div class="stat"><b>4</b>Candidates / 候选</div><div class="stat"><b>3</b>Records / 记录</div><div class="stat"><b>1</b>Duplicate / 重复</div><div class="stat"><b>1</b>Needs review / 待复核</div></div>
<p>2 records pass structure and excerpt checks; factual accuracy still needs human judgment.<br>2 条通过结构和摘录检查；事实是否正确仍需人工判断。</p>
<div class="overflow"><table><thead><tr>HEADERS</tr></thead><tbody>ROWS</tbody></table></div>
<p class="note">The battery record deliberately has no summary: <code>summary:required_missing</code>.<br>电池实验记录故意缺少摘要，因此进入待复核队列。</p>
<p><a href="table.xlsx">Open Excel / 打开 Excel</a> · <a href="table.csv">CSV</a> · <a href="evidence.html">Inspect source evidence / 查看原文证据</a></p></section>
<section id="resume"><h2>4. Run again, reuse saved results / 再次运行，复用已保存结果</h2>
<div class="compare"><div><strong>First run / 第一次</strong><p>3 fixture enrichment calls<br>3 次本地模拟富化</p></div><div><strong>Second run / 第二次</strong><p>0 fixture enrichment calls<br>0 次本地模拟富化</p></div></div>
<p>Both runs make 0 HTTP requests. No API keys or paid services are used.<br>两次运行的 HTTP 请求均为 0；不使用密钥或付费服务。</p>
<p><a href="first-run-report.json">First report / 首次报告</a> · <a href="second-run-report.json">Second report / 再次报告</a></p></section>
<p>Generated by <code>examples/make_walkthrough.py</code> from the included fictional fixtures.<br>由随仓库提供的虚构样例运行生成；替换为实际来源与服务后才能展示真实互联网采集和模型质量。</p>
</main></body></html>'''
    page = page.replace('FIELDS', esc(fields)).replace('CONFIG', esc(json.dumps(config, ensure_ascii=False, indent=2)))
    page = page.replace('HEADERS', ''.join('<th>'+esc(key)+'</th>' for key in columns)).replace('ROWS', table)
    target = output / 'walkthrough.html'
    target.write_text(page, encoding='utf-8')
    print('Open / 打开：'+str(target))
    print('Verified / 已验证：4 candidates → 3 records; 1 duplicate; 1 review item; second-run fixture calls = 0.')


if __name__ == '__main__':
    main()
