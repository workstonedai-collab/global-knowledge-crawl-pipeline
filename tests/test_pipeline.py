from __future__ import annotations

import copy
import csv
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
import zipfile
from contextlib import redirect_stderr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from gkp.cli import main
from gkp.common import BudgetExceeded, PipelineError, canonical_url, get_path, normalized_date, render
from gkp.config import Budget, Config
from gkp.discovery import rss_items
from gkp.exports import export_records, xlsx_write
from gkp.fetching import parse_html
from gkp.http import HttpClient
from gkp.pipeline import run, workspace_lock
from gkp.schema import validate_result
from gkp.state import State

ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "examples", self.root / "examples")
        self.config_path = self.root / "examples" / "demo.json"
        self.workspace = self.root / "workspace"

    def tearDown(self):
        self.temp.cleanup()

    def configure(self, edit=None):
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        if edit:
            edit(data)
        self.config_path.write_text(json.dumps(data), encoding="utf-8")
        return Config(self.config_path)

    def records(self):
        return [json.loads(line) for line in (self.workspace / "output" / "records.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_offline_end_to_end_keeps_provenance_review_and_duplicates(self):
        with patch("socket.getaddrinfo", side_effect=AssertionError("offline attempted DNS")):
            report = run(self.configure(), self.workspace)
        self.assertEqual(report["counts"], {"records": 3, "validated": 2, "needs_review": 1, "failed": 0, "pending": 0, "duplicates": 1})
        self.assertEqual(report["budget"]["http_requests"], 0)
        self.assertEqual(report["budget"]["ai_calls"], 3)
        lamp = self.records()[0]
        self.assertEqual({source["discovery_provider"] for source in lamp["metadata"]["sources"]}, {"listing", "fixture"})
        self.assertEqual(len(lamp["metadata"]["sources"]), 3)
        self.assertNotIn("ignore this script", lamp["body"])
        self.assertEqual(self.records()[-1]["enrichment"]["fields"]["summary"], None)
        self.assertIn("summary:required_missing", self.records()[-1]["issues"])

    def test_rerun_reuses_saved_results_and_export_has_no_duplicates(self):
        config = self.configure()
        run(config, self.workspace)
        first = (self.workspace / "output" / "table.csv").read_bytes()
        report = run(config, self.workspace)
        self.assertEqual(report["new_candidates"], 0)
        self.assertEqual(report["budget"]["ai_calls"], 0)
        self.assertEqual(first, (self.workspace / "output" / "table.csv").read_bytes())

    def test_changed_template_invalidates_only_contract_cache(self):
        run(self.configure(), self.workspace)
        template_path = self.root / "examples" / "product-template.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        template["version"] = "v2"
        template["fields"].append({"name": "source_url", "type": "string", "source": "metadata.url"})
        template_path.write_text(json.dumps(template), encoding="utf-8")
        report = run(self.configure(), self.workspace)
        self.assertEqual(report["budget"]["ai_calls"], 3)
        self.assertEqual(report["new_candidates"], 0)
        with (self.workspace / "output" / "table.csv").open(encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[0]["source_url"], rows[0]["_url"])
        self.assertEqual(run(self.configure(), self.workspace)["budget"]["ai_calls"], 0)

    def test_ai_budget_pauses_and_resumes_only_unfinished_records(self):
        config = self.configure(lambda d: d["limits"].update(max_ai_calls=1))
        first = run(config, self.workspace)
        self.assertEqual(first["status"], "paused")
        self.assertEqual(first["budget"]["ai_calls"], 1)
        second = run(config, self.workspace, discover=False)
        third = run(config, self.workspace, discover=False)
        self.assertEqual(second["budget"]["ai_calls"], 1)
        self.assertEqual(third["counts"]["pending"], 0)
        self.assertEqual(third["budget"]["ai_calls"], 1)

    def test_custom_chinese_ai_fields_need_no_core_changes(self):
        template_path = self.root / "examples" / "product-template.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        for field in template["fields"]:
            if field["name"] == "title":
                field["name"] = "标题"
            elif field["name"] == "summary":
                field["name"] = "摘要"
        template_path.write_text(json.dumps(template), encoding="utf-8")
        fixture_path = self.root / "examples" / "fixtures" / "enrichment.json"
        fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
        for result in fixtures.values():
            result["fields"]["摘要"] = result["fields"].pop("summary")
            if "summary" in result["evidence"]:
                result["evidence"]["摘要"] = result["evidence"].pop("summary")
        fixture_path.write_text(json.dumps(fixtures), encoding="utf-8")
        report = run(self.configure(), self.workspace)
        self.assertEqual(report["counts"]["validated"], 2)
        self.assertIn("摘要", self.records()[0]["enrichment"]["fields"])
        self.assertIn("摘要:required_missing", self.records()[-1]["issues"])

    def test_insufficient_token_budget_makes_no_ai_request(self):
        report = run(self.configure(lambda d: d["limits"].update(max_total_tokens=1)), self.workspace)
        self.assertEqual(report["stop_reason"], "budget_total_tokens")
        self.assertEqual(report["budget"]["ai_calls"], 0)

    def test_saved_success_survives_interruption(self):
        real = State.enrichment_result
        calls = []
        def interrupt(state, *args):
            real(state, *args)
            calls.append(args[0])
            raise KeyboardInterrupt
        config = self.configure()
        with patch.object(State, "enrichment_result", interrupt):
            with self.assertRaises(KeyboardInterrupt):
                run(config, self.workspace)
        report = run(config, self.workspace)
        self.assertEqual(report["budget"]["ai_calls"], 2)
        self.assertEqual(report["counts"]["records"], 3)

    def test_discovery_failure_does_not_advance_its_checkpoint(self):
        feed = self.root / "examples" / "fixtures" / "feed.xml"
        feed.write_text("not XML", encoding="utf-8")
        config = self.configure()
        report = run(config, self.workspace)
        self.assertEqual(report["status"], "partial")
        state = State(self.workspace / "state.sqlite", config.dataset)
        try:
            keys = [row["key"] for row in state.db.execute("SELECT key FROM checkpoints")]
            self.assertFalse(any(key.startswith("source:public-feed:") for key in keys))
            self.assertTrue(any(key.startswith("source:public-list:") for key in keys))
        finally:
            state.close()

    def test_exhausted_fetch_can_be_explicitly_retried(self):
        fixture = self.root / "examples" / "fixtures" / "library.html"
        original = fixture.read_text(encoding="utf-8")
        fixture.write_text("<p>tiny</p>", encoding="utf-8")
        config = self.configure()
        report = run(config, self.workspace)
        self.assertEqual(report["counts"]["failed"], 1)
        fixture.write_text(original, encoding="utf-8")
        self.assertEqual(run(config, self.workspace)["counts"]["failed"], 1)
        report = run(config, self.workspace, retry_failed=True)
        self.assertEqual(report["counts"]["failed"], 0)
        self.assertEqual(report["budget"]["ai_calls"], 1)

    def test_review_retry_does_not_repeat_validated_results(self):
        config = self.configure()
        run(config, self.workspace)
        report = run(config, self.workspace, retry_review=True)
        self.assertEqual(report["budget"]["ai_calls"], 1)

    def test_dataset_mismatch_and_concurrent_workspace_are_rejected(self):
        run(self.configure(), self.workspace)
        other = self.configure(lambda d: d.update(dataset="another_dataset"))
        with self.assertRaisesRegex(PipelineError, "workspace_dataset_mismatch"):
            run(other, self.workspace)
        with workspace_lock(self.workspace):
            with self.assertRaisesRegex(PipelineError, "workspace_already_running"):
                run(other, self.workspace)

    def test_offline_config_rejects_live_services(self):
        with self.assertRaisesRegex(PipelineError, "offline_enrichment_requires_fixture"):
            self.configure(lambda d: d.update(enrichment={"provider": "http_json", "endpoint": "https://api.example.com/enrich"}))

    def test_cli_errors_do_not_echo_config_or_credentials(self):
        self.config_path.write_text('{"secret": "synthetic-only"', encoding="utf-8")
        output = io.StringIO()
        with redirect_stderr(output):
            self.assertEqual(main(["validate", str(self.config_path)]), 1)
        self.assertNotIn("synthetic-only", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())


class ExtractionTests(unittest.TestCase):
    def test_normalization_preserves_meaningful_query_and_blocks_credentials(self):
        self.assertEqual(canonical_url("https://Example.com/news?utm_source=x&id=3#top"), "https://example.com/news?id=3")
        self.assertNotEqual(canonical_url("https://example.com/a/"), canonical_url("https://example.com/a"))
        for url in ("https://user:pass@example.com/", "https://example.com/?api_key=placeholder"):
            with self.assertRaises(PipelineError):
                canonical_url(url)

    def test_html_extracts_main_text_date_and_links(self):
        doc = parse_html('<title>A title</title><nav>Ignore</nav><main><p>Useful body.</p><a href="/a">Read A</a></main><script>Ignore</script><meta property="article:published_time" content="2026-01-01T00:00:00Z">')
        self.assertEqual(doc.title, "A title")
        self.assertNotIn("Ignore", doc.text)
        self.assertEqual(doc.links, [("/a", "Read A")])
        self.assertEqual(doc.published_at, "2026-01-01T00:00:00+00:00")

    def test_atom_and_unknown_dates(self):
        feed = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Title</title><link href="https://example.com/a"/><published>2026-01-01T00:00:00Z</published><summary>Text</summary></entry></feed>'
        self.assertEqual(list(rss_items(feed))[0]["url"], "https://example.com/a")
        self.assertIsNone(normalized_date("2026-01-01"))
        self.assertIsNone(normalized_date("yesterday"))
        with self.assertRaisesRegex(PipelineError, "feed_dtd_blocked"):
            list(rss_items('<!DOCTYPE x [<!ENTITY y "z">]><rss/>'))

    def test_request_mapping_preserves_objects_and_rejects_unknown_placeholders(self):
        schema = {"type": "object"}
        self.assertEqual(render({"schema": "$schema", "n": "$limit"}, {"schema": schema, "limit": 2}), {"schema": schema, "n": 2})
        self.assertEqual(get_path({"choices": [{"text": "ok"}]}, "choices.0.text"), "ok")
        with self.assertRaises(PipelineError):
            render("$missing", {})

    def test_wrong_types_enum_and_evidence_are_reviewable(self):
        template = {"fields": [
            {"name": "count", "type": "integer", "required": True},
            {"name": "category", "type": "string", "enum": ["research"], "evidence_required": True}]}
        result = validate_result({"fields": {"count": True, "category": "release"}, "evidence": {"category": ["invented quote"]}}, template, {}, "Actual source")
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["fields"], {"count": None, "category": None})
        self.assertIn("count:wrong_type", result["issues"])
        self.assertIn("category:invalid_evidence", result["issues"])

    def test_malformed_result_becomes_review_instead_of_success(self):
        result = validate_result(None, {"fields": [{"name": "summary", "type": "string", "required": True}]}, {}, "Body")
        self.assertEqual(result["status"], "needs_review")
        self.assertIn("invalid_result_structure", result["issues"])

    def test_workbook_contains_strings_not_executable_formulas(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "table.xlsx"
            xlsx_write(path, ["summary", "count"], [{"summary": "=1+1", "count": 2}])
            with zipfile.ZipFile(path) as archive:
                self.assertIsNone(archive.testzip())
                root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
                self.assertFalse(root.findall(".//{*}f"))
                text = [node.text for node in root.findall(".//{*}t")]
                self.assertIn("'=1+1", text)


class LocalApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.requests = []
        self.fail_ai = False
        self.bad_json = False
        self.deny_robots = False
        parent = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                parent.requests.append(("GET", self.path, None, dict(self.headers)))
                if self.path == "/robots.txt":
                    self.send(200, "User-agent: *\nDisallow: /article\n" if parent.deny_robots else "User-agent: *\nAllow: /\n", "text/plain")
                elif self.path == "/listing":
                    self.send(200, '<main><a href="/article">Test article</a></main>', "text/html")
                elif self.path == "/article":
                    self.send(200, '<article><h1>Test article</h1><p>Example Studio announced a proposed service update.</p><p>No date was confirmed.</p></article>', "text/html")
                elif self.path.startswith("/search-get"):
                    self.send(200, json.dumps({"data": [{"link": parent.base + "/article", "heading": "Test article"}]}))
                else:
                    self.send(404, "missing", "text/plain")

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                parent.requests.append(("POST", self.path, body, dict(self.headers)))
                if self.path == "/search":
                    self.send(200, json.dumps({"data": [{"link": parent.base + "/article?utm_source=search", "heading": "Test article"}]}))
                elif self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/chat")
                    self.end_headers()
                elif self.path in {"/chat", "/custom"}:
                    if parent.fail_ai:
                        self.send(429, "synthetic-provider-error-must-not-be-logged")
                        return
                    result = {"fields": {"organization": "Example Studio", "summary": "A proposed update with no confirmed date."},
                              "evidence": {"organization": ["Example Studio announced"], "summary": ["No date was confirmed."]}}
                    if self.path == "/chat":
                        self.send(200, json.dumps({"choices": [{"message": {"content": "not json" if parent.bad_json else json.dumps(result)}}], "usage": {"total_tokens": 25}}))
                    else:
                        self.send(200, json.dumps({"data": {"result": result, "usage": {"total_tokens": 25}}}))
                else:
                    self.send(404, "missing")

            def send(self, status, data, kind="application/json"):
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.end_headers()
                self.wfile.write(data.encode())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = "http://127.0.0.1:" + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.template = {"version": "test-v1", "fields": [
            {"name": "title", "type": "string", "source": "metadata.title", "required": True},
            {"name": "organization", "type": "string", "instruction": "Extract organization", "evidence_required": True},
            {"name": "summary", "type": "string", "instruction": "Summarize", "required": True, "evidence_required": True}]}
        (self.root / "template.json").write_text(json.dumps(self.template), encoding="utf-8")
        self.data = {"dataset": "local_test", "template": "template.json", "allow_private_network": True,
                     "sources": [{"id": "list", "type": "listing", "url": self.base + "/listing"}],
                     "search": {"provider": "http_json", "endpoint": self.base + "/search", "queries": ["service update"],
                                "request": {"q": "$query", "since": "$since", "limit": "$limit"},
                                "response": {"items_path": "data", "fields": {"url": "link", "title": "heading"}}},
                     "enrichment": {"provider": "chat_completions", "endpoint": self.base + "/chat", "model": "test-model", "credential_env": "GKP_TEST_CREDENTIAL"}}
        self.workspace = self.root / "workspace"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def config(self):
        path = self.root / "config.json"
        path.write_text(json.dumps(self.data), encoding="utf-8")
        return Config(path)

    def execute(self, **kwargs):
        with patch.dict(os.environ, {"GKP_TEST_CREDENTIAL": "synthetic-test-only"}):
            return run(self.config(), self.workspace, **kwargs)

    def test_live_shape_end_to_end_with_only_local_mock_server(self):
        report = self.execute()
        self.assertEqual(report["counts"]["validated"], 1)
        self.assertEqual(report["counts"]["records"], 1)
        chat = [row for row in self.requests if row[1] == "/chat"][0]
        self.assertEqual(chat[3]["Authorization"], "Bearer synthetic-test-only")
        self.assertEqual(chat[2]["max_tokens"], 1200)
        self.assertEqual(report["budget"]["tokens_reported"], 25)
        for path in (self.workspace / "output").iterdir():
            if path.suffix != ".xlsx":
                self.assertNotIn("synthetic-test-only", path.read_text(encoding="utf-8-sig"))
        self.assertEqual(self.execute()["budget"]["ai_calls"], 0)

    def test_custom_http_enrichment_request_and_nested_response(self):
        self.data["enrichment"] = {"provider": "http_json", "endpoint": self.base + "/custom",
                                   "request": {"content": "$text", "schema": "$schema", "limit": "$max_output_tokens"},
                                   "response_path": "data.result", "usage_path": "data.usage.total_tokens"}
        report = self.execute()
        self.assertEqual(report["counts"]["validated"], 1)
        request = [row for row in self.requests if row[1] == "/custom"][0][2]
        self.assertIsInstance(request["schema"], dict)
        self.assertIn("Example Studio", request["content"])

    def test_get_search_mapping(self):
        self.data["search"].update(endpoint=self.base + "/search-get", method="GET")
        report = self.execute()
        self.assertEqual(report["counts"]["records"], 1)
        self.assertTrue(any("q=service+update" in row[1] for row in self.requests))

    def test_transient_failure_retries_without_repeating_saved_fetch(self):
        self.fail_ai = True
        first = self.execute()
        self.assertEqual(first["counts"]["failed"], 1)
        self.assertNotIn("synthetic-provider-error", json.dumps(first))
        self.fail_ai = False
        second = self.execute()
        self.assertEqual(second["counts"]["validated"], 1)
        self.assertEqual(sum(row[1] == "/article" for row in self.requests), 1)

    def test_invalid_model_json_is_cached_as_review(self):
        self.bad_json = True
        first = self.execute()
        self.assertEqual(first["counts"]["needs_review"], 1)
        self.assertEqual(self.execute()["budget"]["ai_calls"], 0)

    def test_robots_prevents_article_request(self):
        self.deny_robots = True
        report = self.execute()
        self.assertEqual(report["counts"]["failed"], 1)
        self.assertFalse(any(row[1] == "/article" for row in self.requests))
        self.assertFalse(any(row[1] == "/chat" for row in self.requests))

    def test_api_auth_redirect_is_blocked(self):
        self.data["enrichment"]["endpoint"] = self.base + "/redirect"
        report = self.execute()
        self.assertEqual(report["counts"]["failed"], 1)
        self.assertFalse(any(row[1] == "/chat" for row in self.requests))

    def test_private_network_block_and_http_budget(self):
        budget = Budget(Config(ROOT / "examples" / "demo.json").limits)
        client = HttpClient(budget)
        with self.assertRaisesRegex(PipelineError, "private_address_blocked"):
            client.request(self.base + "/article")
        self.data["limits"] = {"max_http_requests": 1}
        report = self.execute()
        self.assertEqual(report["status"], "paused")
        self.assertEqual(report["budget"]["http_requests"], 1)


if __name__ == "__main__":
    unittest.main()
