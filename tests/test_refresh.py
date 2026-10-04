import json
from unittest.mock import patch

import test_pipeline as fixtures
import unittest
from gkp.common import PipelineError
from gkp.pipeline import run
from gkp.preview import evidence_report, write_configurator


class RefreshTests(unittest.TestCase):
    setUp = fixtures.PipelineTests.setUp
    tearDown = fixtures.PipelineTests.tearDown
    configure = fixtures.PipelineTests.configure
    records = fixtures.PipelineTests.records
    def test_changed_body_reenriches_only_that_record_and_keeps_history(self):
        config = self.configure()
        run(config, self.workspace)
        path = self.root / 'examples/fixtures/library.html'
        path.write_text(path.read_text(encoding='utf-8').replace('four-week', 'six-week'), encoding='utf-8')
        report = run(config, self.workspace, discover=False, refresh_existing=True)
        self.assertEqual(report['changed_this_run'], 1)
        self.assertEqual(report['budget']['ai_calls'], 1)
        self.assertEqual(len(json.loads((self.workspace / 'output/changes.json').read_text(encoding='utf-8'))), 1)
        self.assertIn('category:invalid_evidence', self.records()[1]['issues'])
        self.assertEqual(run(config, self.workspace, discover=False, refresh_existing=True)['budget']['ai_calls'], 0)

    def test_unchanged_refresh_reuses_all_ai_results(self):
        config = self.configure()
        run(config, self.workspace)
        report = run(config, self.workspace, discover=False, refresh_existing=True)
        self.assertEqual(report['refreshed_this_run'], 4)
        self.assertEqual(report['changed_this_run'], 0)
        self.assertEqual(report['budget']['ai_calls'], 0)
        self.assertEqual(json.loads((self.workspace / 'output/changes.json').read_text(encoding='utf-8')), [])

    def test_failed_refresh_preserves_last_usable_record(self):
        config = self.configure()
        run(config, self.workspace)
        before = self.records()
        with patch('gkp.pipeline.Fetcher.body', side_effect=PipelineError('synthetic_failure', True)):
            report = run(config, self.workspace, discover=False, refresh_existing=True)
        self.assertEqual(self.records(), before)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(len(report['discovery_errors']), 4)
        self.assertEqual(report['refreshed_this_run'], 0)

    def test_small_refresh_budget_rotates_through_saved_urls(self):
        config = self.configure()
        run(config, self.workspace)
        config = self.configure(lambda d: d['limits'].update(max_items=2))
        from gkp.fetching import Fetcher
        fetch = Fetcher.body
        visited = []

        def tracked(instance, metadata):
            visited.append(metadata['url'])
            return fetch(instance, metadata)

        with patch('gkp.pipeline.Fetcher.body', tracked):
            first = run(config, self.workspace, discover=False, refresh_existing=True)
            second = run(config, self.workspace, discover=False, refresh_existing=True)
        self.assertEqual(first['refreshed_this_run'], 2)
        self.assertEqual(second['refreshed_this_run'], 2)
        self.assertEqual(len(set(visited)), 4)
        self.assertEqual(second['budget']['ai_calls'], 0)

    def test_duplicate_becomes_independent_when_its_body_changes(self):
        config = self.configure()
        run(config, self.workspace)
        path = self.root / 'examples/fixtures/lamp-copy.html'
        path.write_text('<main><p>An entirely different public announcement by Fictional Lab, with enough content to be extracted.</p></main>', encoding='utf-8')
        config = self.configure(lambda d: d['fetch']['fixtures'].update({'https://example.net/news/lamp-copy': 'fixtures/lamp-copy.html'}))
        report = run(config, self.workspace, discover=False, refresh_existing=True)
        self.assertEqual(report['counts']['duplicates'], 0)
        self.assertEqual(report['counts']['records'], 4)
        self.assertEqual(report['changed_this_run'], 1)
        self.assertEqual(report['budget']['ai_calls'], 1)

    def test_html_report_escapes_untrusted_content_and_has_no_scripts(self):
        record = {'id': 'r', 'status': 'needs_review', 'issues': ['<img onerror=1>'], 'body': '</pre><script>alert(1)</script>',
                  'metadata': {'url': 'javascript:alert(1)', 'title': '<script>title</script>'},
                  'enrichment': {'fields': {'summary': '<img src=x onerror=1>'}, 'evidence': {'summary': ['<script>quote</script>']}}}
        rendered = evidence_report([record], [])
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('href="javascript:', rendered)
        self.assertIn('&lt;script&gt;quote', rendered)
        self.assertIn('default-src', rendered)

    def test_configurator_is_written_without_network_or_service_credentials(self):
        path = self.root / 'configure.html'
        with patch('socket.getaddrinfo', side_effect=AssertionError('network access')):
            write_configurator(path)
        rendered = path.read_text(encoding='utf-8')
        self.assertIn('downloadConfig', rendered)
        self.assertNotIn('fetch(', rendered)
        self.assertNotIn('localStorage', rendered)
